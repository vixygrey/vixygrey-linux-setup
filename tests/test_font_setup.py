import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import setup
from safe_files import SafetyError, digest


class FontSetupSafety(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.binary = self.home / "bin"
        self.binary.mkdir()
        self.cache = self.binary / "fc-cache"
        self.set_cache_exit(0)
        environment = patch.dict(
            os.environ, {"HOME": str(self.home), "PATH": str(self.binary)}, clear=True
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.entry = next(entry for entry in setup.catalog() if entry["method"] == "font")
        source = self.root / "font.zip"
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("Regular.ttf", b"fixture regular")
        self.entry = self.entry | {"sha256": digest(source.read_bytes())}
        self.downloads = 0

        def download(artifact, destination):
            self.downloads += 1
            shutil.copyfile(source, destination)

        transport = patch.object(setup.archives, "download", side_effect=download)
        transport.start()
        self.addCleanup(transport.stop)
        self.app = setup.Setup(
            SimpleNamespace(replace=[], trust=[self.entry["id"]], profile=[], apps_only=True)
        )
        self.app.env["PATH"] = str(self.binary)
        self.app.selected = [self.entry]
        self.receipt = self.home / setup.archives.receipt_path(self.entry)

    def set_cache_exit(self, status):
        self.cache.write_text(
            f'#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/cache-calls"\nexit {status}\n'
        )
        self.cache.chmod(0o755)

    def apply(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.apply()

    def test_cache_failure_retries_without_downloading_or_redeploying_fonts(self):
        self.set_cache_exit(7)
        with self.assertRaises(SafetyError):
            self.apply()
        font = self.home / ".local/share/fonts/JetBrainsMonoNerd/Regular.ttf"
        metadata = font.stat()
        self.assertTrue(setup.archives.installed(self.entry, self.app.files))
        self.assertEqual(self.app.app_status(self.entry)["state"], "cache-pending")
        self.assertTrue(json.loads(self.receipt.read_text())["cache_pending"])
        self.entry = self.entry | {"notes": "Reworded documentation"}
        self.app.selected = [self.entry]
        self.set_cache_exit(0)
        self.apply()
        self.assertEqual(self.downloads, 1)
        self.assertEqual(font.stat().st_mtime_ns, metadata.st_mtime_ns)
        self.assertFalse(json.loads(self.receipt.read_text())["cache_pending"])
        self.assertEqual(self.app.app_status(self.entry)["state"], "installed")
        calls = (self.home / "cache-calls").read_text().splitlines()
        self.assertEqual(calls, [f"-f {font.parent.resolve()}"] * 2)
        self.apply()
        self.assertEqual((self.home / "cache-calls").read_text().splitlines(), calls)

    def test_missing_cache_remains_pending_until_tool_available(self):
        self.cache.unlink()
        with self.assertRaisesRegex(SafetyError, "fc-cache"):
            self.apply()
        status = self.app.app_status(self.entry)
        self.assertEqual(status["state"], "cache-pending")
        self.assertFalse(status["cache_available"])
        self.set_cache_exit(0)
        self.apply()
        self.assertEqual(self.downloads, 1)
        self.assertEqual(self.app.app_status(self.entry)["state"], "installed")

    def test_legacy_receipt_does_not_force_cache_rebuild(self):
        self.apply()
        receipt = json.loads(self.receipt.read_text())
        receipt.pop("cache_pending", None)
        receipt.pop("retired", None)
        self.receipt.write_text(json.dumps(receipt))
        before = (self.home / "cache-calls").read_bytes()
        self.apply()
        self.assertEqual(self.downloads, 1)
        self.assertEqual((self.home / "cache-calls").read_bytes(), before)

    def test_upgrade_preview_reports_local_changes_without_downloading_or_writing(self):
        self.apply()
        font = self.home / ".local/share/fonts/JetBrainsMonoNerd/Regular.ttf"
        font.write_bytes(b"personal font")
        self.app.selected = [self.entry | {"version": "next"}]
        before = {str(p): p.read_bytes() for p in self.home.rglob("*") if p.is_file()}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.app.steps.clear()
            self.app.plan()
        self.assertEqual(self.downloads, 1)
        self.assertEqual(
            {str(p): p.read_bytes() for p in self.home.rglob("*") if p.is_file()}, before
        )
        action = setup.action_records(self.app)[0]
        self.assertTrue(action["font_readiness"]["payload_preflight_required"])
        self.assertIn(
            {"path": ".local/share/fonts/JetBrainsMonoNerd/Regular.ttf", "state": "modified"},
            action["font_readiness"]["font_files"],
        )

    def test_unapproved_source_blocks_before_downloading(self):
        self.app.trust.clear()
        with self.assertRaises(SafetyError):
            self.apply()
        self.assertEqual(self.downloads, 0)
        self.assertFalse(self.receipt.exists())
        self.assertFalse((self.home / ".local/share/fonts").exists())

    def test_preview_blocks_symlink_font_directory_without_writes(self):
        outside = self.root / "outside"
        outside.mkdir()
        fonts = self.home / ".local/share/fonts"
        fonts.mkdir(parents=True)
        (fonts / "JetBrainsMonoNerd").symlink_to(outside, target_is_directory=True)
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.plan()
        self.assertTrue(self.app.blocks)
        self.assertEqual(self.downloads, 0)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(self.receipt.exists())


if __name__ == "__main__":
    unittest.main()
