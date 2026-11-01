import contextlib
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import venv
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True

import archives
import setup

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

    def test_profiles_expand_canonical_ids_allow_skip_and_do_not_imply_trust(self):
        environment = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"}
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "setup.py"),
                    "--apps-only",
                    "--profile",
                    "base",
                    "--skip",
                    "git",
                    "--format",
                    "json",
                ],
                env={**environment, "HOME": temporary},
                text=True,
                capture_output=True,
                check=False,
            )
            document = json.loads(result.stdout)
            self.assertEqual(document["intent"]["profiles"], ["base"])
            self.assertIn("micro", document["selected_ids"])
            self.assertNotIn("git", document["selected_ids"])
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "setup.py"),
                    "--apps-only",
                    "--profile",
                    "desktop",
                    "--format",
                    "json",
                ],
                env={**environment, "HOME": temporary},
                text=True,
                capture_output=True,
                check=False,
            )
            document = json.loads(result.stdout)
            self.assertEqual(result.returncode, 2)
            self.assertIn(
                "todoist: review https://flathub.org/apps/com.todoist.Todoist and explicitly --trust todoist",
                document["blockers"],
            )
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_profiles_reject_unknown_names_and_invalid_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            environment = {
                "HOME": temporary,
                "PATH": "/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "setup.py"),
                    "--apps-only",
                    "--profile",
                    "missing",
                ],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("Unknown --profile entries: missing", result.stderr)
            self.assertEqual(list(Path(temporary).iterdir()), [])

            original = setup.PROFILE_PATH
            path = Path(temporary) / "profiles.json"
            entries = [{"id": "git", "name": "Git", "aliases": ["git-alias"]}]
            try:
                for values, message in [
                    ({"valid": ["git", "git"]}, "unique non-empty"),
                    ({"valid": ["git-alias"]}, "canonical IDs"),
                    ({"valid": ["unknown"]}, "unknown profile member"),
                ]:
                    path.write_text(json.dumps(values))
                    setup.PROFILE_PATH = path
                    with self.subTest(values=values), self.assertRaisesRegex(SafetyError, message):
                        setup.profiles(entries)
            finally:
                setup.PROFILE_PATH = original

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

    def test_status_reports_stale_receipts_conflicts_and_preserved_files_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            receipt = home / ".local/state/vixygrey-setup/receipts/omp.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text("{}")
            command = home / ".local/bin/omp"
            command.parent.mkdir(parents=True)
            command.write_text("mine")
            managed = home / ".config/kitty/kitty.conf"
            managed.parent.mkdir(parents=True)
            managed.write_text("mine")
            before = {
                path.relative_to(home): path.read_bytes()
                for path in home.rglob("*")
                if path.is_file()
            }
            environment = {
                "HOME": temporary,
                "PATH": "/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "setup.py"),
                    "--status",
                    "--only",
                    "omp",
                    "--trust",
                    "omp",
                    "--format",
                    "json",
                ],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads(result.stdout)
            self.assertEqual(
                document["apps"], [{"id": "omp", "method": "archive", "state": "stale-receipt"}]
            )
            self.assertIn(
                {"path": ".config/kitty/kitty.conf", "state": "preserved"}, document["files"]
            )
            after = {
                path.relative_to(home): path.read_bytes()
                for path in home.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)
            receipt.unlink()
            before = {
                path.relative_to(home): path.read_bytes()
                for path in home.rglob("*")
                if path.is_file()
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "setup.py"),
                    "--status",
                    "--only",
                    "omp",
                    "--trust",
                    "omp",
                    "--format",
                    "json",
                ],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["apps"][0]["state"], "command-conflict")
            after = {
                path.relative_to(home): path.read_bytes()
                for path in home.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_status_and_doctor_are_json_read_only_and_reject_apply(self):
        with tempfile.TemporaryDirectory() as temporary:
            environment = {
                "HOME": temporary,
                "PATH": "/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            for arguments, kind in [
                (["--status", "--apps-only", "--only", "omp", "--trust", "omp"], "status"),
                (["--doctor"], "doctor"),
            ]:
                result = subprocess.run(
                    [sys.executable, str(ROOT / "setup.py"), *arguments, "--format", "json"],
                    env=environment,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["kind"], kind)
                self.assertEqual(list(Path(temporary).iterdir()), [])
            result = subprocess.run(
                [sys.executable, str(ROOT / "setup.py"), "--status", "--apply"],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--status cannot be combined", result.stderr)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_saved_profile_plan_applies_the_reviewed_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            home.mkdir()
            binary = home / ".local/bin"
            binary.mkdir(parents=True)
            flatpak = binary / "flatpak"
            flatpak.write_text(
                "#!/bin/sh\n"
                'case "$1" in\n'
                '  info) [ -f "$FLATPAK_INSTALLED" ] && '
                'IFS= read -r installed < "$FLATPAK_INSTALLED" && [ "$installed" = "$2" ] ;;\n'
                '  remotes) printf "flathub https://dl.flathub.org/repo/\\n" ;;\n'
                "  install) for argument do :; done; "
                'printf "%s\\n" "$argument" > "$FLATPAK_INSTALLED" ;;\n'
                "  *) exit 1 ;;\n"
                "esac\n"
            )
            flatpak.chmod(0o755)
            installed = Path(temporary) / "flatpak-installed"
            plan = Path(temporary) / "plan.json"
            excluded = set(setup.profiles(setup.catalog())["desktop"]) - {"todoist"}
            environment = {
                "HOME": str(home),
                "PATH": str(binary),
                "PYTHONDONTWRITEBYTECODE": "1",
                "FLATPAK_INSTALLED": str(installed),
            }
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "setup.py"),
                    "--apps-only",
                    "--profile",
                    "desktop",
                    "--trust",
                    "todoist",
                    "--skip",
                    ",".join(sorted(excluded)),
                    "--format",
                    "json",
                    "--plan-out",
                    str(plan),
                ],
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            reviewed = plan.read_bytes()
            self.assertEqual(json.loads(reviewed)["selected_ids"], ["todoist"])
            self.assertFalse(installed.exists())
            self.assertFalse((home / ".local/bin/todoist").exists())
            with (
                patch.dict(os.environ, environment, clear=True),
                patch.object(setup, "cachyos", return_value=True),
                patch.object(setup.archives, "machine_arch", return_value="x86_64"),
                patch.object(setup.os, "geteuid", return_value=1000),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(setup.main(["--apply-plan", str(plan)]), 0)
            self.assertEqual(installed.read_text(), "com.todoist.Todoist\n")
            self.assertEqual(plan.read_bytes(), reviewed)
            self.assertFalse((home / ".config").exists())
            self.assertEqual(sorted(path.name for path in binary.iterdir()), ["flatpak"])

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
            self.assertEqual(list(Path(temporary).iterdir()), [])


class PacmanSafety(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        environment = patch.dict(os.environ, {"HOME": str(self.home), "PATH": ""}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.app = setup.Setup(SimpleNamespace(replace=[], trust=[], profile=[], apps_only=True))
        self.entry = {
            "id": "fixture",
            "name": "Fixture",
            "method": "pacman",
            "package": "extra/micro",
            "source": "https://archlinux.org/packages/extra/x86_64/micro/",
            "notes": "Official package",
            "third_party": False,
        }
        self.app.selected = [self.entry]
        self.installed = set()
        self.calls = []
        executable = patch.object(
            self.app,
            "executable",
            side_effect=lambda name: f"/usr/bin/{name}" if name in {"pacman", "sudo"} else None,
        )
        executable.start()
        self.addCleanup(executable.stop)
        commands = patch.object(self.app, "run", side_effect=self.command)
        commands.start()
        self.addCleanup(commands.stop)

    def command(self, argv, capture=False):
        self.calls.append(argv)
        if argv[:2] == ["pacman", "-Q"]:
            return SimpleNamespace(returncode=0 if argv[-1] in self.installed else 1, stdout="")
        if argv[:2] == ["pacman", "-Si"]:
            return SimpleNamespace(returncode=0, stdout="Repository : extra\nName : micro\n")
        if argv[:3] == ["sudo", "pacman", "-Syu"]:
            self.installed.add(argv[-1].rsplit("/", 1)[-1])
            return SimpleNamespace(returncode=0, stdout="")
        raise AssertionError(f"Unexpected command: {argv}")

    def test_cachyos_detection_requires_exact_os_id_and_plan_uses_new_field(self):
        with (
            patch.object(setup.sys, "platform", "linux"),
            patch.object(
                setup.Path, "read_text", return_value='ID=arch\nID_LIKE=cachyos\nNAME="CachyOS"\n'
            ),
        ):
            self.assertFalse(setup.cachyos())
        with (
            patch.object(setup.sys, "platform", "linux"),
            patch.object(setup.Path, "read_text", return_value="ID=cachyos\nID_LIKE=arch\n"),
            patch.object(setup, "catalog_digest", return_value="f" * 64),
        ):
            self.assertTrue(setup.cachyos())
            preflight = setup.plan_document(self.app, {})["preflight"]
        self.assertTrue(preflight["is_cachyos"])
        self.assertNotIn("is_aurora", preflight)

    def test_native_preview_status_and_doctor_do_not_write_or_escalate(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.plan()
        self.assertEqual(self.app.blocks, [])
        self.assertEqual(setup.action_records(self.app)[0]["method"], "pacman")
        self.assertEqual(setup.action_records(self.app)[0]["package"], "extra/micro")
        self.assertEqual(self.app.status_document()["apps"][0]["state"], "missing")
        with patch.object(setup, "cachyos", return_value=False):
            doctor = self.app.doctor_document()
        self.assertEqual(
            next(c for c in doctor["checks"] if c["id"] == "cachyos")["state"], "blocked"
        )
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertFalse(any(call[0] == "sudo" for call in self.calls))

    def test_native_gui_package_does_not_plan_archive_launcher(self):
        for identifier in ("kitty", "zed"):
            with self.subTest(identifier=identifier):
                entry = self.entry | {"id": identifier, "package": identifier}
                self.assertEqual(list(setup.launchers(entry, self.home)), [])

    def test_native_apply_uses_full_upgrade_and_confirms_installed_state(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.apply()
        self.assertIn(["sudo", "pacman", "-Syu", "--needed", "--", "extra/micro"], self.calls)
        self.assertIn(["pacman", "-Q", "--", "micro"], self.calls)
        self.assertIn("micro", self.installed)
        self.calls.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.apply()
        self.assertFalse(any(call[0] == "sudo" for call in self.calls))

    def test_successful_transaction_without_installed_package_is_rejected(self):
        def unchanged(argv, capture=False):
            if argv[:3] == ["sudo", "pacman", "-Syu"]:
                return SimpleNamespace(returncode=0, stdout="")
            return self.command(argv, capture)

        with (
            patch.object(self.app, "run", side_effect=unchanged),
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaisesRegex(SafetyError, "did not confirm"),
        ):
            self.app.apply()
        self.assertNotIn("micro", self.installed)

    def test_znver4_package_preview_preserves_repository_priority(self):
        self.entry["package"] = "zoxide"
        for repository, blocked in (
            ("cachyos-extra-znver4", False),
            ("local", True),
            ("cachyos-extra-znver4-untrusted", True),
        ):
            with self.subTest(repository=repository):
                self.app.blocks.clear()
                self.app.steps.clear()
                self.app.dependencies.clear()
                with (
                    patch.object(
                        self.app,
                        "run",
                        side_effect=lambda argv, capture=False: SimpleNamespace(
                            returncode=1 if argv[1] == "-Q" else 0,
                            stdout=(
                                f"Repository : {repository}\nName : zoxide\n\n"
                                "Repository : extra\nName : zoxide\n"
                            ),
                        ),
                    ),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.app.plan()
                self.assertEqual(bool(self.app.blocks), blocked)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_unofficial_repository_or_unsafe_name_blocks_before_apply(self):
        self.entry["package"] = "community/micro"
        with self.assertRaises(SafetyError):
            setup.validate_catalog([self.entry])
        self.entry["package"] = "extra/micro;touch"
        with self.assertRaises(SafetyError):
            setup.validate_catalog([self.entry])
        self.entry["package"] = "extra/micro"
        with patch.object(
            self.app,
            "run",
            side_effect=lambda argv, capture=False: SimpleNamespace(
                returncode=1 if argv[1] == "-Q" else 0, stdout="Repository : local\n"
            ),
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                self.app.plan()
        self.assertTrue(self.app.blocks)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_manager_prerequisites_are_native(self):
        self.app.selected = [
            self.entry,
            {
                "id": "npm-fixture",
                "name": "npm fixture",
                "method": "npm",
                "package": "sample",
                "version": "1.0.0",
                "source": "https://www.npmjs.com/",
                "notes": "Fixture",
                "third_party": False,
            },
            {
                "id": "uv-fixture",
                "name": "uv fixture",
                "method": "uv",
                "package": "sample",
                "version": "1.0.0",
                "source": "https://pypi.org/",
                "notes": "Fixture",
                "third_party": False,
            },
            {
                "id": "flatpak-fixture",
                "name": "Flatpak fixture",
                "method": "flatpak",
                "package": "org.example.App",
                "source": "https://flathub.org/apps/",
                "notes": "Fixture",
                "third_party": False,
            },
        ]
        with contextlib.redirect_stdout(io.StringIO()):
            self.app.plan()
        dependencies = [payload for kind, payload in self.app.steps if kind == "dependency"]
        self.assertEqual(dependencies, ["nodejs", "npm", "uv", "flatpak"])
        self.assertIn(("flathub", None), self.app.steps)
        self.assertFalse(self.app.blocks)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_apply_guard_rejects_wrong_distro_root_and_architecture_without_writes(self):
        for target, uid, architecture in (
            (False, 1000, "x86_64"),
            (True, 0, "x86_64"),
            (True, 1000, "aarch64"),
        ):
            with (
                self.subTest(target=target, uid=uid, architecture=architecture),
                patch.object(setup, "catalog", return_value=[self.entry]),
                patch.object(setup, "profiles", return_value={"base": ["fixture"]}),
                patch.object(setup, "cachyos", return_value=target),
                patch.object(setup.os, "geteuid", return_value=uid),
                patch.object(setup.archives, "machine_arch", return_value=architecture),
                patch.object(setup.Setup, "apply", side_effect=AssertionError("must not apply")),
                self.assertRaisesRegex(SafetyError, "Apply requires x86_64 CachyOS"),
            ):
                setup.main(["--apply", "--apps-only", "--only", "fixture"])
        self.assertEqual(list(self.home.iterdir()), [])


class PythonHelperStatus(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.environment = {
            "HOME": str(self.home),
            "PATH": "",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        self.entry = next(entry for entry in setup.catalog() if entry["id"] == "yaml-py")
        with patch.dict(os.environ, self.environment, clear=True):
            application = setup.Setup(SimpleNamespace(replace=[], trust=[]))
        _, self.base, self.marker, command, wrapper = application.helper_paths(self.entry)
        venv.EnvBuilder(with_pip=False, symlinks=True).create(self.base)
        self.python = self.base / "bin/python"
        result = subprocess.run(
            [str(self.python), "-c", 'import sysconfig; print(sysconfig.get_path("purelib"))'],
            env=self.environment,
            text=True,
            capture_output=True,
            check=True,
        )
        distribution = Path(result.stdout.strip()) / f"PyYAML-{self.entry['version']}.dist-info"
        distribution.mkdir(parents=True)
        self.metadata = distribution / "METADATA"
        self.metadata.write_text(
            f"Metadata-Version: 2.1\nName: PyYAML\nVersion: {self.entry['version']}\n"
        )
        self.marker.write_text(self.entry["id"])
        self.command = self.home / command
        self.command.parent.mkdir(parents=True)
        self.command.write_bytes(wrapper)
        self.command.chmod(0o755)
        manager = self.command.with_name("uv")
        manager.write_text('#!/bin/sh\n: > "$HOME/uv-was-called"\nexit 97\n')
        manager.chmod(0o755)

    def snapshot(self):
        return {
            path.relative_to(self.home): (
                path.lstat().st_mode,
                path.lstat().st_mtime_ns,
                os.readlink(path)
                if path.is_symlink()
                else path.read_bytes()
                if path.is_file()
                else None,
            )
            for path in self.home.rglob("*")
        }

    def status(self, *approval):
        before = self.snapshot()
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "setup.py"),
                "--status",
                "--apps-only",
                "--only",
                "yaml-py",
                "--format",
                "json",
                *approval,
            ],
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot(), before)
        return json.loads(result.stdout)["apps"][0]["state"]

    def test_installed_helper_needs_no_source_approval(self):
        self.assertEqual(self.status(), "installed")
        self.assertEqual(self.status("--trust", "yaml-py"), "installed")

    def test_wrong_or_missing_distribution_is_not_installed(self):
        self.metadata.write_text("Metadata-Version: 2.1\nName: PyYAML\nVersion: 0.0.0\n")
        self.assertEqual(self.status(), "blocked")
        self.assertEqual(self.status("--trust", "yaml-py"), "missing")
        self.metadata.unlink()
        self.assertEqual(self.status("--trust", "yaml-py"), "missing")

    def test_missing_or_foreign_ownership_is_not_installed(self):
        self.marker.write_text("another-helper")
        self.assertEqual(self.status("--trust", "yaml-py"), "missing")
        self.marker.unlink()
        self.assertEqual(self.status("--trust", "yaml-py"), "missing")

    def test_missing_interpreter_is_not_installed(self):
        self.python.unlink()
        self.assertEqual(self.status("--trust", "yaml-py"), "missing")

    def test_modified_or_symlinked_wrapper_is_a_conflict(self):
        self.command.write_text("personal command\n")
        self.assertEqual(self.status("--trust", "yaml-py"), "command-conflict")
        self.command.unlink()
        self.command.symlink_to(self.python)
        self.assertEqual(self.status("--trust", "yaml-py"), "command-conflict")


if __name__ == "__main__":
    unittest.main()
