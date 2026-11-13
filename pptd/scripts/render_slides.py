#!/usr/bin/env python3
"""Optional local PPTX -> PNG rendering; rendering is not visual acceptance."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

MANIFEST = "render-manifest.json"
FORMAT = "pptd-render-v1"
COMMAND_TIMEOUT = 180
POWERSHELL_SCRIPT = Path(__file__).resolve().with_name("render_powerpoint.ps1")


class RenderError(RuntimeError):
    pass


class Unavailable(RenderError):
    pass


def powerpoint_command() -> str | None:
    """Probe registration and the executable, without activating COM/Office."""
    if os.name != "nt" or not POWERSHELL_SCRIPT.is_file():
        return None
    shell = shutil.which("powershell.exe")
    if not shell:
        return None
    import winreg

    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"PowerPoint.Application\CLSID", 0,
                                winreg.KEY_READ | view) as key:
                clsid = winreg.QueryValueEx(key, None)[0]
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"CLSID\{clsid}\LocalServer32", 0,
                                winreg.KEY_READ | view) as key:
                command = winreg.QueryValueEx(key, None)[0]
            match = re.match(r'^\s*(?:"([^"]+\.exe)"|(.+?\.exe))(?:\s|$)', command, re.I)
            if match and Path(os.path.expandvars(match[1] or match[2])).is_file():
                return shell
        except OSError:
            continue
    return None


def libreoffice_command() -> str | None:
    for name in ("soffice.com", "soffice", "libreoffice"):
        command = shutil.which(name)
        if command:
            return command
    candidates = [Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
                  Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice"]
    if os.name == "nt":
        candidates = [Path(os.environ[root]) / "LibreOffice/program" / executable
                      for root in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")
                      if os.environ.get(root)
                      for executable in ("soffice.com", "soffice.exe")]
    return next((str(path) for path in candidates if path.is_file() and os.access(path, os.X_OK)), None)


def pdf_renderer():
    # Optional on both Office paths: direct PowerPoint PNG export substitutes embedded fonts.
    for name in ("pymupdf", "fitz"):
        if importlib.util.find_spec(name) is not None:
            try:
                module = importlib.import_module(name)
                if all(hasattr(module, attr) for attr in ("open", "Matrix", "VersionBind")):
                    return module
            except (ImportError, OSError) as exc:
                raise Unavailable(f"font-faithful PDF -> PNG review needs usable optional PyMuPDF: {exc}") from exc
    raise Unavailable("font-faithful Office PDF -> PNG review needs optional PyMuPDF")


def choose_engine(requested: str):
    if requested in ("auto", "powerpoint"):
        shell = powerpoint_command()
        if shell:
            return "powerpoint", shell, pdf_renderer()
        if requested == "powerpoint":
            raise Unavailable("PowerPoint rendering needs installed PowerPoint and Windows PowerShell on Windows")
    command = libreoffice_command()
    if not command:
        raise Unavailable("No local rendering engine available: LibreOffice is not installed or discoverable"
                          + ("; PowerPoint is unavailable" if requested == "auto" else ""))
    return "libreoffice", command, pdf_renderer()


def run_command(command: Sequence[str], label: str, timeout: int = COMMAND_TIMEOUT,
                kill_tree: bool = False) -> str:
    process = subprocess.Popen([str(part) for part in command], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, encoding="utf-8", errors="replace",
                               start_new_session=(os.name != "nt"),
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
    try:
        output, _ = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        # Only the isolated LibreOffice conversion owns a process tree. Never kill Office globally.
        if kill_tree and os.name == "nt":
            try:
                subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
            except (OSError, subprocess.SubprocessError):
                pass
        elif kill_tree:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()  # Our command process only, not PowerPoint's COM server.
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            if process.stdout:
                process.stdout.close()
        message = f"{label} interrupted" if isinstance(exc, KeyboardInterrupt) else f"{label} timed out after {timeout}s"
        raise RenderError(message) from exc
    if process.returncode:
        raise RenderError(f"{label} failed ({process.returncode}):\n{output[-4000:].strip()}")
    return output


def render_powerpoint(source: Path, stage: Path, work: Path, width: int, shell: str, pdf_module) -> None:
    session = work / "powerpoint-session.json"
    pdf_dir = work / "powerpoint-pdf"
    pdf_dir.mkdir()
    command = [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
               "-File", str(POWERSHELL_SCRIPT), "-Pptx", str(source), "-OutDir", str(pdf_dir),
               "-Width", str(width), "-SessionFile", str(session)]
    try:
        run_command(command, "PowerPoint rendering")
    except (RenderError, OSError):
        # A timeout cannot execute the worker's finally. Try a fresh COM client, scoped by
        # recorded application PID and target path; never start or forcibly stop Office here.
        if session.is_file():
            try:
                run_command(command + ["-Cleanup"], "PowerPoint cleanup", timeout=20)
            except (RenderError, OSError) as exc:
                print(f"[pptd render] {exc}; Office was not forcibly stopped", file=sys.stderr)
        raise
    pdf = pdf_dir / "slides.pdf"
    if not pdf.is_file():
        raise RenderError("PowerPoint did not produce a font-faithful PDF")
    rasterize_pdf(pdf, stage, width, pdf_module)


def rasterize_pdf(pdf: Path, stage: Path, width: int, pdf_module) -> None:
    try:
        with pdf_module.open(str(pdf)) as document:
            for index, page in enumerate(document):
                if page.rect.width <= 0 or page.rect.height <= 0:
                    raise RenderError(f"PDF page {index + 1} has an invalid canvas")
                scale = width / page.rect.width
                pixmap = page.get_pixmap(matrix=pdf_module.Matrix(scale, scale), alpha=False)
                pixmap.save(str(stage / f"slide-{index + 1:03}.png"))
    except Exception as exc:
        raise RenderError(f"PDF rasterization failed: {exc}") from exc


def render_libreoffice(source: Path, stage: Path, work: Path, width: int, command: str, pdf_module) -> None:
    local_source = work / "deck.pptx"
    shutil.copy2(source, local_source)
    pdf_dir = work / "pdf"
    pdf_dir.mkdir()
    profile = work / "lo-profile"
    run_command([command, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--nologo",
                 "--nodefault", "--norestore", "--convert-to", "pdf:impress_pdf_Export",
                 "--outdir", str(pdf_dir), str(local_source)], "LibreOffice conversion", kill_tree=True)
    pdf = pdf_dir / "deck.pdf"
    if not pdf.is_file():
        raise RenderError("LibreOffice did not produce a PDF")
    rasterize_pdf(pdf, stage, width, pdf_module)


def inspect_output(output: Path, force: bool):
    """Only an empty directory or an exact helper-managed file set can be used."""
    if output.is_symlink() or (os.name == "nt" and output.exists()
                              and output.lstat().st_file_attributes & 0x400):
        raise RenderError(f"output must not be a symlink/junction: {output}")
    if output == Path(output.anchor) or output == Path.home().resolve():
        raise RenderError(f"refusing a filesystem root or home directory: {output}")
    if output.suffix.lower() in {".pptd", ".page", ".pptx"}:
        raise RenderError(f"output must be a render directory, not a source-material path: {output}")
    if not output.exists():
        return None, []
    if not output.is_dir():
        raise RenderError(f"output is not a directory: {output}")
    children = list(output.iterdir())
    if any(not path.is_file() or path.is_symlink() or
           (os.name == "nt" and path.lstat().st_file_attributes & 0x400) for path in children):
        raise RenderError("output contains unrelated directories or links; choose an empty render directory")
    names = {path.name for path in children}
    if names:
        manifest = output / MANIFEST
        try:
            if not manifest.is_file() or manifest.stat().st_size > 1024 * 1024:
                raise ValueError("missing or oversized managed manifest")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            slides = metadata["slides"]
            if (metadata["format"] != FORMAT or not isinstance(slides, list) or not slides
                    or slides != [f"slide-{i + 1:03}.png" for i in range(len(slides))]
                    or names != set(slides) | {MANIFEST}):
                raise ValueError("not an exact managed file set")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise RenderError("output contains unrelated/source material or is not helper-managed; "
                              "--force never deletes such directories") from exc
        if not force:
            raise RenderError(f"output already contains renders (pass --force to replace them): {output}")
    snapshot = (output.stat().st_ino,
                tuple(sorted((path.name, path.stat().st_ino, path.stat().st_size, path.stat().st_mtime_ns)
                             for path in children)))
    return snapshot, sorted(names)


def publish(stage: Path, output: Path, expected, force: bool) -> None:
    current, old_names = inspect_output(output, force)
    if current != expected:
        raise RenderError("output changed while rendering; no files were replaced")
    output.parent.mkdir(parents=True, exist_ok=True)
    backup = output.parent / (stage.parent.name + "-previous")
    if current is not None:
        if backup.exists():
            raise RenderError(f"temporary backup path already exists: {backup}")
        output.rename(backup)
    try:
        if current is not None and inspect_output(backup, True)[0] != expected:
            raise RenderError("output changed during publication; no files were replaced")
        # Staging is on the output filesystem, so this publishes all slides and the manifest together.
        stage.rename(output)
    except (OSError, RenderError, KeyboardInterrupt) as exc:
        if current is not None:
            try:
                backup.rename(output)
            except OSError as restore_error:
                raise RenderError(f"publication failed; prior output preserved at {backup}: {restore_error}") from exc
        raise
    if current is not None:
        # This backup is OUTSIDE TemporaryDirectory: unexpected concurrent user files must survive.
        # Never recursively wipe a user directory. Remove only our recorded generated file set.
        try:
            for name in old_names:
                (backup / name).unlink()
            backup.rmdir()
        except OSError as exc:
            print(f"[pptd render] rendered, but prior-output cleanup needs attention at {backup}: {exc}",
                  file=sys.stderr)


def render(source: Path, output: Path, engine: str, command: str, pdf_module, width: int,
           force: bool, expected) -> dict:
    ancestor = output.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    if not ancestor.is_dir():
        raise RenderError(f"output parent is not a directory: {ancestor}")
    with tempfile.TemporaryDirectory(prefix=".pptd-render-", dir=ancestor) as temporary:
        work = Path(temporary)
        stage = work / "slides"
        stage.mkdir()
        if engine == "powerpoint":
            render_powerpoint(source, stage, work, width, command, pdf_module)
        else:
            render_libreoffice(source, stage, work, width, command, pdf_module)
        names = [f"slide-{i + 1:03}.png" for i in range(len(list(stage.iterdir())))]
        if not names or {path.name for path in stage.iterdir()} != set(names):
            raise RenderError("renderer did not produce a complete numbered PNG slide set")
        for name in names:
            with (stage / name).open("rb") as image:
                header = image.read(24)
            if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
                raise RenderError(f"renderer produced an invalid PNG: {name}")
            pixel_width, pixel_height = struct.unpack(">II", header[16:24])
            if abs(pixel_width - width) > 1 or not pixel_height:
                raise RenderError(f"renderer produced unexpected PNG dimensions: {name}")
        metadata = {"format": FORMAT, "engine": engine, "source": str(source), "width": width, "slides": names}
        (stage / MANIFEST).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        publish(stage, output, expected, force)
    return {"status": "rendered", "engine": engine, "output": str(output),
            "slides": [str(output / name) for name in names], "manifest": str(output / MANIFEST)}


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="local .pptx to render (read-only)")
    parser.add_argument("--output", "-o", type=Path, required=True, help="empty or helper-managed render directory")
    parser.add_argument("--engine", choices=("auto", "powerpoint", "libreoffice"), default="auto",
                        help="auto: local PowerPoint first, otherwise LibreOffice; both use optional PyMuPDF for PDF -> PNG")
    parser.add_argument("--if-available", action="store_true", help="report skipped/exit 0 if dependencies are unavailable")
    parser.add_argument("--force", action="store_true", help="replace only an existing helper-managed render set")
    parser.add_argument("--width", type=int, default=1600, help="PNG width in pixels; height preserves canvas ratio (default: 1600)")
    args = parser.parse_args(argv)
    try:
        source = args.input.expanduser().resolve()
        if not source.is_file() or source.suffix.lower() != ".pptx":
            raise RenderError(f"input must be an existing local .pptx: {source}")
        if not 1 <= args.width <= 16384:
            raise RenderError("--width must be between 1 and 16384 pixels")
        # Check the caller's path before resolve() follows a link/junction.
        inspect_output(args.output.expanduser().absolute(), args.force)
        output = args.output.expanduser().resolve()
        expected, _ = inspect_output(output, args.force)
        try:
            engine, command, pdf_module = choose_engine(args.engine)
        except Unavailable as exc:
            if not args.if_available:
                raise
            print(json.dumps({"status": "skipped", "engine": args.engine, "reason": str(exc)}, ensure_ascii=False, indent=2))
            return 0
        result = render(source, output, engine, command, pdf_module, args.width, args.force, expected)
    except KeyboardInterrupt:
        print("[pptd render] interrupted", file=sys.stderr)
        return 130
    except (RenderError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"[pptd render] {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
