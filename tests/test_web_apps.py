import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import setup
from safe_files import SafetyError


class WebAppSafety(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        binary = self.home / "bin"
        binary.mkdir()
        self.opener = binary / "xdg-open"
        self.opener.write_text('#!/bin/sh\n/usr/bin/touch "$HOME/browser-was-launched"\nexit 97\n')
        self.opener.chmod(0o755)
        environment = patch.dict(
            os.environ, {"HOME": str(self.home), "PATH": str(binary)}, clear=True
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.entry = next(entry for entry in setup.catalog() if entry["id"] == "notion")
        self.args = SimpleNamespace(
            replace=[], trust=["notion"], profile=[], apps_only=True, desktop=False
        )
        self.application = setup.Setup(self.args)
        self.application.env["PATH"] = str(binary)
        self.application.selected = [self.entry]
        self.launcher = self.home / ".local/share/applications/vixygrey-notion.desktop"

    def apply(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.application.apply()

    def test_preview_requires_source_approval_without_writes(self):
        self.application.trust.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            self.application.plan()
        self.assertTrue(any("--trust notion" in blocker for blocker in self.application.blocks))
        self.assertEqual(sorted(path.name for path in self.home.iterdir()), ["bin"])

    def test_provisioning_is_idempotent_and_preserves_personal_changes(self):
        self.assertEqual(self.application.app_status(self.entry)["state"], "missing")
        self.apply()
        self.assertEqual(self.application.app_status(self.entry)["state"], "installed")
        modified = self.launcher.stat().st_mtime_ns
        self.apply()
        self.assertEqual(self.launcher.stat().st_mtime_ns, modified)
        self.launcher.write_text("[Desktop Entry]\nName=My Notion\n")
        self.apply()
        self.assertEqual(self.launcher.read_text(), "[Desktop Entry]\nName=My Notion\n")
        self.assertEqual(self.application.app_status(self.entry)["state"], "command-conflict")
        self.assertFalse((self.home / "browser-was-launched").exists())

    def test_missing_browser_opener_blocks_even_an_existing_launcher(self):
        self.apply()
        self.opener.unlink()
        self.assertFalse(self.application.is_installed(self.entry))
        self.assertEqual(self.application.app_status(self.entry)["state"], "blocked")
        with self.assertRaises(SafetyError):
            self.apply()
        self.assertTrue(self.launcher.is_file())

    def test_replacement_consent_does_not_follow_launcher_symlinks(self):
        target = self.home / "personal.desktop"
        target.write_text("personal launcher\n")
        self.launcher.parent.mkdir(parents=True)
        self.launcher.symlink_to(target)
        self.application.files.replacements.add(".local/share/applications/vixygrey-notion.desktop")
        self.apply()
        self.assertTrue(self.launcher.is_symlink())
        self.assertEqual(target.read_text(), "personal launcher\n")
        self.assertEqual(self.application.app_status(self.entry)["state"], "command-conflict")

    def test_web_catalog_rejects_non_https_targets_and_launcher_injection(self):
        for url in ["file:///tmp/note", "javascript:alert(1)", "http://example.com", "https://"]:
            with self.subTest(url=url), self.assertRaises(SafetyError):
                setup.validate_catalog([self.entry | {"package": url}])
        with self.assertRaises(SafetyError):
            setup.validate_catalog([self.entry | {"name": "Notion\nExec=unwanted"}])


if __name__ == "__main__":
    unittest.main()
