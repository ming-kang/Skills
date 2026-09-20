#!/usr/bin/env python3
import importlib.util
import os
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from typing import Optional
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[3] / "pptd"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

SPEC = importlib.util.spec_from_file_location("export_images", SCRIPTS_DIR / "export_images.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def make_images_zip(path: Path, names=("1.jpeg", "10.jpeg", "2.jpeg")) -> None:
    # 1x1 white JPEG, the smallest valid payload Pillow can open.
    import base64

    pixel = base64.b64decode(
        "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////"
        "////////////////////////////////////////////2wBDAf//////////////////"
        "////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB"
        "/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMB"
        "AAIQAxAAAAGf/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAA"
        "AAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgB"
        "AgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAA"
        "AAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABCf/8QAFBEBAAAAAAAAAAAA"
        "AAAAAAAAAP/aAAgBAwEPEBB//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEPEBB/"
        "/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxB//9k="
    )
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, pixel)


class ExportImagesTests(unittest.TestCase):
    def test_unzip_images_keeps_zip_entry_order(self):
        """Page order comes from the ZIP, not from guessing file names."""
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            archive_path = root / "images.zip"
            # Entry order is the deck order; the numeric stems lie about it.
            make_images_zip(archive_path, names=("cover.jpeg", "10.jpeg", "2.jpeg", "1.jpeg"))
            images = MODULE.unzip_images(archive_path, root / "pages")
            self.assertEqual(
                [path.name for path in images],
                ["cover.jpeg", "10.jpeg", "2.jpeg", "1.jpeg"],
            )

    def test_unzip_images_flattens_nested_entries(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            archive_path = root / "images.zip"
            make_images_zip(archive_path, names=("pages/1.jpeg", "note.txt", "pages/2.jpeg"))
            images = MODULE.unzip_images(archive_path, root / "pages")
            self.assertEqual(
                [path.name for path in images], ["1.jpeg", "2.jpeg"]
            )

    def test_is_image_zip_accepts_image_entries_only(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            good = root / "images.zip"
            make_images_zip(good)
            self.assertTrue(MODULE.is_image_zip(good))

            bad = root / "text.zip"
            with zipfile.ZipFile(bad, "w") as archive:
                archive.writestr("readme.txt", "hello")
            self.assertFalse(MODULE.is_image_zip(bad))
            self.assertFalse(MODULE.is_image_zip(root / "missing.zip"))

    def test_stitch_overview_grid(self):
        try:
            image_cls, draw_cls, image_font = MODULE.ensure_pillow()
        except MODULE.ExportError:
            self.skipTest("Pillow is not available")
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            images = []
            for index in range(1, 5):
                path = root / f"{index}.jpeg"
                image = image_cls.new("RGB", (320, 180), (index * 40 % 255, 30, 60))
                image.save(path, "JPEG")
                images.append(path)
            overview = MODULE.stitch_overview(
                images, root / "overview.jpg", image_cls, draw_cls, image_font
            )
            self.assertTrue(overview.is_file())
            with image_cls.open(overview) as result:
                self.assertEqual(
                    result.width,
                    3 * MODULE.OVERVIEW_THUMB_WIDTH + 4 * MODULE.OVERVIEW_GAP,
                )
                rows = 2
                cell = MODULE.OVERVIEW_LABEL_HEIGHT + 360
                self.assertEqual(result.height, rows * cell + (rows + 1) * MODULE.OVERVIEW_GAP)


class DisposableOutputTests(unittest.TestCase):
    def test_refuses_to_replace_a_pptd_project(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "deck.pptd").write_text("version: v2\n", encoding="utf-8")
            (root / "pages").mkdir()
            with self.assertRaisesRegex(MODULE.ExportError, "looks like a PPTD project"):
                MODULE.assert_disposable_output(root)

    def test_rejects_a_file_output(self):
        with tempfile.TemporaryDirectory() as name:
            target = Path(name) / "overview.jpg"
            target.write_bytes(b"x")
            with self.assertRaisesRegex(MODULE.ExportError, "must be a directory"):
                MODULE.assert_disposable_output(target)

    def test_allows_a_qa_directory(self):
        with tempfile.TemporaryDirectory() as name:
            qa = Path(name) / ".qa-images"
            (qa / "pages").mkdir(parents=True)
            (qa / "overview.jpg").write_bytes(b"x")
            MODULE.assert_disposable_output(qa)  # must not raise

    def test_allows_a_missing_directory(self):
        with tempfile.TemporaryDirectory() as name:
            MODULE.assert_disposable_output(Path(name) / "nope")


@unittest.skipUnless(MODULE.sys.platform == "win32", "the browser QA path is Windows-only")
class ExportImagesEndToEndTests(unittest.TestCase):
    """Drive the real editor, dialog, download and stitching pipeline.

    Needs `agent-browser` on PATH and any Chrome/Chromium; both are optional
    runtime dependencies, so the test skips itself when they are missing.
    """

    DECK = Path(__file__).resolve().parents[3] / "tools" / "pptd" / "tests" / "fixtures" / "qa-deck" / "deck.pptd"

    @staticmethod
    def chromium() -> Optional[str]:
        candidates = [
            os.environ.get("PPTD_TEST_CHROMIUM"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            str(Path.home() / "AppData/Local/Google/Chrome/Application/chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
        candidates.extend(
            str(path)
            for path in sorted(Path.home().glob("AppData/Local/ms-playwright/chromium-*/chrome-win64/chrome.exe"))
        )
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return candidate
        return None

    def test_exports_and_stitches_every_page(self):
        import shutil as shutil_module

        if not shutil_module.which("agent-browser"):
            self.skipTest("agent-browser is not installed")
        chromium = self.chromium()
        if not chromium:
            self.skipTest("no Chrome/Chromium executable available")
        if not self.DECK.is_file():
            self.skipTest(f"missing fixture: {self.DECK}")

        import socket
        import subprocess
        import tempfile

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
            root = Path(name)
            process = subprocess.Popen(
                [
                    chromium,
                    f"--user-data-dir={root / 'profile'}",
                    f"--remote-debugging-port={port}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                from export_pptx import cdp_alive, find_debug_chrome_pid, process_image_name

                deadline = time.monotonic() + 30
                while time.monotonic() < deadline and not cdp_alive(port):
                    time.sleep(0.5)
                self.assertTrue(cdp_alive(port), "browser did not open a CDP port")

                environment = dict(os.environ)
                environment["AGENT_BROWSER_CDP"] = str(port)
                with patch.dict(MODULE.os.environ, environment):
                    output = root / "qa"
                    summary = MODULE.export_images(self.DECK, output, force=True)

                pages = [entry["path"] for entry in MODULE.build_payload(self.DECK)["pages"]]
                self.assertEqual(summary["pages"], len(pages))
                self.assertTrue((output / "overview.jpg").is_file())
                self.assertEqual(
                    [entry["page"] for entry in summary["images"]],
                    pages,
                    "image → .page mapping must follow the deck order",
                )
                for entry in summary["images"]:
                    self.assertTrue((output / entry["image"]).is_file())
            finally:
                import subprocess as subprocess_module

                pid = find_debug_chrome_pid(port)
                subprocess_module.run(
                    ["taskkill", "/pid", str(pid or 0), "/T", "/F"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline and pid and process_image_name(pid) is not None:
                    time.sleep(0.5)
                process.poll()


if __name__ == "__main__":
    unittest.main()
