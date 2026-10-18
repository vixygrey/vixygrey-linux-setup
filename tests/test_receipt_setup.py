import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import setup
from safe_files import SafetyError, digest


def legacy_receipt(path, entry):
    receipt = json.loads(path.read_text())
    receipt.pop("spec_version")
    receipt["spec"] = digest(json.dumps(entry, sort_keys=True).encode())
    path.write_text(json.dumps(receipt))
    return receipt


class ReceiptSetup(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.binary = self.home / "bin"
        self.binary.mkdir()
        environment = patch.dict(
            os.environ, {"HOME": str(self.home), "PATH": str(self.binary)}, clear=True
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.downloads = 0
        self.source = self.root / "fixture.tar"

        def download(artifact, destination):
            self.downloads += 1
            shutil.copyfile(self.source, destination)
            self.assertEqual(digest(destination.read_bytes()), artifact["sha256"])

        transport = patch.object(setup.archives, "download", side_effect=download)
        transport.start()
        self.addCleanup(transport.stop)

    def select(self, entry, *, trust=True):
        self.entry = entry
        self.app = setup.Setup(
            SimpleNamespace(
                replace=[], trust=[entry["id"]] if trust else [], profile=[], apps_only=True
            )
        )
        self.app.env["PATH"] = str(self.binary)
        self.app.selected = [entry]
        self.receipt = self.home / setup.archives.receipt_path(entry)

    def apply(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.apply()

    def preview(self):
        self.app.steps.clear()
        self.app.blocks.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.plan()
        return setup.action_records(self.app)

    def snapshot(self):
        return {
            str(path.relative_to(self.home)): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.home.rglob("*")
            if path.is_file()
        }

    def archive(self):
        self.source = self.root / "fixture.tar"
        with tarfile.open(self.source, "w") as archive:
            for name, data in (
                ("bin/fixture", b"#!/bin/sh\nexit 0\n"),
                ("bin/alternate", b"#!/bin/sh\nexit 1\n"),
            ):
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(data))
        entry = {
            "id": "fixture-archive",
            "name": "Fixture archive",
            "method": "archive",
            "package": "fixture-archive",
            "version": "1.0",
            "source": "https://example.invalid/release",
            "notes": "Original description",
            "third_party": True,
            "artifacts": {
                setup.archives.machine_arch(): {
                    "url": "https://example.invalid/fixture.tar",
                    "sha256": digest(self.source.read_bytes()),
                    "format": "tar",
                }
            },
            "commands": {"fixture-command": "bin/fixture"},
        }
        self.select(entry)
        return entry

    def font(self, *names):
        self.source = self.root / f"font-{len(list(self.root.glob('font-*.zip')))}.zip"
        with zipfile.ZipFile(self.source, "w") as archive:
            for name in names:
                archive.writestr(name, name.encode())
        entry = {
            "id": "fixture-font",
            "name": "Fixture font",
            "method": "font",
            "package": "fixture-font",
            "version": "1.0",
            "source": "https://example.invalid/fonts",
            "notes": "Original description",
            "third_party": True,
            "url": "https://example.invalid/font.zip",
            "sha256": digest(self.source.read_bytes()),
        }
        self.select(entry)
        return entry

    def set_cache_exit(self, status):
        cache = self.binary / "fc-cache"
        cache.write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/cache-calls"\nexit {status}\n')
        cache.chmod(0o755)

    def test_archive_legacy_migrates_only_on_apply_without_redeploy(self):
        entry = self.archive()
        self.apply()
        payload = self.home / ".local/share/vixygrey/apps/fixture-archive/1.0/bin/fixture"
        wrapper = self.home / ".local/bin/fixture-command"
        self.assertEqual(payload.read_bytes(), b"#!/bin/sh\nexit 0\n")
        self.assertTrue(os.access(payload, os.X_OK))
        self.assertEqual(subprocess.run([str(wrapper)], check=False).returncode, 0)
        self.assertTrue(os.access(wrapper, os.X_OK))
        old = legacy_receipt(self.receipt, entry)
        before = self.snapshot()
        self.assertTrue(setup.archives.needs_receipt_migration(entry, self.app.files))
        self.assertEqual(self.app.status_document()["apps"][0]["state"], "installed")
        actions = self.preview()
        self.assertEqual([action["kind"] for action in actions], ["receipt-migrate"])
        self.assertEqual(actions[0]["id"], entry["id"])
        self.assertFalse(self.app.blocks)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.downloads, 1)

        self.apply()
        migrated = json.loads(self.receipt.read_text())
        self.assertEqual(migrated["spec_version"], setup.archives.SPEC_VERSION)
        self.assertEqual(migrated["files"], old["files"])
        self.assertEqual([backup.name for backup in self.app.files.backups], [self.receipt.name])
        self.assertEqual(json.loads(self.app.files.backups[0].read_text()), old)
        for deployed in (payload, wrapper):
            relative = str(deployed.relative_to(self.home))
            self.assertEqual(self.snapshot()[relative], before[relative])
        self.assertEqual(self.downloads, 1)
        self.assertFalse(setup.archives.needs_receipt_migration(entry, self.app.files))

        edited = entry | {
            "name": "Renamed fixture",
            "package": "new catalog label",
            "source": "https://example.invalid/new-description",
            "notes": "Edited notes",
            "aliases": ["fixture alias"],
        }
        self.app.selected = [edited]
        self.assertEqual(self.app.app_status(edited)["state"], "installed")
        self.assertEqual(self.preview(), [])
        self.apply()
        self.assertEqual(self.downloads, 1)
        self.assertEqual(json.loads(self.receipt.read_text()), migrated)

    def test_unapproved_archive_source_and_mismatched_legacy_cannot_migrate(self):
        entry = self.archive()
        self.app.trust.clear()
        self.preview()
        self.assertTrue(any("--trust" in block for block in self.app.blocks))
        with self.assertRaises(SafetyError):
            self.apply()
        self.assertEqual(self.downloads, 0)
        self.assertFalse(self.receipt.exists())

        self.app.trust.add(entry["id"])
        self.apply()
        old = legacy_receipt(self.receipt, entry)
        old["spec"] = "0" * 64
        self.receipt.write_text(json.dumps(old))
        self.assertEqual(self.app.app_status(entry)["state"], "stale-receipt")
        self.assertFalse(setup.archives.needs_receipt_migration(entry, self.app.files))
        with self.assertRaises(SafetyError):
            setup.archives.migrate_receipt(entry, self.app.files)
        self.assertEqual(json.loads(self.receipt.read_text()), old)

        old["spec"] = digest(json.dumps(entry, sort_keys=True).encode())
        self.receipt.write_text(json.dumps(old))
        changed = entry | {"commands": {"fixture-command": "bin/alternate"}}
        self.app.selected = [changed]
        self.assertEqual(self.app.app_status(changed)["state"], "stale-receipt")
        self.assertFalse(setup.archives.needs_receipt_migration(changed, self.app.files))
        with self.assertRaises(SafetyError):
            setup.archives.migrate_receipt(changed, self.app.files)
        self.assertEqual(json.loads(self.receipt.read_text()), old)
        actions = self.preview()
        self.assertNotIn("receipt-migrate", [action["kind"] for action in actions])
        self.assertTrue(self.app.blocks)
        with self.assertRaises(SafetyError):
            self.apply()
        self.assertEqual(self.downloads, 1)
        self.assertEqual(json.loads(self.receipt.read_text()), old)
        self.assertEqual(
            subprocess.run([str(self.home / ".local/bin/fixture-command")], check=False).returncode,
            0,
        )

    def test_legacy_receipt_requires_artifact_checksum_and_deployed_integrity(self):
        entry = self.archive()
        self.apply()
        old = legacy_receipt(self.receipt, entry)
        mismatched = old | {"sha256": "0" * 64}
        self.receipt.write_text(json.dumps(mismatched))
        self.assertEqual(self.app.app_status(entry)["state"], "stale-receipt")
        self.assertFalse(setup.archives.needs_receipt_migration(entry, self.app.files))
        with self.assertRaises(SafetyError):
            setup.archives.migrate_receipt(entry, self.app.files)
        self.assertEqual(json.loads(self.receipt.read_text()), mismatched)

        self.receipt.write_text(json.dumps(old))
        payload = self.home / ".local/share/vixygrey/apps/fixture-archive/1.0/bin/fixture"
        payload.write_bytes(b"modified executable")
        self.assertEqual(self.app.app_status(entry)["state"], "stale-receipt")
        self.assertFalse(setup.archives.needs_receipt_migration(entry, self.app.files))
        with self.assertRaises(SafetyError):
            setup.archives.migrate_receipt(entry, self.app.files)
        self.assertEqual(json.loads(self.receipt.read_text()), old)
        self.assertEqual(self.downloads, 1)

    def test_font_pending_cache_and_retired_inventory_survive_migration(self):
        self.set_cache_exit(0)
        self.font("Regular.ttf", "Retired.otf")
        self.apply()
        self.font("Regular.ttf", "New.ttf")
        entry = self.entry
        self.set_cache_exit(7)
        with self.assertRaises(SafetyError):
            self.apply()
        old = legacy_receipt(self.receipt, entry)
        self.assertTrue(old["cache_pending"])
        retired = f"{setup.archives.FONT_DIRECTORY}/Retired.otf"
        self.assertIn(retired, old["retired"])
        self.assertEqual((self.home / retired).read_bytes(), b"Retired.otf")
        before = self.snapshot()
        self.assertTrue(setup.archives.needs_receipt_migration(entry, self.app.files))
        self.assertEqual(self.app.status_document()["apps"][0]["state"], "cache-pending")
        actions = self.preview()
        self.assertEqual([action["kind"] for action in actions], ["receipt-migrate", "font-cache"])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.downloads, 2)

        with self.assertRaises(SafetyError):
            self.apply()
        migrated = json.loads(self.receipt.read_text())
        self.assertEqual(migrated["spec_version"], setup.archives.SPEC_VERSION)
        for key in ("files", "retired", "cache_pending"):
            self.assertEqual(migrated[key], old[key])
        self.assertEqual(self.app.files.backups[-1].name, self.receipt.name)
        self.assertEqual(json.loads(self.app.files.backups[-1].read_text()), old)
        for relative in (
            f"{setup.archives.FONT_DIRECTORY}/Regular.ttf",
            f"{setup.archives.FONT_DIRECTORY}/New.ttf",
            retired,
        ):
            self.assertEqual(self.snapshot()[relative], before[relative])
        self.assertEqual(self.downloads, 2)
        edited = entry | {
            "name": "Renamed font",
            "notes": "Edited notes",
            "source": "https://example.invalid/new-description",
            "package": "new catalog label",
        }
        self.app.selected = [edited]
        self.assertEqual(self.app.app_status(edited)["state"], "cache-pending")
        self.assertEqual([action["kind"] for action in self.preview()], ["font-cache"])
        self.set_cache_exit(0)
        self.apply()
        self.assertEqual(self.downloads, 2)
        self.assertEqual(self.app.app_status(edited)["state"], "installed")
        receipt = json.loads(self.receipt.read_text())
        self.assertFalse(receipt["cache_pending"])
        self.assertEqual(receipt["retired"], old["retired"])
        self.assertEqual(receipt["files"], old["files"])
        self.assertEqual(self.preview(), [])


if __name__ == "__main__":
    unittest.main()
