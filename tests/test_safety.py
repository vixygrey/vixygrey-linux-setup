import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True

import archives
from safe_files import Files, SafetyError

ROOT = Path(__file__).resolve().parents[1]


class DeploymentSafety(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.files = Files(self.home)

    def test_new_file_is_private_and_repeat_does_not_rewrite_it(self):
        self.assertEqual(self.files.put(".config/demo", b"new"), "create")
        path = self.home / ".config/demo"
        metadata = path.stat()
        self.assertEqual(metadata.st_mode & 0o777, 0o600)
        self.assertEqual(self.files.put(".config/demo", b"new"), "unchanged")
        self.assertEqual(path.stat().st_mtime_ns, metadata.st_mtime_ns)
        self.assertEqual(path.read_bytes(), b"new")

    def test_conflict_is_preserved_without_creating_a_backup(self):
        self.files.put(".config/demo", b"mine")
        self.assertEqual(self.files.put(".config/demo", b"repo"), "preserve")
        self.assertEqual((self.home / ".config/demo").read_bytes(), b"mine")
        self.assertFalse((self.home / ".local/state").exists())

    def test_explicit_replace_preserves_original_bytes_and_home_relative_path(self):
        self.files.put(".config/example/settings.json", b"original")
        replacing = Files(self.home, [".config/example/settings.json"])
        self.assertEqual(replacing.put(".config/example/settings.json", b"repo"), "replace")
        self.assertEqual((self.home / ".config/example/settings.json").read_bytes(), b"repo")
        (backup,) = replacing.backups
        self.assertEqual(backup.read_bytes(), b"original")
        self.assertTrue(str(backup).endswith("/.config/example/settings.json"))
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_symlink_ancestor_is_protected_even_with_replace_consent(self):
        outside = self.home / "outside"
        outside.mkdir()
        (outside / "config").write_bytes(b"keep")
        (self.home / ".config").symlink_to(outside, target_is_directory=True)
        replacing = Files(self.home, [".config/config"])
        self.assertEqual(replacing.put(".config/config", b"overwrite"), "protected")
        self.assertEqual((outside / "config").read_bytes(), b"keep")

    def test_dangling_destination_symlink_is_never_followed(self):
        (self.home / "config").symlink_to(self.home / "missing")
        replacing = Files(self.home, ["config"])
        self.assertEqual(replacing.put("config", b"new"), "protected")
        self.assertFalse((self.home / "missing").exists())
        self.assertTrue((self.home / "config").is_symlink())

    def test_traversal_and_absolute_paths_are_rejected(self):
        for value in ["../escape", "/tmp/escape", ".config/../../escape"]:
            with self.subTest(value=value), self.assertRaises(SafetyError):
                self.files.target(value)

    def test_identical_launcher_gets_executable_permission_without_replacement(self):
        self.files.put(".local/bin/demo", b"#!/bin/sh\nexit 0\n")
        self.assertEqual(
            self.files.status(".local/bin/demo", b"#!/bin/sh\nexit 0\n", 0o755), "mode"
        )
        self.assertEqual(self.files.put(".local/bin/demo", b"#!/bin/sh\nexit 0\n", 0o755), "mode")
        self.assertTrue(os.access(self.home / ".local/bin/demo", os.X_OK))
        self.assertFalse(self.files.backups)


class ArchiveSafety(unittest.TestCase):
    def make_tar(self, entries):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "bundle.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            for name, content, link in entries:
                info = tarfile.TarInfo(name)
                if link is not None:
                    info.type = tarfile.SYMTYPE
                    info.linkname = link
                    archive.addfile(info)
                else:
                    info.size = len(content)
                    info.mode = 0o4755
                    archive.addfile(info, io.BytesIO(content))
        return path

    def test_internal_library_link_becomes_regular_data_and_setuid_is_stripped(self):
        path = self.make_tar(
            [("lib/versioned.so", b"library", None), ("lib/current.so", b"", "versioned.so")]
        )
        result = list(archives.tar_payload(path))
        self.assertEqual(
            result, [("lib/versioned.so", b"library", 0o755), ("lib/current.so", b"library", 0o755)]
        )

    def test_absolute_and_parent_traversal_archive_paths_are_rejected(self):
        for name in ["/tmp/escape", "../escape", "folder/../../escape"]:
            with self.subTest(name=name):
                path = self.make_tar([(name, b"evil", None)])
                with self.assertRaises(SafetyError):
                    list(archives.tar_payload(path))

    def test_outward_and_cyclic_archive_links_are_rejected(self):
        for entries in [
            [("link", b"", "../escape")],
            [("link", b"", "/etc/passwd")],
            [("first", b"", "second"), ("second", b"", "first")],
        ]:
            with self.subTest(entries=entries):
                with self.assertRaises(SafetyError):
                    list(archives.tar_payload(self.make_tar(entries)))

    def test_font_archive_does_not_install_scripts(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "font.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("install.sh", "exit 1")
                archive.writestr("fonts/Example.ttf", b"font-data")
            self.assertEqual(
                list(archives.font_payload(path)), [("Example.ttf", b"font-data", 0o644)]
            )

    def test_debian_container_cannot_choose_a_temporary_output_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "package.deb"
            name = b"data.tar../oops"
            header = (
                name.ljust(16)
                + b"0".ljust(12)
                + b"0".ljust(6)
                + b"0".ljust(6)
                + b"100644".ljust(8)
                + b"1".ljust(10)
                + b"`\n"
            )
            path.write_bytes(b"!<arch>\n" + header + b"x\n")
            with self.assertRaises(SafetyError):
                list(archives.payload_for(path, {"format": "deb"}))


class CommandSafety(unittest.TestCase):
    def test_typo_and_empty_selection_do_not_fall_back_to_installing_everything(self):
        with tempfile.TemporaryDirectory() as temporary:
            for selection in ["", "not-a-real-app"]:
                result = subprocess.run(
                    [sys.executable, str(ROOT / "setup.py"), "--apps-only", "--only", selection],
                    env={
                        "HOME": temporary,
                        "PATH": "/usr/bin:/bin",
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_xdg_home_aliases_match_the_same_canonical_home_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "real"
            home.mkdir()
            alias = root / "alias"
            alias.symlink_to(home, target_is_directory=True)
            result = subprocess.run(
                [sys.executable, str(ROOT / "setup.py"), "--theme-only"],
                env={
                    "HOME": str(alias),
                    "PATH": "/usr/bin:/bin",
                    "XDG_CONFIG_HOME": str(alias / ".config"),
                    "XDG_DATA_HOME": str(alias / ".local/share"),
                },
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(list(home.iterdir()), [])

    def test_vendor_install_plan_requires_explicit_approval_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            for approval, expected in [([], 2), (["--trust", "omp"], 0)]:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "setup.py"),
                        "--apps-only",
                        "--only",
                        "omp",
                        *approval,
                    ],
                    env={"HOME": temporary, "PATH": "/usr/bin:/bin"},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_json_plan_serialization_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            home.mkdir()
            plan = Path(temporary) / "plan.json"
            command = [
                sys.executable,
                str(ROOT / "setup.py"),
                "--apps-only",
                "--only",
                "omp",
                "--trust",
                "omp",
                "--format",
                "json",
                "--plan-out",
                str(plan),
            ]
            environment = {
                "HOME": str(home),
                "PATH": "/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            result = subprocess.run(
                command, env=environment, text=True, capture_output=True, check=False
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads(result.stdout)
            self.assertEqual(document["schema_version"], 1)
            self.assertEqual(document["selected_ids"], ["omp"])
            self.assertIn("actions", document)
            self.assertEqual(json.loads(plan.read_text()), document)
            document["catalog_digest"] = "0" * 64
            plan.write_text(json.dumps(document))
            result = subprocess.run(
                [sys.executable, str(ROOT / "setup.py"), "--apply-plan", str(plan)],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(list(home.iterdir()), [])

    def test_catalog_validator_is_offline_and_does_not_write_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [sys.executable, str(ROOT / "setup.py"), "--validate-catalog"],
                env={"HOME": temporary, "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Catalog valid: 122 entries", result.stdout)
            self.assertEqual(list(Path(temporary).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
