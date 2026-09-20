#!/usr/bin/env python3
"""Export a PPTD project as page images through the local neo-ppt mirror for visual QA.

Reuses the localhost local-editor host from export_pptx.py, chooses
图片 in the export dialog, captures the images ZIP, unzips it, and stitches all pages
into a single overview image that a multimodal model can review.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pptd_browser import (
    EditorExportSession,
    browser_cdp_url,
    cdp_call,
    cdp_connect,
    ensure_agent_browser,
    ensure_debug_chrome,
    open_export_dialog,
    wait_for_export_dialog,
)
from pptd_common import ExportError, ensure_module, log
from pptd_deck import find_manifest

from export_pptx import open_local_editor

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
OVERVIEW_COLUMNS = 3
OVERVIEW_THUMB_WIDTH = 640
OVERVIEW_LABEL_HEIGHT = 32
OVERVIEW_GAP = 12
PAGE_URL_HINT = "127.0.0.1"

# The export dialog's 图片 format option is a plain <div class="radio-group-item">
# without an ARIA role, so agent-browser's interactive snapshot never exposes it.
# Local editor is same-origin (no iframe); CDP Runtime.evaluate on the page works.
IMAGE_FORMAT_CLICK_JS = """
(() => {
  const items = [...document.querySelectorAll('.radio-group-item')];
  const pool = items.length
    ? items
    : [...document.querySelectorAll('div,span,label,button')].filter(
        (el) => el.children.length === 0
      );
  const target = pool.find((el) => el.textContent.trim() === '图片');
  if (!target) return null;
  target.click();
  return 'clicked';
})()
""".strip()

ACTIVE_FORMAT_JS = """
(() => {
  const active = document.querySelector('.radio-group-item.active');
  return active ? active.textContent.trim() : null;
})()
""".strip()


def ensure_pillow() -> Tuple[Any, Any, Any]:
    ensure_module("PIL", "pillow", "Pillow is required for stitching")
    from PIL import Image, ImageDraw, ImageFont

    return Image, ImageDraw, ImageFont


def is_image_zip(path: Path) -> bool:
    if not path.is_file() or path.name.endswith(".crdownload"):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return any(
                Path(name).suffix.lower() in IMAGE_SUFFIXES
                for name in archive.namelist()
            )
    except (OSError, zipfile.BadZipFile):
        return False


def unzip_images(archive_path: Path, pages_dir: Path) -> List[Path]:
    """Extract the page images **in ZIP entry order**.

    The editor writes one entry per page in page order. Guessing page order from
    file names ("2.jpeg" vs "10.jpeg", covers mixed in) produced silently wrong
    image → .page mappings, so the entry order is the contract instead.
    """
    pages_dir.mkdir(parents=True, exist_ok=True)
    images: List[Path] = []
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            if info.is_dir() or Path(info.filename).suffix.lower() not in IMAGE_SUFFIXES:
                continue
            name = Path(info.filename).name
            if not name:
                continue
            target = pages_dir / name
            with archive.open(info) as source, target.open("wb") as out:
                shutil.copyfileobj(source, out)
            images.append(target)
    if not images:
        raise ExportError(f"no page images found in: {archive_path}")
    return images


def canonical_page_names(images: Sequence[Path]) -> List[Tuple[Path, str]]:
    """Rename the extracted pages to `pages/<n>.<ext>`; return (path, editorName).

    The names inside the editor's ZIP are whatever the editor chose (page titles,
    ids, timestamps), so the summary's `images[].image` path is useless to a
    caller that has to find "the render of page 7". Numbering from the ZIP entry
    order makes `P<n>` on the stitched overview and `pages/<n>.<ext>` the same
    page; the editor's own name is returned alongside for cross-checking.

    The editor's names can already look canonical ("1.jpeg"), and a naive
    in-place rename would then overwrite a neighbour, so every file is staged
    aside first and moved back in page order.
    """
    if not images:
        return []
    pages_dir = images[0].parent
    editor_names = [path.name for path in images]
    targets: List[Path] = []
    for index, path in enumerate(images, start=1):
        suffix = path.suffix.lower()
        if suffix not in IMAGE_SUFFIXES:
            raise ExportError(f"page image has an unsupported extension: {path.name}")
        targets.append(pages_dir / f"{index}{suffix}")

    staging = Path(tempfile.mkdtemp(prefix=".pptd-rename-", dir=str(pages_dir)))
    try:
        for path in images:
            path.replace(staging / path.name)
        for name, target in zip(editor_names, targets):
            (staging / name).replace(target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return list(zip(targets, editor_names))


def label_font(image_font: Any) -> Any:
    try:
        return image_font.load_default(size=18)
    except TypeError:  # older Pillow without the size argument
        return image_font.load_default()


def stitch_overview(
    images: Sequence[Path],
    output: Path,
    image_cls: Any,
    draw_cls: Any,
    image_font: Any,
) -> Path:
    thumbs: List[Tuple[str, Any]] = []
    for index, path in enumerate(images, start=1):
        with image_cls.open(path) as opened:
            frame = opened.convert("RGB")
            ratio = OVERVIEW_THUMB_WIDTH / frame.width
            thumb = frame.resize(
                (OVERVIEW_THUMB_WIDTH, max(1, round(frame.height * ratio)))
            )
        thumbs.append((f"P{index}", thumb))

    columns = OVERVIEW_COLUMNS
    rows = math.ceil(len(thumbs) / columns)
    cell_height = OVERVIEW_LABEL_HEIGHT + max(thumb.height for _, thumb in thumbs)
    width = columns * OVERVIEW_THUMB_WIDTH + (columns + 1) * OVERVIEW_GAP
    height = rows * cell_height + (rows + 1) * OVERVIEW_GAP

    overview = image_cls.new("RGB", (width, height), "#e5e7eb")
    draw = draw_cls.Draw(overview)
    font = label_font(image_font)
    for position, (label, thumb) in enumerate(thumbs):
        column = position % columns
        row = position // columns
        x = OVERVIEW_GAP + column * (OVERVIEW_THUMB_WIDTH + OVERVIEW_GAP)
        y = OVERVIEW_GAP + row * (cell_height + OVERVIEW_GAP)
        draw.rectangle(
            (x, y, x + OVERVIEW_THUMB_WIDTH, y + OVERVIEW_LABEL_HEIGHT - 4),
            fill="#111827",
        )
        draw.text((x + 8, y + 5), label, fill="#ffffff", font=font)
        overview.paste(thumb, (x, y + OVERVIEW_LABEL_HEIGHT))

    overview.save(output, "JPEG", quality=85)
    return output


def evaluate_in_page(cdp_url: str, url_hint: str, expression: str) -> Any:
    socket = cdp_connect(cdp_url)
    try:
        targets = cdp_call(socket, 1, "Target.getTargets", {}).get("targetInfos", [])
        page_targets = [
            item
            for item in targets
            if item.get("type") == "page" and url_hint in str(item.get("url", ""))
        ]
        target = page_targets[0] if page_targets else next(
            (item for item in targets if url_hint in str(item.get("url", ""))),
            None,
        )
        if target is None:
            visible = ", ".join(
                f"{item.get('type')}:{str(item.get('url', ''))[:80]}" for item in targets
            )
            raise ExportError(
                f"no browser target matches {url_hint!r}; observed: {visible}"
            )
        attached = cdp_call(
            socket,
            2,
            "Target.attachToTarget",
            {"targetId": target["targetId"], "flatten": True},
        )
        session_id = attached["sessionId"]
        result = cdp_call(
            socket,
            3,
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
            session_id,
        )
        if result.get("exceptionDetails"):
            details = result["exceptionDetails"]
            raise ExportError(f"page script failed: {details.get('text')}")
        return result.get("result", {}).get("value")
    finally:
        socket.close()


def select_image_format(browser: BrowserSession) -> None:
    cdp_url = browser_cdp_url(browser)
    value = evaluate_in_page(cdp_url, PAGE_URL_HINT, IMAGE_FORMAT_CLICK_JS)
    if value != "clicked":
        raise ExportError("could not find the 图片 option in the export dialog")
    deadline = time.monotonic() + 10
    active = None
    while time.monotonic() < deadline:
        active = evaluate_in_page(cdp_url, PAGE_URL_HINT, ACTIVE_FORMAT_JS)
        if active == "图片":
            return
        time.sleep(0.3)
    raise ExportError(f"image format was not activated; active option: {active!r}")


def assert_disposable_output(output: Path) -> None:
    """Refuse to wipe anything that is not our own QA output directory.

    export_images replaces the output directory wholesale, and --output takes an
    arbitrary path; pointing it at the project itself must not delete the deck.
    """
    if not output.exists():
        return
    if not output.is_dir():
        raise ExportError(f"output must be a directory, not a file: {output}")
    # A .pptd manifest is the definitive marker; a pages/ directory only counts
    # when it holds .page files, since our own output also has pages/.
    protected = sorted(
        entry.name
        for entry in output.iterdir()
        if entry.suffix.lower() == ".pptd"
        or (entry.is_dir() and entry.name == "pages" and any(entry.glob("*.page")))
    )
    if protected:
        raise ExportError(
            f"refusing to replace {output}: it looks like a PPTD project "
            f"(contains {', '.join(protected)}). Point --output at a separate "
            "QA directory such as <project>/.qa-images"
        )


def export_images(
    source: Path,
    output: Path,
    force: bool = False,
) -> Dict[str, Any]:
    manifest = find_manifest(source)
    output = output.expanduser().resolve()
    assert_disposable_output(output)
    if output.exists() and any(output.iterdir()) and not force:
        raise ExportError(
            f"output directory already exists (pass --force to replace it): {output}"
        )
    agent_browser = ensure_agent_browser()
    # Same Windows debug-browser setup as the PPTX export path: agent-browser
    # cannot launch Chrome itself there, so image QA drives the same
    # registered, self-reclaiming browser instead of failing to start one.
    cdp_port = ensure_debug_chrome()
    image_cls, draw_cls, image_font = ensure_pillow()

    log(f"manifest: {manifest}")
    # One call so the payload and the host agree on how media is delivered.
    host, payload = open_local_editor(manifest)
    with EditorExportSession(
        agent_browser, host, session_prefix="pptd-images", cdp_port=cdp_port
    ) as session:
        dialog = open_export_dialog(session.browser)

        select_image_format(session.browser)
        dialog = wait_for_export_dialog(session.browser)

        log("rendering page images in the local editor")
        downloaded = session.download_from_dialog(
            dialog, accept=is_image_zip, click_timeout=300, find_timeout=240
        )

        # Everything below consumes `downloaded`, which lives inside the
        # session's temp directory, so it runs before the session exits.
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True)
        images = unzip_images(downloaded, output / "pages")
        page_paths = [entry["path"] for entry in payload["pages"]]
        if len(images) != len(page_paths):
            # The images are the QA input: a wrong image → .page mapping would
            # send the review in circles, so stop instead of warning.
            raise ExportError(
                f"the editor exported {len(images)} page image(s) for "
                f"{len(page_paths)} page(s); refusing to guess the mapping"
            )
        # pages/<n>.<ext> in deck order, so the P<n> label on the overview and
        # the file name on disk refer to the same page.
        named = canonical_page_names(images)
        images = [path for path, _ in named]
        try:
            if downloaded.resolve().parent == session.downloads.resolve():
                downloaded.unlink(missing_ok=True)
        except OSError:
            pass
        overview = stitch_overview(
            images, output / "overview.jpg", image_cls, draw_cls, image_font
        )

    mapping = [
        {
            "index": index,
            "overviewLabel": f"P{index}",
            "image": f"pages/{canonical.name}",
            "page": page_paths[index - 1],
            # The editor's own entry name, kept for cross-checking its ZIP.
            "editorImage": editor_name,
        }
        for index, (canonical, editor_name) in enumerate(named, start=1)
    ]
    return {
        "pages": len(images),
        "overview": str(overview),
        "output": str(output),
        "images": mapping,
        "exporter": "browser-local-editor",
        # How the deck's local media reached the editor: "host" means the payload
        # carried no base64 and the host served the files, "embedded" means the
        # old self-contained payload.
        "mediaDelivery": "host" if payload.get("mediaBase") else "embedded",
        # Media files the editor actually pulled from the host. A deck that
        # references images but reports 0 is rendering placeholders.
        "mediaRequests": host.media_requests,
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a PPTD project as page images via the local neo-ppt editor, unzip "
            "them, and stitch an overview image for visual QA."
        )
    )
    parser.add_argument("input", type=Path, help=".pptd manifest or project directory")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="output directory (default: <project>/.qa-images)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output directory",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        manifest = find_manifest(args.input)
        output = args.output or manifest.parent / ".qa-images"
        summary = export_images(args.input, output, args.force)
    except (ExportError, OSError, subprocess.SubprocessError) as exc:
        print(f"pptd image export failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
