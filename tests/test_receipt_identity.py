import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True

import archives
from safe_files import Files, SafetyError, digest


class ReceiptIdentity(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.files = Files(self.home)
        self.source = self.home / "fixture"

    def entry(self, format_name="raw"):
        if format_name == "raw":
            self.source.write_bytes(b"#!/bin/sh\nexit 0\n")
            artifact = {
                "url": "https://example.invalid/app",
                "sha256": digest(self.source.read_bytes()),
                "format": "raw",
                "filename": "bin/app",
            }
        else:
            with tarfile.open(self.source, "w") as archive:
                content = b"#!/bin/sh\nexit 0\n"
                info = tarfile.TarInfo("bin/app")
                info.size = len(content)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(content))
            artifact = {
                "url": "https://example.invalid/app.tar",
                "sha256": digest(self.source.read_bytes()),
                "commands": {"app": "bin/app"},
            }
        return {
            "id": "app",
            "method": "archive",
            "version": "1",
            "artifacts": {
                archives.machine_arch(): artifact,
                "unused-architecture": {
                    "url": "https://example.invalid/unused",
                    "sha256": "0" * 64,
                },
            },
            "commands": {"app": "bin/app"},
            "notes": "original",
            "name": "Original",
            "aliases": ["original"],
            "source": "https://example.invalid/docs",
        }

    def font_entry(self):
        with zipfile.ZipFile(self.source, "w") as archive:
            archive.writestr("fonts/Mono.ttf", b"font-data")
        return {
            "id": "font",
            "method": "font",
            "version": "1",
            "url": "https://example.invalid/font.zip",
            "sha256": digest(self.source.read_bytes()),
            "notes": "original",
            "name": "Original",
            "aliases": ["original"],
            "source": "https://example.invalid/docs",
        }

    def install(self, entry):
        def local_download(artifact, destination):
            destination.write_bytes(self.source.read_bytes())

        with patch.object(archives, "download", side_effect=local_download):
            self.assertEqual(archives.install(entry, self.files), [])
        self.assertTrue(archives.installed(entry, self.files))
        receipt = archives.read_receipt(entry, self.files)
        self.assertEqual(receipt["spec_version"], 1)
        return receipt

    def receipt_file(self, entry):
        return self.files.target(archives.receipt_path(entry))

    def save(self, entry, receipt):
        self.receipt_file(entry).write_text(json.dumps(receipt))

    def test_archive_raw_and_tar_metadata_are_not_deployment_identity(self):
        for kind in ("raw", "tar"):
            with self.subTest(kind=kind):
                entry = self.entry(kind)
                self.install(entry)
                edited = copy.deepcopy(entry)
                edited.update(
                    notes="different",
                    name="Changed",
                    aliases=["new"],
                    source="https://example.invalid/new-docs",
                )
                edited["artifacts"]["unused-architecture"]["sha256"] = "f" * 64
                self.assertTrue(archives.installed(edited, self.files))
                self.assertFalse(archives.needs_receipt_migration(edited, self.files))
                changed = copy.deepcopy(edited)
                changed["artifacts"][archives.machine_arch()]["url"] = (
                    "https://example.invalid/new-artifact"
                )
                self.assertFalse(archives.installed(changed, self.files))
                changed = copy.deepcopy(edited)
                changed["version"] = "2"
                self.assertFalse(archives.installed(changed, self.files))
                self.receipt_file(entry).unlink()

    def test_tar_defaults_and_override_precedence(self):
        entry = self.entry("tar")
        self.install(entry)
        equivalent = copy.deepcopy(entry)
        equivalent["artifacts"][archives.machine_arch()]["format"] = "tar"
        equivalent["commands"] = {"ignored": "other"}
        self.assertTrue(archives.installed(equivalent, self.files))
        for edit in (
            {"format": "raw", "filename": "bin/app"},
            {"commands": {"renamed": "bin/app"}},
        ):
            changed = copy.deepcopy(equivalent)
            changed["artifacts"][archives.machine_arch()].update(edit)
            self.assertFalse(archives.installed(changed, self.files))
        changed = copy.deepcopy(equivalent)
        changed["artifacts"][archives.machine_arch()]["sha256"] = "f" * 64
        self.assertFalse(archives.installed(changed, self.files))

    def test_raw_filename_and_effective_commands_are_meaningful(self):
        entry = self.entry()
        self.install(entry)
        equivalent = copy.deepcopy(entry)
        equivalent["artifacts"][archives.machine_arch()]["filename"] = "bin/./app"
        equivalent["commands"]["app"] = "bin/./app"
        equivalent["third_party"] = True
        self.assertTrue(archives.installed(equivalent, self.files))
        changed = copy.deepcopy(entry)
        changed["artifacts"][archives.machine_arch()]["filename"] = "bin/another"
        self.assertFalse(archives.installed(changed, self.files))
        changed = copy.deepcopy(entry)
        changed["commands"] = {"new": "bin/app"}
        self.assertFalse(archives.installed(changed, self.files))

    def test_selected_architecture_is_identity_even_with_identical_artifacts(self):
        entry = self.entry()
        self.install(entry)
        changed = copy.deepcopy(entry)
        changed["artifacts"]["other-architecture"] = copy.deepcopy(
            changed["artifacts"][archives.machine_arch()]
        )
        self.assertTrue(archives.installed(changed, self.files))
        with patch.object(archives, "machine_arch", return_value="other-architecture"):
            self.assertFalse(archives.installed(changed, self.files))

    def test_deployed_payload_and_executable_integrity(self):
        entry = self.entry()
        receipt = self.install(entry)
        payload = self.files.target(next(name for name in receipt["files"] if "/apps/" in name))
        payload.write_bytes(b"changed")
        self.assertFalse(archives.installed(entry, self.files))
        payload.write_bytes(self.source.read_bytes())
        payload.chmod(0o600)
        self.assertFalse(archives.installed(entry, self.files))
        payload.chmod(0o755)
        payload.unlink()
        self.assertFalse(archives.installed(entry, self.files))

    def test_font_payload_integrity_and_artifact_pin(self):
        entry = self.font_entry()
        receipt = self.install(entry)
        changed = copy.deepcopy(entry)
        changed["sha256"] = "f" * 64
        self.assertFalse(archives.installed(changed, self.files))
        font = self.files.target(next(iter(receipt["files"])))
        font.write_bytes(b"damaged-font")
        self.assertFalse(archives.installed(entry, self.files))
        font.unlink()
        self.assertFalse(archives.installed(entry, self.files))

    def test_font_metadata_and_pending_state_survive_legacy_migration(self):
        entry = self.font_entry()
        receipt = self.install(entry)
        retired = f"{archives.FONT_DIRECTORY}/Old.otf"
        receipt["retired"] = {retired: {"sha256": "1" * 64, "mode": 0o644}}
        receipt["cache_pending"] = True
        receipt.pop("spec_version")
        receipt["spec"] = digest(json.dumps(entry, sort_keys=True).encode())
        self.save(entry, receipt)
        before = self.receipt_file(entry).read_bytes()
        font = self.files.target(next(iter(receipt["files"])))
        original = font.stat().st_mtime_ns
        self.assertTrue(archives.installed(entry, self.files))
        self.assertTrue(archives.needs_receipt_migration(entry, self.files))
        self.assertEqual(self.receipt_file(entry).read_bytes(), before)
        archives.migrate_receipt(entry, self.files)
        migrated = archives.read_receipt(entry, self.files)
        self.assertEqual(migrated["retired"], receipt["retired"])
        self.assertTrue(migrated["cache_pending"])
        self.assertEqual(migrated["files"], receipt["files"])
        self.assertEqual(font.stat().st_mtime_ns, original)
        self.assertEqual(len(self.files.backups), 1)
        self.assertEqual(self.files.backups[0].read_bytes(), before)
        self.assertEqual(self.files.backups[0].stat().st_mode & 0o777, 0o600)
        changed = copy.deepcopy(entry)
        changed.update(
            notes="edited", name="New", aliases=[], source="https://example.invalid/other"
        )
        self.assertTrue(archives.installed(changed, self.files))
        self.assertFalse(archives.needs_receipt_migration(changed, self.files))
        with patch.object(archives, "machine_arch", return_value="other-architecture"):
            self.assertTrue(archives.installed(changed, self.files))
        archives.migrate_receipt(changed, self.files)
        self.assertEqual(len(self.files.backups), 1)
        changed["url"] = "https://example.invalid/other.zip"
        self.assertFalse(archives.installed(changed, self.files))

    def test_legacy_archive_migration_requires_exact_current_entry(self):
        entry = self.entry("tar")
        receipt = self.install(entry)
        receipt.pop("spec_version")
        receipt["spec"] = digest(json.dumps(entry, sort_keys=True).encode())
        self.save(entry, receipt)
        changed = copy.deepcopy(entry)
        changed["commands"] = {"different": "bin/app"}
        self.assertFalse(archives.installed(changed, self.files))
        self.assertFalse(archives.needs_receipt_migration(changed, self.files))
        with self.assertRaises(SafetyError):
            archives.migrate_receipt(changed, self.files)
        changed = copy.deepcopy(entry)
        changed["notes"] = "new"
        self.assertFalse(archives.installed(changed, self.files))
        self.assertTrue(archives.installed(entry, self.files))
        before = self.receipt_file(entry).read_bytes()
        archives.migrate_receipt(entry, self.files)
        self.assertEqual(self.files.backups[0].read_bytes(), before)
        self.assertTrue(archives.installed(changed, self.files))

    def test_legacy_archive_integrity_and_old_version_inventory(self):
        entry = self.entry()
        receipt = self.install(entry)
        receipt.pop("spec_version")
        receipt["spec"] = digest(json.dumps(entry, sort_keys=True).encode())
        self.save(entry, receipt)
        payload = self.files.target(next(name for name in receipt["files"] if "/apps/" in name))
        payload.write_bytes(b"corrupted")
        self.assertFalse(archives.installed(entry, self.files))
        self.assertFalse(archives.needs_receipt_migration(entry, self.files))
        with self.assertRaises(SafetyError):
            archives.migrate_receipt(entry, self.files)
        old = copy.deepcopy(receipt)
        old["files"] = {
            name.replace("/app/1/", "/app/old/"): record
            for name, record in receipt["files"].items()
        }
        self.save(entry, old)
        self.assertEqual(archives.read_receipt(entry, self.files)["files"], old["files"])
        self.assertFalse(archives.installed(entry, self.files))

    def test_legacy_font_missing_optional_metadata_keeps_defaults(self):
        entry = self.font_entry()
        receipt = self.install(entry)
        receipt.pop("spec_version")
        receipt.pop("retired")
        receipt.pop("cache_pending")
        receipt["spec"] = digest(json.dumps(entry, sort_keys=True).encode())
        self.save(entry, receipt)
        self.assertTrue(archives.needs_receipt_migration(entry, self.files))
        archives.migrate_receipt(entry, self.files)
        migrated = archives.read_receipt(entry, self.files)
        self.assertNotIn("retired", migrated)
        self.assertNotIn("cache_pending", migrated)
        self.assertTrue(archives.installed(entry, self.files))

    def test_unsupported_font_receipt_version_blocks_migration(self):
        entry = self.font_entry()
        receipt = self.install(entry)
        for version in (True, 2, None):
            with self.subTest(version=version):
                self.save(entry, dict(receipt, spec_version=version))
                with self.assertRaises(SafetyError):
                    archives.font_receipt(entry, self.files)
                with self.assertRaises(SafetyError):
                    archives.migrate_receipt(entry, self.files)

    def test_malformed_unsupported_and_unrelated_receipts_fail_closed(self):
        entry = self.entry()
        receipt = self.install(entry)
        examples = [
            dict(receipt, spec_version=True),
            dict(receipt, spec_version=2),
            dict(receipt, files={"/tmp/unrelated": {"sha256": "0" * 64, "mode": 0o600}}),
            dict(receipt, files={"other/path": {"sha256": "0" * 64, "mode": 0o600}}),
            dict(receipt, files={".local/bin/nested/command": {"sha256": "0" * 64, "mode": 0o600}}),
            dict(receipt, files={".local/bin/command": {"sha256": "bad", "mode": 0o600}}),
        ]
        for invalid in examples:
            with self.subTest(invalid=invalid):
                self.save(entry, invalid)
                with self.assertRaises(SafetyError):
                    archives.installed(entry, self.files)
                with self.assertRaises(SafetyError):
                    archives.migrate_receipt(entry, self.files)
                with patch.object(archives, "download") as download, self.assertRaises(SafetyError):
                    archives.install(entry, self.files)
                download.assert_not_called()
        self.receipt_file(entry).write_text("{broken")
        with self.assertRaises(SafetyError):
            archives.read_receipt(entry, self.files)

    def test_symlink_receipt_is_protected_during_read_and_migration(self):
        entry = self.entry()
        receipt = self.install(entry)
        external = self.home / "external-receipt"
        external.write_text(json.dumps(receipt))
        self.receipt_file(entry).unlink()
        self.receipt_file(entry).symlink_to(external)
        with self.assertRaises(SafetyError):
            archives.installed(entry, self.files)
        with self.assertRaises(SafetyError):
            archives.migrate_receipt(entry, self.files)
        self.assertEqual(json.loads(external.read_text()), receipt)


if __name__ == "__main__":
    unittest.main()
