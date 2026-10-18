import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True

import archives
from safe_files import Files, SafetyError


class FontArchives(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.fonts = self.home / archives.FONT_DIRECTORY
        self.receipt = self.home / archives.receipt_path({"id": "font"})
        self.sources = self.home / "sources"
        self.sources.mkdir()
        self.source = None
        downloader = patch.object(archives, "download", side_effect=self.download)
        downloader.start()
        self.addCleanup(downloader.stop)

    def download(self, artifact, destination):
        destination.write_bytes(self.source.read_bytes())
        self.assertEqual(hashlib.sha256(destination.read_bytes()).hexdigest(), artifact["sha256"])

    def release(self, *members):
        source = self.sources / f"{len(list(self.sources.iterdir()))}.zip"
        with warnings.catch_warnings(), zipfile.ZipFile(source, "w") as archive:
            warnings.simplefilter("ignore", UserWarning)
            for name, data in members:
                archive.writestr(name, data)
        self.source = source
        return {
            "id": "font",
            "method": "font",
            "url": "https://example.invalid/font.zip",
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }

    def path(self, name):
        return f"{archives.FONT_DIRECTORY}/{name}"

    def deploy(self, entry, replacements=()):
        files = Files(self.home, replacements)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            conflicts = archives.install(entry, files)
        return conflicts, files, output.getvalue()

    def test_nonfont_archive_members_are_not_installed(self):
        entry = self.release(
            ("install.sh", b"exit 1"), ("fonts/Regular.ttf", b"font"), ("README.md", b"text")
        )
        self.assertEqual(self.deploy(entry)[0], [])
        self.assertEqual(
            {path.name: path.read_bytes() for path in self.fonts.iterdir()},
            {"Regular.ttf": b"font"},
        )

    def test_first_repeat_and_explicit_upgrade_with_backups(self):
        first = self.release(("fonts/Regular.ttf", b"first"))
        self.assertEqual(self.deploy(first)[0], [])
        self.assertTrue(archives.installed(first, Files(self.home)))
        before = self.receipt.read_bytes()
        self.assertEqual(self.deploy(first)[0], [])
        self.assertEqual(self.receipt.read_bytes(), before)
        second = self.release(("Regular.ttf", b"second"), ("Bold.otf", b"bold"))
        conflicts, _, guidance = self.deploy(second)
        self.assertEqual(conflicts, [self.path("Regular.ttf")])
        self.assertIn(f"--replace {self.path('Regular.ttf')}", guidance)
        self.assertFalse((self.fonts / "Bold.otf").exists())
        self.assertEqual(self.receipt.read_bytes(), before)
        conflicts, files, _ = self.deploy(second, [self.path("Regular.ttf")])
        self.assertEqual(conflicts, [])
        self.assertEqual((self.fonts / "Regular.ttf").read_bytes(), b"second")
        self.assertEqual((self.fonts / "Bold.otf").read_bytes(), b"bold")
        self.assertEqual(
            [backup.read_bytes() for backup in files.backups if backup.name == "Regular.ttf"],
            [b"first"],
        )
        self.assertTrue(archives.installed(second, Files(self.home)))
        self.assertTrue(archives.font_receipt(second, Files(self.home))["cache_pending"])

    def test_partial_consent_collects_conflicts_without_any_mutations(self):
        first = self.release(("A.ttf", b"old-a"), ("B.ttf", b"old-b"))
        self.deploy(first)
        old_receipt = self.receipt.read_bytes()
        second = self.release(("A.ttf", b"new-a"), ("B.ttf", b"new-b"), ("C.ttf", b"new-c"))
        conflicts, files, guidance = self.deploy(second, [self.path("A.ttf")])
        self.assertEqual(conflicts, [self.path("B.ttf")])
        self.assertIn(f"--replace {self.path('B.ttf')}", guidance)
        self.assertEqual((self.fonts / "A.ttf").read_bytes(), b"old-a")
        self.assertFalse((self.fonts / "C.ttf").exists())
        self.assertEqual(self.receipt.read_bytes(), old_receipt)
        self.assertFalse(files.backups)

    def test_user_modified_and_unmanaged_bytes_need_exact_approval(self):
        old = self.release(("A.ttf", b"original"))
        self.deploy(old)
        (self.fonts / "A.ttf").write_bytes(b"user-edited")
        (self.fonts / "B.ttf").write_bytes(b"unmanaged")
        replacement = self.release(("A.ttf", b"upstream"), ("B.ttf", b"upstream-b"))
        before = self.receipt.read_bytes()
        blocked, _, _ = self.deploy(replacement)
        self.assertEqual(blocked, [self.path("A.ttf"), self.path("B.ttf")])
        self.assertEqual(self.receipt.read_bytes(), before)
        blocked, _, _ = self.deploy(replacement, [self.path("A.ttf")])
        self.assertEqual(blocked, [self.path("B.ttf")])
        self.assertEqual((self.fonts / "A.ttf").read_bytes(), b"user-edited")
        self.assertEqual((self.fonts / "B.ttf").read_bytes(), b"unmanaged")
        _, files, _ = self.deploy(replacement, [self.path("A.ttf"), self.path("B.ttf")])
        self.assertEqual(
            {backup.read_bytes() for backup in files.backups if backup.suffix == ".ttf"},
            {b"user-edited", b"unmanaged"},
        )

    def test_destination_symlinks_and_ancestor_are_protected_even_with_consent(self):
        first = self.release(("A.ttf", b"new"), ("B.ttf", b"new-b"))
        self.fonts.mkdir(parents=True)
        outside = self.home / "outside"
        outside.write_bytes(b"untouched")
        (self.fonts / "A.ttf").symlink_to(outside)
        blocked, _, guidance = self.deploy(first, [self.path("A.ttf")])
        self.assertEqual(blocked, [self.path("A.ttf")])
        self.assertIn("protected", guidance)
        self.assertFalse((self.fonts / "B.ttf").exists())
        self.assertEqual(outside.read_bytes(), b"untouched")
        (self.fonts / "A.ttf").unlink()
        self.fonts.rmdir()
        self.fonts.symlink_to(self.sources, target_is_directory=True)
        blocked, _, _ = self.deploy(first, [self.path("A.ttf"), self.path("B.ttf")])
        self.assertEqual(blocked, [self.path("A.ttf"), self.path("B.ttf")])
        self.assertFalse((self.sources / "A.ttf").exists())
        self.assertFalse(self.receipt.exists())

    def test_receipt_symlink_preflight_blocks_all_writes(self):
        first = self.release(("A.ttf", b"new"))
        self.receipt.parent.mkdir(parents=True)
        self.receipt.symlink_to(self.home / "not-a-receipt")
        blocked, _, guidance = self.deploy(first)
        self.assertEqual(blocked, [archives.receipt_path(first)])
        self.assertIn("protected", guidance)
        self.assertFalse((self.fonts / "A.ttf").exists())

    def test_last_moment_put_refusal_never_commits_receipt(self):
        entry = self.release(("A.ttf", b"new"))
        files = Files(self.home)
        original_put = files.put

        def refuse(relative, data, mode=0o600):
            if relative == self.path("A.ttf"):
                return "protected"
            return original_put(relative, data, mode)

        with patch.object(files, "put", side_effect=refuse), self.assertRaises(SafetyError):
            archives.install(entry, files)
        self.assertFalse(self.receipt.exists())

    def test_save_receipt_rejects_protected_path(self):
        entry = self.release(("A.ttf", b"new"))
        self.deploy(entry)
        receipt = archives.font_receipt(entry, Files(self.home))
        self.receipt.unlink()
        self.receipt.symlink_to(self.home / "outside")
        with self.assertRaises(SafetyError):
            archives.save_font_receipt(entry, Files(self.home), receipt)
        self.assertFalse((self.home / "outside").exists())

    def test_late_invalid_members_precede_all_home_mutations(self):
        for name in ("../escape.ttf", "dir/A.ttf"):
            with self.subTest(name=name):
                bad = self.release(("A.ttf", b"first"), (name, b"late"))
                with self.assertRaises(SafetyError):
                    self.deploy(bad)
                self.assertFalse((self.fonts / "A.ttf").exists())
                self.assertFalse(self.receipt.exists())

    def test_legacy_receipt_retirement_provenance_and_active_validity(self):
        old = self.release(("A.ttf", b"a"), ("B.otf", b"b"))
        self.deploy(old)
        legacy = archives.font_receipt(old, Files(self.home))
        legacy.pop("cache_pending")
        legacy.pop("retired")
        self.receipt.write_text(json.dumps(legacy))
        self.assertTrue(archives.installed(old, Files(self.home)))
        middle = self.release(("A.ttf", b"a"), ("C.ttf", b"c"))
        self.assertEqual(self.deploy(middle)[0], [])
        receipt = archives.font_receipt(middle, Files(self.home))
        self.assertEqual(
            receipt["retired"], {self.path("B.otf"): legacy["files"][self.path("B.otf")]}
        )
        self.assertEqual((self.fonts / "B.otf").read_bytes(), b"b")
        (self.fonts / "B.otf").write_bytes(b"user edit")
        self.assertTrue(archives.installed(middle, Files(self.home)))
        last = self.release(("C.ttf", b"c"))
        self.assertEqual(self.deploy(last)[0], [])
        retained = archives.font_receipt(last, Files(self.home))["retired"]
        self.assertEqual(retained[self.path("B.otf")], legacy["files"][self.path("B.otf")])
        self.assertEqual(retained[self.path("A.ttf")], legacy["files"][self.path("A.ttf")])
        (self.fonts / "B.otf").unlink()
        (self.fonts / "A.ttf").unlink()
        self.assertTrue(archives.installed(last, Files(self.home)))

    def test_malformed_receipts_fail_closed(self):
        entry = self.release(("A.ttf", b"a"))
        self.deploy(entry)
        for corrupt in (
            "not json",
            json.dumps({"sha256": "x"}),
            json.dumps(
                {
                    **archives.font_receipt(entry, Files(self.home)),
                    "retired": {
                        ".local/share/fonts/JetBrainsMonoNerd/../escape.ttf": {
                            "sha256": "0" * 64,
                            "mode": 420,
                        }
                    },
                }
            ),
        ):
            with self.subTest(corrupt=corrupt):
                self.receipt.write_text(corrupt)
                with self.assertRaises(SafetyError):
                    archives.font_receipt(entry, Files(self.home))
                with self.assertRaises(SafetyError):
                    self.deploy(entry)
