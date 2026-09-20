#!/usr/bin/env python3
import functools
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import threading
import urllib.error
import urllib.request
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[3] / "pptd"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pptd_common  # noqa: E402  (path set up above)

SCRIPT = SCRIPTS_DIR / "export_pptx.py"
SPEC = importlib.util.spec_from_file_location("export_pptx", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ExportPptxTests(unittest.TestCase):
    def test_parse_agent_browser_version(self):
        self.assertEqual(MODULE.parse_version("agent-browser 0.33.2"), (0, 33, 2))
        self.assertEqual(MODULE.parse_version("v1.4.0-beta.1"), (1, 4, 0))

    @patch.object(MODULE, "run_command")
    @patch.object(MODULE.shutil, "which")
    def test_old_agent_browser_is_upgraded(self, which, run_command):
        which.side_effect = [
            "/bin/node",
            "/bin/npm",
            "/bin/agent-browser",
            "/bin/npm",
            "/bin/agent-browser",
        ]
        run_command.side_effect = [
            MODULE.subprocess.CompletedProcess([], 0, "v22.11.0\n"),
            MODULE.subprocess.CompletedProcess([], 0, "agent-browser 0.17.1\n"),
            MODULE.subprocess.CompletedProcess([], 0, "changed 1 package\n"),
            MODULE.subprocess.CompletedProcess([], 0, "agent-browser 0.33.2\n"),
        ]
        self.assertEqual(MODULE.ensure_agent_browser(), "/bin/agent-browser")
        self.assertEqual(run_command.call_args_list[2].args[0], [
            "/bin/npm", "install", "-g", "agent-browser@latest"
        ])

    @patch.object(MODULE, "run_command")
    @patch.object(MODULE.shutil, "which")
    def test_missing_nodejs_raises_clear_error(self, which, run_command):
        which.return_value = None
        with self.assertRaisesRegex(MODULE.ExportError, "Node.js is not installed"):
            MODULE.ensure_nodejs()
        run_command.assert_not_called()

    @patch.object(MODULE, "run_command")
    @patch.object(MODULE.shutil, "which")
    def test_old_nodejs_raises_clear_error(self, which, run_command):
        which.return_value = "/bin/node"
        run_command.return_value = MODULE.subprocess.CompletedProcess([], 0, "v16.20.2\n")
        with self.assertRaisesRegex(MODULE.ExportError, "Node.js 18\\+ is required"):
            MODULE.ensure_nodejs()

    @patch.object(MODULE, "run_command")
    @patch.object(MODULE.shutil, "which")
    def test_missing_npm_raises_clear_error(self, which, run_command):
        which.side_effect = ["/bin/node", None]
        run_command.return_value = MODULE.subprocess.CompletedProcess([], 0, "v22.11.0\n")
        with self.assertRaisesRegex(MODULE.ExportError, "npm is not installed"):
            MODULE.ensure_nodejs()

    def test_parse_node_version(self):
        self.assertEqual(MODULE.parse_node_version("v22.11.0"), (22, 11, 0))
        self.assertEqual(MODULE.parse_node_version("18.20.4"), (18, 20, 4))

    def test_fade_is_inserted_before_timing(self):
        source = (
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<p:sld xmlns:p="urn:test"><p:cSld><p:spTree><p:extLst/>'
            b'</p:spTree></p:cSld><p:clrMapOvr/><p:timing/><p:extLst/></p:sld>'
        )
        result_bytes = MODULE.replace_transition(source, "fade")
        result = result_bytes.decode("utf-8")
        self.assertIn("<p:transition", result)
        self.assertIn("<p:fade/>", result)
        self.assertGreater(result.index("<p:transition"), result.index("<p:clrMapOvr"))
        self.assertLess(result.index("<p:transition"), result.index("<p:timing"))
        MODULE.validate_transition_order(result_bytes, "fade")

    def test_existing_transition_is_replaced_or_removed(self):
        source = (
            b'<p:sld xmlns:p="urn:test"><p:cSld/>'
            b'<p:transition><p:wipe/></p:transition><p:extLst/></p:sld>'
        )
        faded = MODULE.replace_transition(source, "fade").decode("utf-8")
        self.assertNotIn("p:wipe", faded)
        self.assertEqual(faded.count("<p:transition"), 1)
        MODULE.validate_transition_order(faded.encode("utf-8"), "fade")
        cleared = MODULE.replace_transition(source, "none").decode("utf-8")
        self.assertNotIn("p:transition", cleared)
        MODULE.validate_transition_order(cleared.encode("utf-8"), "none")

    def test_nested_transition_is_relocated_to_slide_root(self):
        source = (
            b'<p:sld xmlns:p="urn:test"><p:cSld><p:spTree>'
            b'<p:transition><p:fade/></p:transition><p:extLst/>'
            b'</p:spTree></p:cSld><p:clrMapOvr/><p:extLst/></p:sld>'
        )
        result = MODULE.replace_transition(source, "fade")
        MODULE.validate_transition_order(result, "fade")
        self.assertEqual(MODULE.root_child_names(result), [
            "cSld", "clrMapOvr", "transition", "extLst"
        ])

    def test_patch_transitions_preserves_a_valid_zip(self):
        with tempfile.TemporaryDirectory() as name:
            deck = Path(name) / "test.pptx"
            with zipfile.ZipFile(deck, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                    '<Override PartName="/ppt/presentation.xml" '
                    f'ContentType="{MODULE.PPTX_CONTENT_TYPE}"/></Types>',
                )
                archive.writestr("ppt/presentation.xml", "<p:presentation xmlns:p=\"urn:test\"/>")
                archive.writestr(
                    "ppt/slides/slide1.xml",
                    '<p:sld xmlns:p="urn:test"><p:cSld/></p:sld>',
                )
            self.assertEqual(MODULE.patch_transitions(deck, "fade"), 1)
            with zipfile.ZipFile(deck) as archive:
                self.assertIsNone(archive.testzip())
                slide = archive.read("ppt/slides/slide1.xml")
                self.assertIn(b"<p:fade/>", slide)

    @patch.object(pptd_common.subprocess, "call", return_value=0)
    def test_run_command_captures_utf8_via_temp_file(self, call):
        def write_sink(*_args, **kwargs):
            kwargs["stdout"].write("agent-browser 0.33.2\n")
            return 0

        call.side_effect = write_sink
        process = MODULE.run_command(["agent-browser", "--version"], timeout=5)
        self.assertEqual(process.returncode, 0)
        self.assertIn("0.33.2", process.stdout)
        self.assertEqual(call.call_args.kwargs["stderr"], subprocess.STDOUT)

    def test_find_download_ignores_files_older_than_since(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            old = root / "old.pptx"
            new = root / "new.pptx"
            for path in (old, new):
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr(
                        "[Content_Types].xml",
                        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                        '<Override PartName="/ppt/presentation.xml" '
                        f'ContentType="{MODULE.PPTX_CONTENT_TYPE}"/></Types>',
                    )
                    archive.writestr("ppt/presentation.xml", "<p:presentation/>")

            older = time.time() - 60
            os.utime(old, (older, older))
            since = time.time() - 5
            found = MODULE.find_download([root], timeout=2.0, since=since)
            self.assertEqual(found.resolve(), new.resolve())

    def test_find_download_survives_files_vanishing_mid_scan(self):
        # Chrome renames "*.crdownload" files away between directory listing
        # and stat(); a vanished file must be skipped, not crash the export.
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            deck = root / "deck.pptx"
            with zipfile.ZipFile(deck, "w") as archive:
                archive.writestr(
                    "[Content_Types].xml",
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                    '<Override PartName="/ppt/presentation.xml" '
                    f'ContentType="{MODULE.PPTX_CONTENT_TYPE}"/></Types>',
                )
                archive.writestr("ppt/presentation.xml", "<p:presentation/>")
            ghost = root / "ghost.crdownload"
            ghost.write_bytes(b"partial download")

            real_stat = Path.stat
            seen = {"count": 0}

            def racy_stat(self, **kwargs):
                if self.name == "ghost.crdownload":
                    seen["count"] += 1
                    if seen["count"] > 1:
                        raise FileNotFoundError(2, "vanished mid-scan", str(self))
                return real_stat(self, **kwargs)

            with patch.object(Path, "stat", racy_stat):
                found = MODULE.find_download([root], timeout=2.0)
            self.assertEqual(found.resolve(), deck.resolve())

    def test_browser_open_does_not_pass_download_path(self):
        session = MODULE.BrowserSession(
            "/bin/agent-browser",
            "test-session",
            Path("."),
            Path("/tmp/downloads"),
        )
        with patch.object(session, "run") as run:
            session.open("http://127.0.0.1:9/?ndExport=1")
        run.assert_called_once_with(
            ["open", "http://127.0.0.1:9/?ndExport=1"],
            timeout=90,
        )

    def test_ensure_debug_chrome_is_windows_only(self):
        with patch.object(MODULE.sys, "platform", "linux"):
            self.assertIsNone(MODULE.ensure_debug_chrome())

    @patch.object(MODULE, "cdp_alive", return_value=True)
    def test_ensure_debug_chrome_prefers_working_explicit_port(self, cdp_alive):
        with patch.object(MODULE.sys, "platform", "win32"), \
                patch.dict(MODULE.os.environ, {"AGENT_BROWSER_CDP": "9444"}):
            self.assertEqual(MODULE.ensure_debug_chrome(), 9444)
        cdp_alive.assert_called_once_with(9444)

    def test_image_map_only_embeds_referenced_media(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "media").mkdir()
            (root / "media" / "used.png").write_bytes(b"\x89PNG\r\n\x1a\n used")
            (root / "media" / "orphan.png").write_bytes(b"\x89PNG\r\n\x1a\n orphan")
            # The visual-QA loop writes page renders here, inside the project.
            (root / ".qa-images" / "pages").mkdir(parents=True)
            (root / ".qa-images" / "pages" / "1.jpeg").write_bytes(b"\xff\xd8\xff qa")

            pages = [{
                "elements": [
                    {"elementType": "image", "src": "media/used.png"},
                    {"elementType": "shape", "fill": {"type": "image", "src": "media/used.png"}},
                    {"elementType": "image", "src": "https://example.com/remote.png"},
                ],
            }]
            image_map = MODULE.build_image_map(root, pages)

        self.assertEqual(list(image_map), ["media/used.png"])
        self.assertTrue(image_map["media/used.png"].startswith("data:image/png;base64,"))

    def test_image_map_rejects_paths_outside_the_project(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            pages = [{"elements": [{"elementType": "image", "src": "../secret.png"}]}]
            with self.assertRaisesRegex(MODULE.ExportError, "escapes the PPTD directory"):
                MODULE.build_image_map(root, pages)

    def test_deck_errors_do_not_fall_back_to_the_browser(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "deck.pptd").write_text(
                "version: v2\npages:\n  - pages/missing.page\n", encoding="utf-8"
            )
            with patch.object(MODULE, "ensure_agent_browser") as agent_browser:
                with self.assertRaisesRegex(MODULE.ExportError, "missing page file"):
                    MODULE.export_pptx(
                        root, root / "out.pptx", "fade", False, prefer_local=True
                    )
            agent_browser.assert_not_called()

    def test_missing_local_toolchain_still_falls_back(self):
        self.assertTrue(issubclass(MODULE.LocalExportUnavailable, MODULE.ExportError))
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with patch.object(MODULE, "export_pptx_local") as local, \
                    patch.object(MODULE, "build_payload", return_value={}), \
                    patch.object(MODULE, "find_manifest", return_value=root / "d.pptd"), \
                    patch.object(MODULE, "ensure_agent_browser") as agent_browser:
                local.side_effect = MODULE.LocalExportUnavailable("node missing")
                agent_browser.side_effect = RuntimeError("reached the browser path")
                with self.assertRaisesRegex(RuntimeError, "reached the browser path"):
                    MODULE.export_pptx(
                        root, root / "out.pptx", "fade", False, prefer_local=True
                    )

    def test_browser_session_exports_cdp_port_to_env(self):
        with patch.dict(MODULE.os.environ, {}, clear=False):
            MODULE.os.environ.pop("AGENT_BROWSER_CDP", None)
            with_port = MODULE.BrowserSession(
                "/bin/agent-browser", "s", Path("."), Path("/tmp/d"), cdp_port=9337
            )
            self.assertEqual(with_port.env["AGENT_BROWSER_CDP"], "9337")
            without_port = MODULE.BrowserSession(
                "/bin/agent-browser", "s", Path("."), Path("/tmp/d")
            )
            self.assertNotIn("AGENT_BROWSER_CDP", without_port.env)


class EditorHostMediaRouteTests(unittest.TestCase):
    """The export host serves the deck's media instead of embedding it."""

    def make_deck(self, root: Path) -> Path:
        (root / "pages").mkdir()
        (root / "media").mkdir()
        (root / "media" / "shot.png").write_bytes(bytes([0x89]) + b"PNG shot-bytes")
        (root / "media" / "font.ttf").write_bytes(b"font-bytes")
        (root / "deck.pptd").write_text(
            chr(10).join([
                "version: v2",
                "title: Media Host",
                "size: [960, 540]",
                "pages:",
                "  - pages/01.page",
                "",
            ]),
            encoding="utf-8",
        )
        (root / "pages" / "01.page").write_text(
            chr(10).join([
                "pageType: content",
                "elements:",
                "  - elementId: pic",
                "    elementType: image",
                "    bounds: [0, 0, 10, 10]",
                "    src: media/shot.png",
                "    fit: {mode: contain}",
                "",
            ]),
            encoding="utf-8",
        )
        return root / "deck.pptd"

    def test_media_is_served_not_embedded(self):
        with tempfile.TemporaryDirectory() as name:
            manifest = self.make_deck(Path(name))
            payload = MODULE.build_payload(manifest)
            # Default: no base64 in the payload at all.
            self.assertEqual(payload["imageMap"], {})

            server, _thread, url = MODULE.serve_local_editor(payload, project_root=manifest.parent)
            try:
                base = url.split("?")[0]
                body = urllib.request.urlopen(base + "payload.json", timeout=10).read()
                self.assertNotIn(b"base64", body)
                self.assertEqual(json.loads(body)["mediaBase"], f"/{MODULE.MEDIA_MOUNT}/")

                # The editor asks for some assets with a leading slash.
                for request in ("media/shot.png", "/media/shot.png", "//media/shot.png"):
                    served = urllib.request.urlopen(f"{base}{MODULE.MEDIA_MOUNT}/{request}", timeout=10)
                    self.assertEqual(served.read(), bytes([0x89]) + b"PNG shot-bytes")
                font = urllib.request.urlopen(f"{base}{MODULE.MEDIA_MOUNT}/media/font.ttf", timeout=10)
                self.assertEqual(font.read(), b"font-bytes")
                self.assertGreaterEqual(server.media_hits["count"], 3)
            finally:
                server.shutdown()
                server.server_close()

    def test_media_route_refuses_escapes_and_other_types(self):
        with tempfile.TemporaryDirectory() as name:
            manifest = self.make_deck(Path(name))
            payload = MODULE.build_payload(manifest)
            server, _thread, url = MODULE.serve_local_editor(payload, project_root=manifest.parent)
            try:
                base = url.split("?")[0]
                for request, expected in (
                    ("../deck.pptd", 403),
                    ("..%2fdeck.pptd", 403),
                    ("pages/01.page", 404),
                    ("missing.png", 404),
                ):
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(f"{base}{MODULE.MEDIA_MOUNT}/{request}", timeout=10)
                    self.assertEqual(caught.exception.code, expected, request)
            finally:
                server.shutdown()
                server.server_close()

    def test_without_a_project_root_the_payload_embeds_media(self):
        with tempfile.TemporaryDirectory() as name:
            manifest = self.make_deck(Path(name))
            payload = MODULE.build_payload(manifest, embed_media=True)
            self.assertTrue(payload["imageMap"])
            self.assertNotIn("mediaBase", payload)
            server, _thread, url = MODULE.serve_local_editor(payload)
            try:
                base = url.split("?")[0]
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(f"{base}{MODULE.MEDIA_MOUNT}/media/shot.png", timeout=10)
                self.assertEqual(caught.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()

    def test_open_local_editor_agrees_with_its_host(self):
        with tempfile.TemporaryDirectory() as name:
            manifest = self.make_deck(Path(name))
            server, _thread, url, payload = MODULE.open_local_editor(manifest)
            try:
                self.assertIn("mediaBase", payload)
                base = url.split("?")[0]
                served = urllib.request.urlopen(f"{base}{MODULE.MEDIA_MOUNT}/media/shot.png", timeout=10)
                self.assertEqual(served.read(), bytes([0x89]) + b"PNG shot-bytes")
            finally:
                server.shutdown()
                server.server_close()


class LocalExportEndToEndTests(unittest.TestCase):
    """Exercises the real Node + patched-WASM path, including the --json handoff."""

    FIXTURE = Path(__file__).resolve().parent / "fixtures" / "minimal"

    @unittest.skipUnless(MODULE.shutil.which("node"), "node is required")
    def test_exports_a_pptx_without_a_node_yaml_package(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "deck.pptx"
            summary = MODULE.export_pptx_local(self.FIXTURE, output, "fade")
            self.assertTrue(output.is_file())
            self.assertEqual(summary["exporter"], "local-wasm-patched")
            self.assertEqual(summary["slides"], summary["fadeTransitions"])
            with zipfile.ZipFile(output) as archive:
                self.assertIn("ppt/presentation.xml", archive.namelist())

    def test_build_local_project_shape(self):
        project = MODULE.build_local_project(self.FIXTURE / "minimal.pptd")
        self.assertEqual(project["manifest"]["version"], "v2")
        self.assertTrue(project["pages"])
        for page in project["pages"]:
            self.assertIsInstance(page["path"], str)
            self.assertIsInstance(page["data"]["elements"], list)

class DebugChromeRegistryTests(unittest.TestCase):
    """The browser registry decides what may be reclaimed — no browser needed."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.registry = Path(temporary.name) / "pptd-cdp.json"
        patcher = patch.object(MODULE, "CDP_REGISTRY_PATH", self.registry)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_register_touch_and_read_back(self):
        MODULE.write_cdp_registry(
            [
                {
                    "port": 9337,
                    "pid": 4242,
                    "profile": str(MODULE.DEBUG_CHROME_PROFILE),
                    "startedAt": 10.0,
                    "lastUsedAt": 20.0,
                }
            ]
        )
        entry = MODULE.registered_debug_chrome(9337)
        self.assertEqual(entry["pid"], 4242)
        MODULE.touch_cdp_registry(9337)
        self.assertGreater(MODULE.registered_debug_chrome(9337)["lastUsedAt"], 20.0)
        self.assertIsNone(MODULE.registered_debug_chrome(9444))

    def test_signature_rejects_foreign_or_recycled_pids(self):
        profile = str(MODULE.DEBUG_CHROME_PROFILE)
        # Our own python pid: it is not a browser, so the signature fails early.
        self.assertIsNone(MODULE.process_image_name(os.getpid()))
        self.assertFalse(MODULE.debug_chrome_is_ours({"pid": os.getpid(), "profile": profile}))
        # A browser the user started by hand: different profile.
        self.assertFalse(MODULE.debug_chrome_is_ours({"pid": os.getpid(), "profile": "/tmp/somewhere-else"}))
        self.assertIsNone(MODULE.process_image_name(None))

    def test_signature_requires_our_command_line(self):
        profile = str(MODULE.DEBUG_CHROME_PROFILE)
        entry = {"pid": 4321, "profile": profile}
        # Chrome relaunches itself with the path quoted; we spawn it unquoted.
        ours = (
            f'chrome.exe --user-data-dir="{profile}"',
            f"chrome.exe --user-data-dir={profile}",
        )
        # A recycled pid now owned by somebody else's browser, and an empty line.
        theirs = ('chrome.exe --user-data-dir="C:/Users/someone/else"', "")
        with patch.object(MODULE, "process_image_name", return_value="chrome.exe"):
            for command in ours:
                with patch.object(MODULE, "process_command_line", return_value=command):
                    self.assertTrue(MODULE.debug_chrome_is_ours(entry), command)
            for command in theirs:
                with patch.object(MODULE, "process_command_line", return_value=command):
                    self.assertFalse(MODULE.debug_chrome_is_ours(entry), command)
            # Unreadable command line: leave it alone instead of guessing.
            with patch.object(MODULE, "process_command_line", return_value=None):
                self.assertFalse(MODULE.debug_chrome_is_ours(entry))

    def test_reap_reclaims_only_signed_idle_instances(self):
        MODULE.write_cdp_registry(
            [
                {
                    "port": 9337,
                    "pid": 111,
                    "profile": str(MODULE.DEBUG_CHROME_PROFILE),
                    "startedAt": 0,
                    "lastUsedAt": 0,
                },
                {"port": 9444, "pid": 222, "profile": "/tmp/foreign-profile", "startedAt": 0, "lastUsedAt": 0},
            ]
        )
        attempted = []

        def fake_kill(entry):
            attempted.append(entry["port"])
            # The real kill_debug_chrome decides by signature; mirror that here.
            return os.path.basename(str(entry.get("profile", ""))) == "pptd-cdp-profile"

        with patch.object(MODULE, "cdp_alive", return_value=True), \
                patch.object(MODULE, "kill_debug_chrome", side_effect=fake_kill):
            reaped = MODULE.reap_idle_debug_chrome(idle_minutes=1)

        self.assertEqual(attempted, [9337, 9444])
        self.assertEqual([entry["port"] for entry in reaped], [9337])
        self.assertEqual([entry["port"] for entry in MODULE.read_cdp_registry()], [9444])

    def test_reap_keeps_recently_used_instances(self):
        now = time.time()
        MODULE.write_cdp_registry(
            [
                {
                    "port": 9337,
                    "pid": 111,
                    "profile": str(MODULE.DEBUG_CHROME_PROFILE),
                    "startedAt": now,
                    "lastUsedAt": now - 30,
                }
            ]
        )
        with patch.object(MODULE, "cdp_alive", return_value=True), \
                patch.object(MODULE, "kill_debug_chrome") as kill:
            self.assertEqual(MODULE.reap_idle_debug_chrome(idle_minutes=60), [])
        kill.assert_not_called()

    def test_reap_can_be_disabled(self):
        MODULE.write_cdp_registry(
            [
                {
                    "port": 9337,
                    "pid": 111,
                    "profile": str(MODULE.DEBUG_CHROME_PROFILE),
                    "startedAt": 0,
                    "lastUsedAt": 0,
                }
            ]
        )
        with patch.object(MODULE, "cdp_alive", return_value=True), \
                patch.object(MODULE, "kill_debug_chrome") as kill:
            self.assertEqual(MODULE.reap_idle_debug_chrome(idle_minutes=0), [])
        kill.assert_not_called()

    def test_missing_registry_is_not_an_error(self):
        self.assertEqual(MODULE.read_cdp_registry(), [])
        self.assertEqual(MODULE.reap_idle_debug_chrome(idle_minutes=1), [])


@unittest.skipUnless(MODULE.sys.platform == "win32", "the debug browser path is Windows-only")
class DebugChromeLifecycleTests(unittest.TestCase):
    """Drive the real spawn → register → reuse → reclaim cycle."""

    PORT = 47731

    @staticmethod
    def chromium() -> Optional[str]:
        override = os.environ.get("PPTD_TEST_CHROMIUM")
        candidates = [override] if override else []
        candidates.extend(MODULE.CHROME_CANDIDATES)
        candidates.extend(
            str(path)
            for path in sorted(Path.home().glob("AppData/Local/ms-playwright/chromium-*/chrome-win64/chrome.exe"))
        )
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return candidate
        return None

    def test_start_reuse_and_reclaim(self):
        chromium = self.chromium()
        if not chromium:
            self.skipTest("no Chrome/Chromium executable available")

        with tempfile.TemporaryDirectory() as name:
            registry = Path(name) / "pptd-cdp.json"
            profile = Path(name) / "pptd-cdp-profile"
            with patch.object(MODULE, "CDP_REGISTRY_PATH", registry), \
                    patch.object(MODULE, "DEBUG_CHROME_PROFILE", profile), \
                    patch.object(MODULE, "CHROME_CANDIDATES", (chromium,)), \
                    patch.dict(
                        MODULE.os.environ,
                        {"PPTD_DEBUG_CHROME_PORT": str(self.PORT), "PPTD_DEBUG_CHROME_IDLE_MINUTES": "60"},
                    ):
                try:
                    self.assertEqual(MODULE.ensure_debug_chrome(), self.PORT)
                    self.assertTrue(MODULE.cdp_alive(self.PORT))
                    entry = MODULE.registered_debug_chrome(self.PORT)
                    self.assertIsNotNone(entry, "a browser we start must be registered")
                    self.assertEqual(entry["profile"], str(profile))
                    self.assertIsNotNone(entry["pid"])
                    self.assertIsNotNone(
                        MODULE.process_image_name(entry["pid"]),
                        "the registered pid must look like a browser",
                    )
                    pid = entry["pid"]

                    # Reuse: same port, same process, no second browser.
                    self.assertEqual(MODULE.ensure_debug_chrome(), self.PORT)
                    self.assertEqual(MODULE.registered_debug_chrome(self.PORT)["pid"], pid)

                    # Reclaim: force ignores the idle age.
                    reaped = MODULE.reap_idle_debug_chrome(force=True)
                    self.assertEqual([item["port"] for item in reaped], [self.PORT])
                    self.assertFalse(MODULE.cdp_alive(self.PORT))
                    self.assertIsNone(MODULE.registered_debug_chrome(self.PORT))
                finally:
                    MODULE.reap_idle_debug_chrome(force=True)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@unittest.skipUnless(MODULE.sys.platform == "win32", "the debug browser path is Windows-only")
class DownloadRedirectTests(unittest.TestCase):
    """The export ZIP must land in our directory, not in the user's Downloads."""

    @staticmethod
    def chromium() -> Optional[str]:
        override = os.environ.get("PPTD_TEST_CHROMIUM")
        candidates = [override] if override else []
        candidates.extend(MODULE.CHROME_CANDIDATES)
        candidates.extend(
            str(path)
            for path in sorted(Path.home().glob("AppData/Local/ms-playwright/chromium-*/chrome-win64/chrome.exe"))
        )
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return candidate
        return None

    def test_download_lands_in_the_redirected_directory(self):
        chromium = self.chromium()
        if not chromium:
            self.skipTest("no Chrome/Chromium executable available")

        port = free_port()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
            root = Path(name)
            profile = root / "profile"
            downloads = root / "downloads"
            downloads.mkdir()
            (root / "payload.txt").write_text("pptd-download-redirect", encoding="utf-8")
            (root / "page.html").write_text(
                '<a id="go" href="payload.txt" download="payload.txt">download</a>',
                encoding="utf-8",
            )
            # The editor is always reached over http; Chromium does not perform
            # downloads triggered from a file:// page, so serve one here too.
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                http_port = probe.getsockname()[1]
            handler = functools.partial(SimpleHTTPRequestHandler, directory=str(root))
            origin = ThreadingHTTPServer(("127.0.0.1", http_port), handler)
            threading.Thread(target=origin.serve_forever, daemon=True).start()
            self.addCleanup(origin.shutdown)
            process = subprocess.Popen(
                [
                    chromium,
                    f"--user-data-dir={profile}",
                    f"--remote-debugging-port={port}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline and not MODULE.cdp_alive(port):
                    time.sleep(0.5)
                self.assertTrue(MODULE.cdp_alive(port), "browser did not open a CDP port")

                version = json.loads(
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=10).read()
                )
                debugger_url = version["webSocketDebuggerUrl"]

                # A BrowserSession stand-in: only browser_cdp_url() is needed.
                browser = MODULE.BrowserSession.__new__(MODULE.BrowserSession)
                browser.executable = ""
                browser.session = "test"
                browser.cwd = root
                browser.download_dir = downloads
                browser.env = dict(os.environ)
                browser.run = lambda args, **kwargs: subprocess.CompletedProcess(
                    args, 0, "cdp-url: " + debugger_url + "\n", ""
                )
                redirect = MODULE.set_download_behavior(browser, downloads)
                self.assertIsNotNone(
                    redirect,
                    "the download redirect should succeed against a live CDP browser",
                )
                # The redirect lives on this socket: closing it drops the setting.
                self.addCleanup(redirect.close)

                cdp_socket = MODULE.cdp_connect(debugger_url)
                try:
                    targets = MODULE.cdp_call(cdp_socket, 1, "Target.getTargets", {}).get("targetInfos", [])
                    page = next((t for t in targets if t.get("type") == "page"), None)
                    self.assertIsNotNone(page, "browser exposed no page target")
                    attached = MODULE.cdp_call(
                        cdp_socket, 2, "Target.attachToTarget", {"targetId": page["targetId"], "flatten": True}
                    )
                    session = attached["sessionId"]
                    MODULE.cdp_call(
                        cdp_socket,
                        3,
                        "Page.navigate",
                        {"url": f"http://127.0.0.1:{http_port}/page.html"},
                        session,
                    )
                    # Wait for the link to exist before clicking: Page.navigate
                    # resolves when the navigation starts, not when it finishes.
                    def anchor_ready() -> bool:
                        result = MODULE.cdp_call(
                            cdp_socket,
                            4,
                            "Runtime.evaluate",
                            {
                                "expression": "Boolean(document.getElementById('go'))",
                                "returnByValue": True,
                            },
                            session,
                        )
                        return bool(result.get("result", {}).get("value"))

                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline and not anchor_ready():
                        time.sleep(0.3)
                    self.assertTrue(anchor_ready(), "the test page never became interactive")
                    MODULE.cdp_call(
                        cdp_socket,
                        5,
                        "Runtime.evaluate",
                        {"expression": "document.getElementById('go').click()", "returnByValue": True},
                        session,
                    )
                finally:
                    cdp_socket.close()

                deadline = time.monotonic() + 20
                downloaded = None
                while time.monotonic() < deadline and downloaded is None:
                    candidates = list(downloads.glob("payload*"))
                    downloaded = candidates[0] if candidates else None
                    if downloaded is None:
                        time.sleep(0.5)
                self.assertIsNotNone(downloaded, f"nothing arrived in {downloads}")
                self.assertEqual(downloaded.read_text(encoding="utf-8"), "pptd-download-redirect")
            finally:
                for pid in (process.pid, MODULE.find_debug_chrome_pid(port)):
                    if pid:
                        subprocess.run(
                            ["taskkill", "/pid", str(pid), "/T", "/F"],
                            capture_output=True,
                            text=True,
                            timeout=30,
                        )
                # The profile lives inside the temp dir: let the browser release
                # its files before the directory is removed.
                deadline = time.monotonic() + 15
                cdp_pid = MODULE.find_debug_chrome_pid(port)
                while time.monotonic() < deadline and cdp_pid and MODULE.process_image_name(cdp_pid) is not None:
                    time.sleep(0.5)
                process.poll()


if __name__ == "__main__":
    unittest.main()
