import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode = True

import setup
from safe_files import SafetyError

ROOT = Path(__file__).resolve().parents[1]
KITTY = ".config/kitty/kitty.conf"


class ConfigDiff(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.environment = {
            "HOME": str(self.home),
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
        }

    def cli(self, *flags, environment=None):
        return subprocess.run(
            [sys.executable, str(ROOT / "setup.py"), *flags],
            env=self.environment | (environment or {}),
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

    def local_diff(self, names, *, apps_only=False, selected=()):
        args = SimpleNamespace(replace=[], trust=[], profile=[], apps_only=apps_only)
        with patch.dict(os.environ, self.environment, clear=True):
            app = setup.Setup(args)
            app.selected = list(selected)
            with (
                patch.object(app, "run", side_effect=AssertionError("package call")),
                patch.object(app.files, "status", side_effect=AssertionError("unbounded status")),
            ):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    app.diff(names)
                return output.getvalue()

    def source(self, name, data):
        root = self.base / "checkout"
        destination = root / "dotfiles" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return root, destination

    def current(self, name, data):
        destination = self.home / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return destination

    def home_snapshot(self):
        return {
            path.relative_to(self.home): (
                path.stat().st_mode,
                path.stat().st_mtime_ns,
                path.read_bytes() if path.is_file() else None,
            )
            for path in self.home.rglob("*")
        }

    def test_real_cli_unified_diff_missing_unchanged_and_repetitions(self):
        desired = (ROOT / "dotfiles" / KITTY).read_bytes()
        original = self.current(KITTY, b"private local setting\n")
        metadata = original.stat().st_mtime_ns
        before = self.home_snapshot()
        result = self.cli("--theme-only", "--diff", KITTY, "--diff", KITTY, "--format", "text")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count(f"--- current/{KITTY}"), 1)
        self.assertIn(f"+++ desired/{KITTY}", result.stdout)
        self.assertIn("-private local setting", result.stdout)
        self.assertIn("+", result.stdout)
        self.assertIn("separate --apply", result.stdout)
        self.assertEqual(original.read_bytes(), b"private local setting\n")
        self.assertEqual(original.stat().st_mtime_ns, metadata)
        self.assertEqual(self.home_snapshot(), before)
        self.assertFalse((self.home / ".local").exists())
        original.write_bytes(desired)
        result = self.cli("--theme-only", "--diff", KITTY)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("UNCHANGED " + KITTY, result.stdout)
        self.assertNotIn("--- current/", result.stdout)
        original.unlink()
        result = self.cli("--theme-only", "--diff", KITTY)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MISSING (new) " + KITTY, result.stdout)
        self.assertFalse(original.exists())

    def test_diff_preserves_missing_final_newline_boundary(self):
        self.current(KITTY, b"private local setting")
        result = self.cli("--theme-only", "--diff", KITTY)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-private local setting\n\\ No newline at end of file\n+", result.stdout)

    def test_selected_launchers_and_theme_scope_exclude_other_files(self):
        name = ".local/share/applications/vixygrey-zed.desktop"
        allowed = self.cli("--apps-only", "--only", "zed", "--diff", name)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertIn("MISSING (new) " + name, allowed.stdout)
        for flags, disallowed in [
            (("--theme-only",), name),
            (("--apps-only", "--only", "git"), name),
            (("--apps-only", "--only", "zed"), KITTY),
            (("--apps-only", "--only", "zed", "--skip", "zed"), name),
            (("--theme-only",), ".local/state/vixygrey-setup/receipts.json"),
        ]:
            with self.subTest(flags=flags, name=disallowed):
                result = self.cli(*flags, "--diff", disallowed)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
        zed = next(entry for entry in setup.catalog() if entry["id"] == "zed")
        self.assertIn(
            "MISSING (new) " + name,
            self.local_diff([name], apps_only=True, selected=[zed]),
        )

    def test_incompatible_modes_fail_before_catalog_or_home_effects(self):
        combinations = [
            ("--apply",),
            ("--apply-plan", "missing.json"),
            ("--format", "json"),
            ("--plan-out", "missing.json"),
            ("--status",),
            ("--doctor",),
            ("--list",),
            ("--validate-catalog",),
            ("--desktop",),
            ("--replace", KITTY),
        ]
        for flags in combinations:
            with self.subTest(flags=flags):
                result = self.cli("--theme-only", "--diff", KITTY, *flags)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("--diff cannot be combined", result.stderr)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_invalid_paths_and_late_invalid_path_do_not_disclose_first_file(self):
        self.current(KITTY, b"PRIVATE_MARKER_DO_NOT_PRINT\n")
        for name in (
            "/tmp/elsewhere",
            "../elsewhere",
            ".config/../../elsewhere",
            ".config/kitty/./kitty.conf",
            "bad\x1b[31m",
            ".config/kitty/kitty.conf\n",
        ):
            with self.subTest(path=name):
                result = self.cli("--theme-only", "--diff", KITTY, "--diff", name)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("PRIVATE_MARKER_DO_NOT_PRINT", result.stderr)
                self.assertNotIn("\x1b", result.stderr)
        self.assertEqual((self.home / KITTY).read_bytes(), b"PRIVATE_MARKER_DO_NOT_PRINT\n")

    def test_destination_symlinks_ancestors_and_special_files_are_protected(self):
        marker = self.current("personal", b"never follow\n")
        target = self.home / KITTY
        target.parent.mkdir(parents=True)
        target.symlink_to(marker)
        result = self.cli("--theme-only", "--diff", KITTY)
        self.assertEqual((result.returncode, result.stdout), (2, ""))
        self.assertEqual(marker.read_bytes(), b"never follow\n")
        target.unlink()
        (self.home / ".config").rename(self.home / "config-backup")
        (self.home / ".config").symlink_to(self.home / "config-backup", target_is_directory=True)
        result = self.cli("--theme-only", "--diff", KITTY)
        self.assertEqual((result.returncode, result.stdout), (2, ""))
        (self.home / ".config").unlink()
        (self.home / "config-backup").rename(self.home / ".config")
        os.mkfifo(target)
        result = self.cli("--theme-only", "--diff", KITTY)
        self.assertEqual((result.returncode, result.stdout), (2, ""))

    def test_repo_root_source_and_source_ancestor_symlinks_are_protected(self):
        root, source = self.source(KITTY, b"desired\n")
        self.current(KITTY, b"private\n")
        with patch.object(setup, "ROOT", root):
            self.assertIn("-private", self.local_diff([KITTY]))
            source.unlink()
            source.symlink_to(self.home / KITTY)
            with self.assertRaises(SafetyError):
                self.local_diff([KITTY])
            source.unlink()
            source.parent.rename(root / "real-kitty")
            source.parent.symlink_to(root / "real-kitty", target_is_directory=True)
            with self.assertRaises(SafetyError):
                self.local_diff([KITTY])
            source.parent.unlink()
            (root / "dotfiles").rename(root / "real-dotfiles")
            (root / "dotfiles").symlink_to(root / "real-dotfiles", target_is_directory=True)
            with self.assertRaises(SafetyError):
                self.local_diff([KITTY])

    def test_invalid_text_and_bounded_input_fail_without_prior_content(self):
        for data in (
            b"\x00binary",
            b"\xffinvalid",
            b"escape\x1b[31m",
            b"return\rline",
            b"tab\tline",
            b"x" * (setup.DIFF_FILE_LIMIT + 1),
        ):
            with self.subTest(data=data[:10]):
                self.current(KITTY, data)
                result = self.cli("--theme-only", "--diff", KITTY)
                self.assertEqual((result.returncode, result.stdout), (2, ""))
        root, source = self.source(KITTY, b"x" * (setup.DIFF_FILE_LIMIT + 1))
        with patch.object(setup, "ROOT", root), self.assertRaises(SafetyError):
            self.local_diff([KITTY])
        self.current(KITTY, b"mine\n")
        for data in (b"\x00binary", b"\xffinvalid", b"escape\x1b[31m"):
            source.write_bytes(data)
            with patch.object(setup, "ROOT", root), self.assertRaises(SafetyError):
                self.local_diff([KITTY])

    def test_unrequested_oversized_repository_file_is_not_read(self):
        root, _ = self.source(KITTY, b"desired\n")
        self.source(".config/other/huge", b"x" * (setup.DIFF_FILE_LIMIT + 1))
        with patch.object(setup, "ROOT", root):
            self.assertIn("MISSING (new) " + KITTY, self.local_diff([KITTY]))

    def test_late_unsafe_content_and_output_limit_do_not_disclose_prior_diff(self):
        root, _ = self.source(KITTY, b"repo\n")
        second = ".config/demo/second"
        self.source(second, b"repo\n")
        self.current(KITTY, b"PRIVATE_MARKER_DO_NOT_PRINT\n")
        self.current(second, b"\x00bad")
        with patch.object(setup, "ROOT", root):
            with (
                contextlib.redirect_stdout(io.StringIO()) as output,
                self.assertRaises(SafetyError),
            ):
                self.local_diff([KITTY, second])
            self.assertEqual(output.getvalue(), "")
        for index in range(3):
            name = f".config/demo/{index}"
            self.source(name, b"D" * 60_000 + b"\n")
            self.current(name, b"C" * 60_000 + b"\n")
        with patch.object(setup, "ROOT", root):
            with (
                contextlib.redirect_stdout(io.StringIO()) as output,
                self.assertRaisesRegex(SafetyError, "Diff output exceeds"),
            ):
                self.local_diff([f".config/demo/{index}" for index in range(3)])
            self.assertEqual(output.getvalue(), "")

    def test_nonstandard_xdg_refused_without_content_or_changes(self):
        self.current(KITTY, b"PRIVATE_MARKER_DO_NOT_PRINT\n")
        for variable in ("XDG_CONFIG_HOME", "XDG_DATA_HOME"):
            with self.subTest(variable=variable):
                result = self.cli(
                    "--theme-only",
                    "--diff",
                    KITTY,
                    environment={variable: str(self.home / "other")},
                )
                self.assertEqual((result.returncode, result.stdout), (2, ""))
                self.assertIn("nonstandard", result.stderr)
        launcher = ".local/share/applications/vixygrey-zed.desktop"
        result = self.cli(
            "--apps-only",
            "--only",
            "zed",
            "--diff",
            launcher,
            environment={"XDG_DATA_HOME": str(self.home / "other")},
        )
        self.assertEqual((result.returncode, result.stdout), (2, ""))

    def test_default_preview_json_and_saved_plan_are_content_free(self):
        marker = "PRIVATE_MARKER_DO_NOT_PRINT"
        self.current(KITTY, (marker + "\n").encode())
        plan = self.base / "plan.json"
        for flags in ((), ("--format", "json"), ("--format", "json", "--plan-out", str(plan))):
            with self.subTest(flags=flags):
                result = self.cli("--theme-only", *flags)
                self.assertNotIn(marker, result.stdout + result.stderr)
        self.assertNotIn(marker, plan.read_text())
        self.assertNotIn("diff", json.loads(plan.read_text())["intent"])
        self.assertEqual((self.home / KITTY).read_text(), marker + "\n")
        self.assertFalse((self.home / ".local/state").exists())
