#!/usr/bin/env python3
"""Preview-first Aurora personal setup. Python 3.11+, standard library only."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True


import archives
from app_files import launchers
from safe_files import Files, SafetyError, digest, relative_path

ROOT = Path(__file__).resolve().parent
METHODS = {
    "brew",
    "flatpak",
    "npm",
    "uv",
    "go",
    "cargo",
    "archive",
    "font",
    "python-helper",
    "system",
}
FLATHUB = "https://dl.flathub.org/repo/"


def catalog() -> list[dict]:
    entries = []
    for path in sorted((ROOT / "catalog").glob("*.json")):
        entries.extend(json.loads(path.read_text()))
    validate_catalog(entries)
    seen = set()
    for entry in entries:
        if entry["method"] == "cargo" and archives.machine_arch() in entry.get("artifacts", {}):
            entry["method"] = "archive"
        identifier = entry["id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", identifier) or identifier in seen:
            raise SafetyError(f"Duplicate or invalid catalog ID: {identifier}")
        seen.add(identifier)
        if entry["method"] not in METHODS or not entry["source"].startswith("https://"):
            raise SafetyError(f"Invalid catalog source or method: {identifier}")
        package = entry["package"]
        if not package or package.startswith("-") or any(c.isspace() for c in package):
            raise SafetyError(f"Invalid package: {identifier}")
        if entry["method"] in {"npm", "uv", "go", "cargo", "archive", "font", "python-helper"}:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]*", entry.get("version", "")):
                raise SafetyError(f"An exact version is required: {identifier}")
        if entry["method"] in {"archive", "font"} or "artifacts" in entry:
            artifacts = [entry] if entry["method"] == "font" else entry["artifacts"].values()
            for artifact in artifacts:
                if not artifact["url"].startswith("https://") or not re.fullmatch(
                    r"[0-9a-f]{64}", artifact["sha256"]
                ):
                    raise SafetyError(f"Invalid pinned artifact: {identifier}")
                if artifact.get("format", "tar") not in {"tar", "deb", "raw"}:
                    raise SafetyError(f"Unsupported artifact format: {identifier}")
                if artifact.get("format") == "raw":
                    relative_path(artifact["filename"])
            command_sets = [
                entry.get("commands", {}),
                *(artifact.get("commands", {}) for artifact in artifacts),
            ]
            for commands in command_sets:
                for command, member in commands.items():
                    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", command):
                        raise SafetyError(f"Invalid command: {command}")
                    relative_path(member)
    if not entries:
        raise SafetyError("Application catalog is empty")
    return entries


def validate_catalog(entries: list[dict]) -> None:
    aliases = {}
    commands = {architecture: set() for architecture in ("x86_64", "aarch64")}
    required = {"id", "name", "method", "package", "source", "notes", "third_party"}
    versioned = {"npm", "uv", "go", "cargo", "archive", "font", "python-helper"}
    for entry in entries:
        identifier = entry.get("id", "")
        missing = required - entry.keys()
        if missing or not isinstance(entry.get("third_party"), bool):
            raise SafetyError(f"{identifier}: missing required catalog fields")
        if not entry["source"].startswith("https://"):
            raise SafetyError(f"{identifier}: source must use HTTPS")
        if entry["method"] not in METHODS:
            raise SafetyError(f"{identifier}: unsupported method")
        if entry["method"] in versioned and not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9.+_-]*", entry.get("version", "")
        ):
            raise SafetyError(f"{identifier}: exact version required")
        for name in [identifier, entry["name"], *entry.get("aliases", [])]:
            key = name.lower().strip()
            if not key or (key in aliases and aliases[key] != identifier):
                raise SafetyError(f"{identifier}: duplicate ID or alias: {name}")
            aliases[key] = identifier
        if entry["method"] == "archive":
            artifacts = entry.get("artifacts", {})
            if set(artifacts) != {"x86_64", "aarch64"}:
                raise SafetyError(f"{identifier}: archive requires x86_64 and aarch64 artifacts")
        for architecture, artifact in entry.get("artifacts", {}).items():
            if architecture not in commands:
                raise SafetyError(f"{identifier}: unsupported artifact architecture")
            if not artifact.get("url", "").startswith("https://") or not re.fullmatch(
                r"[0-9a-f]{64}", artifact.get("sha256", "")
            ):
                raise SafetyError(f"{identifier}: invalid pinned artifact")
            for command, member in artifact.get("commands", entry.get("commands", {})).items():
                if command in commands[architecture]:
                    raise SafetyError(f"{identifier}: duplicate command: {command}")
                commands[architecture].add(command)
                relative_path(member)


def aurora() -> bool:
    if sys.platform != "linux":
        return False
    release = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            release[key] = value.strip("\"'")
    values = [release.get(key, "").lower() for key in ("ID", "IMAGE_ID", "VARIANT_ID", "NAME")]
    if any(re.search(r"(^|[/ :_-])aurora($|[/ :_-])", value) for value in values):
        return True
    image = Path("/usr/share/ublue-os/image-info.json")
    if image.is_file():
        info = json.loads(image.read_text())
        return str(info.get("image-name", "")).startswith("aurora")
    return False


def tokens(values) -> set[str]:
    return {token.strip() for value in values for token in value.split(",") if token.strip()}


PLAN_SCHEMA_VERSION = 1


def catalog_digest() -> str:
    chunks = []
    for path in sorted((ROOT / "catalog").glob("*.json")):
        name = str(path.relative_to(ROOT)).encode()
        data = path.read_bytes()
        chunks.extend([len(name).to_bytes(8), name, len(data).to_bytes(8), data])
    return digest(b"".join(chunks))


def intent(args) -> dict:
    return {
        "apps_only": args.apps_only,
        "desktop": args.desktop,
        "include_optional": args.include_optional,
        "only": sorted(set(args.only)),
        "replace": sorted({str(relative_path(value)) for value in args.replace}),
        "skip": sorted(set(args.skip)),
        "theme_only": args.theme_only,
        "trust": sorted(set(args.trust)),
    }


def select(entries: list[dict], value: dict) -> list[dict]:
    if value["theme_only"]:
        return []
    return [
        entry
        for entry in entries
        if (not value["only"] or entry["id"] in value["only"])
        and entry["id"] not in value["skip"]
        and (not entry.get("optional") or value["include_optional"] or entry["id"] in value["only"])
    ]


def action_records(setup) -> list[dict]:
    records = []
    for kind, payload in setup.steps:
        if kind == "app":
            records.append(
                {
                    "id": payload["id"],
                    "kind": kind,
                    "method": payload["method"],
                    "package": payload["package"],
                    "source": payload["source"],
                    "version": payload.get("version", ""),
                }
            )
        elif kind == "file":
            name, data, mode = payload
            records.append({"digest": digest(data), "kind": kind, "mode": mode, "path": name})
        else:
            records.append({"kind": kind, "value": payload})
    return records


def plan_document(setup, value: dict) -> dict:
    return {
        "actions": action_records(setup),
        "blockers": setup.blocks,
        "catalog_digest": catalog_digest(),
        "intent": value,
        "preflight": {
            "architecture": archives.machine_arch(),
            "is_aurora": aurora(),
            "platform": sys.platform,
        },
        "preserved_conflicts": setup.preserved,
        "schema_version": PLAN_SCHEMA_VERSION,
        "selected_ids": sorted(entry["id"] for entry in setup.selected),
    }


def plan_bytes(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def print_report(document: dict, format_name: str):
    if format_name == "json":
        print(json.dumps(document, indent=2, sort_keys=True))
        return
    if document["kind"] == "status":
        for entry in document["apps"]:
            print(f"APP {entry['state']} {entry['id']} [{entry['method']}]")
        for entry in document["files"]:
            print(f"FILE {entry['state']} {entry['path']}")
        return
    for check in document["checks"]:
        print(f"CHECK {check['state']} {check['id']}: {check['remediation']}")


def write_plan(path: str, data: bytes):
    target = Path(path)
    if not target.parent.is_dir() or target.is_symlink() or target.exists():
        raise SafetyError(
            f"Plan output must be a new regular file in an existing directory: {target}"
        )
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def load_plan(path: str) -> dict:
    try:
        document = json.loads(Files.read(Path(path)))
    except (json.JSONDecodeError, OSError) as error:
        raise SafetyError(f"Cannot read plan: {error}") from None
    required = {
        "actions",
        "blockers",
        "catalog_digest",
        "intent",
        "preflight",
        "preserved_conflicts",
        "schema_version",
        "selected_ids",
    }
    if not isinstance(document, dict) or set(document) != required:
        raise SafetyError("Invalid plan schema")
    value = document["intent"]
    fields = {
        "apps_only",
        "desktop",
        "include_optional",
        "only",
        "replace",
        "skip",
        "theme_only",
        "trust",
    }
    if (
        document["schema_version"] != PLAN_SCHEMA_VERSION
        or not isinstance(value, dict)
        or set(value) != fields
    ):
        raise SafetyError("Unsupported plan schema")
    if not re.fullmatch(r"[0-9a-f]{64}", document["catalog_digest"]):
        raise SafetyError("Invalid plan catalog digest")
    for name in fields:
        expected = (
            isinstance(value[name], bool)
            if name in {"apps_only", "desktop", "include_optional", "theme_only"}
            else isinstance(value[name], list)
            and value[name] == sorted(set(value[name]))
            and all(isinstance(item, str) for item in value[name])
        )
        if not expected:
            raise SafetyError(f"Invalid plan intent: {name}")
    if document["selected_ids"] != sorted(set(document["selected_ids"])) or not all(
        isinstance(item, str) for item in document["selected_ids"]
    ):
        raise SafetyError("Invalid plan selected IDs")
    return document


class Setup:
    def __init__(self, args):
        self.args = args
        self.files = Files(Path.home(), args.replace)
        self.env = os.environ.copy()
        home = str(self.files.home)
        paths = [
            f"{home}/.local/bin",
            f"{home}/.local/share/vixygrey/npm/bin",
            f"{home}/.cargo/bin",
            "/home/linuxbrew/.linuxbrew/bin",
            "/home/linuxbrew/.linuxbrew/sbin",
        ]
        self.env["PATH"] = os.pathsep.join(paths + [self.env.get("PATH", "")])
        self.env.update(
            HOMEBREW_NO_AUTO_UPDATE="1",
            HOMEBREW_NO_ANALYTICS="1",
            UV_TOOL_BIN_DIR=f"{home}/.local/bin",
            GOBIN=f"{home}/.local/bin",
            CARGO_HOME=f"{home}/.cargo",
            npm_config_update_notifier="false",
        )
        self.steps: list[tuple[str, object]] = []
        self.blocks: list[str] = []
        self.preserved: list[str] = []
        self.dependencies = set()
        self.trust = tokens(args.trust)
        self.brew_packages = None
        self.manager_packages = {}
        self.selected: list[dict] = []

    def executable(self, name: str) -> str | None:
        return shutil.which(name, path=self.env["PATH"])

    def run(self, argv: list[str], capture=False):
        executable = self.executable(argv[0])
        if not executable:
            raise SafetyError(f"Required executable is missing: {argv[0]}")
        return subprocess.run(
            [executable, *argv[1:]], env=self.env, check=False, text=True, capture_output=capture
        )

    def command(self, argv: list[str]):
        print("+ " + shlex.join(argv), flush=True)
        result = self.run(argv)
        if result.returncode:
            raise SafetyError(
                f"Command failed with exit {result.returncode}; stopped without marking it installed"
            )

    def brew_installed(self) -> set[str]:
        if self.brew_packages is None:
            self.brew_packages = set()
            if self.executable("brew"):
                result = self.run(["brew", "list", "--formula", "--full-name"], capture=True)
                if result.returncode:
                    raise SafetyError("Cannot read installed Homebrew formulas")
                self.brew_packages = set(result.stdout.splitlines())
        return self.brew_packages

    def dependency(self, formula: str):
        if not re.fullmatch(r"[a-z0-9][a-z0-9@+._-]*", formula):
            raise SafetyError(f"Implicit prerequisites must be Homebrew core formulas: {formula}")
        if formula in self.dependencies or formula in self.brew_installed():
            return
        self.dependencies.add(formula)
        if not self.executable("brew"):
            self.blocks.append(
                f"Homebrew required for {formula}; use Aurora’s supported Homebrew provisioning"
            )
        else:
            self.steps.append(("dependency", formula))

    def manager(self, name: str, formula: str):
        if not self.executable(name):
            self.dependency(formula)

    def is_installed(self, entry: dict) -> bool:
        method, package = entry["method"], entry["package"]
        if method == "system":
            docker = Path("/usr/bin/docker")
            if (
                package != "docker"
                or not docker.is_file()
                or not Path("/usr/bin/dockerd").is_file()
            ):
                return False
            result = subprocess.run(
                [
                    str(docker),
                    "--host",
                    "unix:///var/run/docker.sock",
                    "info",
                    "--format",
                    "{{.ServerVersion}}",
                ],
                text=True,
                capture_output=True,
                env=self.env,
                check=False,
                timeout=15,
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        if method == "brew":
            return package in self.brew_installed()
        if method == "flatpak":
            if not self.executable("flatpak"):
                return False
            return self.run(["flatpak", "info", package], capture=True).returncode == 0
        if method in {"archive", "font"}:
            return archives.installed(entry, self.files)
        if method == "npm":
            metadata = self.files.target(
                f".local/share/vixygrey/npm/lib/node_modules/{package}/package.json"
            )
            if metadata.is_file():
                return json.loads(self.files.read(metadata)).get("version") == entry["version"]
            return False
        if method == "uv" and self.executable("uv"):
            if method not in self.manager_packages:
                result = self.run(["uv", "tool", "list"], capture=True)
                if result.returncode:
                    raise SafetyError("Cannot inspect uv tool installations")
                self.manager_packages[method] = result.stdout.splitlines()
            base = package.split("[")[0].lower().replace("_", "-")
            return f"{base} v{entry['version']}" in self.manager_packages[method]
        if method == "cargo" and self.executable("cargo"):
            if method not in self.manager_packages:
                result = self.run(["cargo", "install", "--list"], capture=True)
                if result.returncode:
                    raise SafetyError("Cannot inspect Cargo installations")
                self.manager_packages[method] = result.stdout.splitlines()
            return f"{package} v{entry['version']}:" in self.manager_packages[method]
        if method == "go" and self.executable("go"):
            binary = self.files.target(".local/bin/" + package.rsplit("/", 1)[-1])
            if not binary.is_file():
                return False
            result = self.run(["go", "version", "-m", str(binary)], capture=True)
            version = entry["version"]
            version = version if version.startswith("v") else "v" + version
            return result.returncode == 0 and any(
                line.split()[:3] == ["mod", entry.get("module", package.split("/cmd/")[0]), version]
                for line in result.stdout.splitlines()
            )
        return False

    def helper_paths(self, entry: dict):
        relative = f".local/share/vixygrey/venvs/{entry['id']}"
        base = self.files.target(relative)
        marker = self.files.target(relative + "/.vixygrey-owned")
        command = f".local/bin/{entry['id']}"
        wrapper = ("#!/bin/sh\nexec " + shlex.quote(str(base / "bin/python")) + ' "$@"\n').encode()
        return relative, base, marker, command, wrapper

    def helper_installed(self, entry: dict) -> bool:
        relative, base, marker, command, wrapper = self.helper_paths(entry)
        if not marker.is_file() or self.files.read(marker) != entry["id"].encode():
            return False
        if (
            not (base / "bin/python").is_file()
            or self.files.status(command, wrapper, 0o755) != "unchanged"
        ):
            return False
        result = subprocess.run(
            [
                str(base / "bin/python"),
                "-c",
                'import importlib.metadata; print(importlib.metadata.version("PyYAML"))',
            ],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == entry["version"]

    def app_status(self, entry: dict) -> dict:
        identifier, method = entry["id"], entry["method"]
        if method in {"archive", "font"}:
            try:
                if self.is_installed(entry):
                    return {"id": identifier, "method": method, "state": "installed"}
            except (OSError, ValueError, SafetyError, subprocess.SubprocessError):
                pass
            try:
                if self.files.target(archives.receipt_path(entry)).exists():
                    return {"id": identifier, "method": method, "state": "stale-receipt"}
            except SafetyError:
                return {"id": identifier, "method": method, "state": "stale-receipt"}
        else:
            try:
                if self.is_installed(entry):
                    return {"id": identifier, "method": method, "state": "installed"}
            except (OSError, ValueError, SafetyError, subprocess.SubprocessError):
                return {"id": identifier, "method": method, "state": "blocked"}
        paths = {name: data for name, data, _ in launchers(entry, self.files.home)}
        if method == "archive":
            paths.update(archives.wrappers(entry, self.files.home))
        if method == "python-helper":
            _, _, _, name, wrapper = self.helper_paths(entry)
            paths[name] = wrapper
        for name, data in paths.items():
            if self.files.status(name, data, 0o755) in {"preserve", "protected"}:
                return {"id": identifier, "method": method, "state": "command-conflict"}
        if entry.get("third_party") and identifier not in self.trust:
            return {"id": identifier, "method": method, "state": "blocked"}
        if method == "system":
            return {"id": identifier, "method": method, "state": "blocked"}
        managers = {
            "brew": "brew",
            "flatpak": "flatpak",
            "npm": "npm",
            "uv": "uv",
            "go": "go",
            "cargo": "cargo",
            "python-helper": "uv",
        }
        if method in managers and not self.executable(managers[method]):
            return {"id": identifier, "method": method, "state": "blocked"}
        return {"id": identifier, "method": method, "state": "missing"}

    def file_status(self) -> list[dict]:
        records = {}
        for entry in self.selected:
            for name, data, mode in launchers(entry, self.files.home):
                records[name] = (data, mode)
        if not self.args.apps_only:
            for source in sorted((ROOT / "dotfiles").rglob("*")):
                if source.is_file():
                    records[str(source.relative_to(ROOT / "dotfiles"))] = (
                        source.read_bytes(),
                        0o600,
                    )
        states = {
            "create": "missing",
            "mode": "unchanged",
            "preserve": "preserved",
            "protected": "protected",
            "replace": "preserved",
            "unchanged": "unchanged",
        }
        return [
            {"path": name, "state": states[self.files.status(name, data, mode)]}
            for name, (data, mode) in records.items()
        ]

    def status_document(self) -> dict:
        return {
            "apps": [self.app_status(entry) for entry in self.selected],
            "files": self.file_status(),
            "kind": "status",
        }

    def doctor_document(self) -> dict:
        checks = []

        def check(identifier: str, state: str, remediation: str, **values):
            checks.append({"id": identifier, "remediation": remediation, "state": state, **values})

        check(
            "aurora",
            "ready" if aurora() else "blocked",
            "Run --apply only from Aurora Linux as a non-root user.",
        )
        architecture = archives.machine_arch()
        check(
            "architecture",
            "ready" if architecture in {"x86_64", "aarch64"} else "blocked",
            "Use a supported x86_64 or aarch64 Aurora machine.",
            value=architecture,
        )
        for command, remediation in (
            ("brew", "Complete Aurora's supported Homebrew provisioning."),
            ("flatpak", "Install or enable Flatpak through normal Aurora provisioning."),
        ):
            check(command, "ready" if self.executable(command) else "blocked", remediation)
        docker = {"method": "system", "package": "docker"}
        check(
            "docker",
            "ready" if self.is_installed(docker) else "blocked",
            "Provision Aurora DX, run ujust dx-group, then log out and back in.",
        )
        plasma = (
            "KDE" in os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
            and self.executable("plasma-apply-colorscheme")
            and self.executable("plasma-apply-wallpaperimage")
        )
        check(
            "plasma",
            "ready" if plasma else "blocked",
            "Use an active KDE Plasma session with both plasma apply commands available.",
        )
        llama = self.executable("llama-cli")
        if llama:
            result = self.run(["llama-cli", "--list-devices"], capture=True)
            vulkan = result.returncode == 0 and bool(
                re.search(r"(?m)^\s*Vulkan\d+\s*:", result.stdout)
            )
            check(
                "vulkan",
                "ready" if vulkan else "blocked",
                "Install the Vulkan llama.cpp selection and confirm a working Aurora GPU driver.",
            )
        else:
            check(
                "vulkan",
                "missing",
                "Install the Vulkan llama.cpp selection and confirm a working Aurora GPU driver.",
            )
        for identifier, path in (("root-space", Path("/")), ("home-space", self.files.home)):
            usage = shutil.disk_usage(path)
            check(
                identifier,
                "ready",
                "Keep sufficient free space for selected apps, models, and configuration backups.",
                available_bytes=usage.free,
                total_bytes=usage.total,
            )
        return {"checks": checks, "kind": "doctor"}

    def plan_app(self, entry: dict):
        identifier, method, package = entry["id"], entry["method"], entry["package"]
        if method == "system":
            if self.is_installed(entry):
                print(f"AVAILABLE {identifier}: local Docker Engine is accessible")
            else:
                self.blocks.append(f"{identifier}: {entry['notes']} [{entry['source']}]")
            return
        if method in {"archive", "font"}:
            archives.artifact_for(entry)
        for command, formula in entry.get("runtime", {}).items():
            self.manager(command, formula)
        if self.is_installed(entry):
            print(f"INSTALLED {identifier}")
            return
        if method == "brew" and package in self.dependencies:
            print(f"PLANNED {identifier} as a prerequisite")
            return
        if method == "python-helper" and self.helper_installed(entry):
            print(f"INSTALLED {identifier}")
            return
        if entry.get("third_party", False) and identifier not in self.trust:
            self.blocks.append(
                f"{identifier}: review {entry['source']} and explicitly --trust {identifier}"
            )
        if method == "brew" and not self.executable("brew"):
            self.blocks.append(
                f"{identifier}: Homebrew is missing; this tool never downloads and executes its installer"
            )
        if method == "flatpak":
            if not self.executable("flatpak"):
                self.blocks.append(f"{identifier}: Flatpak is missing")
            else:
                result = self.run(
                    ["flatpak", "remotes", "--user", "--columns=name,url"], capture=True
                )
                if result.returncode:
                    self.blocks.append("Cannot inspect user Flatpak remotes")
                else:
                    remotes = dict(
                        line.split(None, 1) for line in result.stdout.splitlines() if line.strip()
                    )
                    if "flathub" not in remotes:
                        if "flathub" not in self.dependencies:
                            self.steps.append(("flathub", None))
                            self.dependencies.add("flathub")
                    elif remotes["flathub"].rstrip("/") != FLATHUB.rstrip("/"):
                        self.blocks.append(
                            "User flathub remote has an unexpected URL; refusing to use or replace it"
                        )
        if method == "npm":
            self.manager("npm", "node")
        if method in {"uv", "python-helper"}:
            self.manager("uv", "uv")
        if method == "go":
            self.manager("go", "go")
        if method == "cargo":
            self.manager("cargo", "rust")
            for formula in ("llvm", "cmake", "ninja", "pkgconf"):
                self.dependency(formula)
            if sys.platform == "linux" and not Path("/usr/include/stdlib.h").is_file():
                self.blocks.append(
                    f"{identifier}: source build requires C development headers; use an Aurora DX development environment with headers, not host dnf layering"
                )
        if method == "go":
            name = ".local/bin/" + package.rsplit("/", 1)[-1]
            try:
                target = self.files.target(name)
                if target.exists() and name not in self.files.replacements:
                    self.blocks.append(
                        f"{identifier}: {name} exists; explicitly --replace it after review"
                    )
            except SafetyError as error:
                self.blocks.append(str(error))
        if method == "python-helper":
            relative, base, marker, command, wrapper = self.helper_paths(entry)
            if base.exists() and (
                not marker.is_file() or self.files.read(marker) != identifier.encode()
            ):
                self.blocks.append(
                    f"{identifier}: existing unmanaged virtual environment at {base}; refusing to replace it"
                )
            if self.files.status(command, wrapper) in {"preserve", "protected"}:
                self.blocks.append(
                    f"{identifier}: {command} conflicts; explicitly --replace it or skip the helper"
                )
        if method == "archive":
            for name, data in archives.wrappers(entry, self.files.home).items():
                if self.files.status(name, data) in {"preserve", "protected"}:
                    self.blocks.append(
                        f"{identifier}: command path {name} conflicts; explicitly --replace it or skip the app"
                    )
        if method == "brew":
            self.dependencies.add(package)
        self.steps.append(("app", entry))

    def plan_file(self, name: str, data: bytes, mode: int = 0o600):
        status = self.files.status(name, data, mode)
        print(f"{status.upper()} {name}")
        if status in {"preserve", "protected"}:
            self.preserved.append(name)
        elif status != "unchanged":
            self.steps.append(("file", (name, data, mode)))

    def plan_theme(self):
        for variable, suffix in [("XDG_CONFIG_HOME", ".config"), ("XDG_DATA_HOME", ".local/share")]:
            if (
                os.environ.get(variable)
                and Path(os.environ[variable]).resolve() != (self.files.home / suffix).resolve()
            ):
                self.blocks.append(
                    f"{variable} is nonstandard; refusing to deploy configuration to the wrong location"
                )
        for source in sorted((ROOT / "dotfiles").rglob("*")):
            if source.is_symlink():
                raise SafetyError(f"Repository dotfile must not be a symlink: {source}")
            if not source.is_file():
                continue
            name = str(source.relative_to(ROOT / "dotfiles"))
            data = source.read_bytes()
            self.plan_file(name, data)
        if self.executable("bat") or any(entry["id"] == "bat" for entry in self.selected):
            self.steps.append(("bat-cache", None))
        if self.args.desktop:
            if "KDE" not in os.environ.get(
                "XDG_CURRENT_DESKTOP", ""
            ).upper() or not self.executable("plasma-apply-colorscheme"):
                self.blocks.append(
                    "--desktop requires an active KDE Plasma session and plasma-apply-colorscheme"
                )
            scheme = ".local/share/color-schemes/DraculaSakura.colors"
            source = ROOT / "dotfiles" / scheme
            if self.files.status(scheme, source.read_bytes()) in {"preserve", "protected"}:
                self.blocks.append("Cannot apply a preserved/conflicting KDE color scheme")
            wallpaper = ".local/share/wallpapers/DraculaSakura.jpg"
            if not self.executable("plasma-apply-wallpaperimage"):
                self.blocks.append("--desktop requires plasma-apply-wallpaperimage")
            if self.files.status(wallpaper, (ROOT / "dotfiles" / wallpaper).read_bytes()) in {
                "preserve",
                "protected",
            }:
                self.blocks.append("Cannot apply a preserved/conflicting wallpaper")
            self.steps.append(("desktop", None))

    def install_app(self, entry: dict):
        method, package = entry["method"], entry["package"]
        version = entry.get("version", "")
        if method == "brew":
            self.command(["brew", "install", "--formula", package])
        elif method == "flatpak":
            self.command(
                [
                    "flatpak",
                    "install",
                    "--user",
                    "--noninteractive",
                    "--assumeyes",
                    "flathub",
                    package,
                ]
            )
        elif method == "npm":
            self.command(
                [
                    "npm",
                    "install",
                    "--global",
                    "--prefix",
                    str(self.files.home / ".local/share/vixygrey/npm"),
                    f"{package}@{version}",
                ]
            )
        elif method == "uv":
            argv = ["uv", "tool", "install"]
            if entry.get("python"):
                argv.extend(["--python", entry["python"]])
            self.command([*argv, f"{package}=={version}"])
        elif method == "go":
            version = version if version.startswith("v") else "v" + version
            import tempfile

            with tempfile.TemporaryDirectory(prefix="vixygrey-go-") as temporary:
                previous = {key: self.env.get(key) for key in ("GOBIN", "CGO_ENABLED")}
                try:
                    self.env["GOBIN"] = temporary
                    if "cgo" in entry:
                        self.env["CGO_ENABLED"] = "1" if entry["cgo"] else "0"
                    tags = (
                        ["-tags", ",".join(entry["build_tags"])] if entry.get("build_tags") else []
                    )
                    self.command(["go", "install", *tags, f"{package}@{version}"])
                finally:
                    for key, value in previous.items():
                        if value is None:
                            self.env.pop(key, None)
                        else:
                            self.env[key] = value
                name = package.rsplit("/", 1)[-1]
                status = self.files.put(
                    f".local/bin/{name}", (Path(temporary) / name).read_bytes(), 0o755
                )
                if status in {"preserve", "protected"}:
                    raise SafetyError(f"Command conflict preserved: {name}")
        elif method == "cargo":
            result = self.run(["brew", "--prefix", "llvm"], capture=True)
            if result.returncode:
                raise SafetyError("Cannot locate the managed C toolchain")
            compiler = Path(result.stdout.strip()) / "bin"
            previous = {key: self.env.get(key) for key in ("CC", "CXX", "CMAKE_GENERATOR")}
            try:
                self.env.update(
                    CC=str(compiler / "clang"),
                    CXX=str(compiler / "clang++"),
                    CMAKE_GENERATOR="Ninja",
                )
                self.command(["cargo", "install", "--locked", "--version", version, package])
            finally:
                for key, value in previous.items():
                    if value is None:
                        self.env.pop(key, None)
                    else:
                        self.env[key] = value
        elif method == "python-helper":
            relative, base, marker, command, wrapper = self.helper_paths(entry)
            self.files.directory(relative)
            self.files.put(str(marker.relative_to(self.files.home)), entry["id"].encode())
            if not (base / "bin/python").is_file():
                self.command(["uv", "venv", "--allow-existing", str(base)])
            self.command(
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(base / "bin/python"),
                    f"{package}=={version}",
                ]
            )
            if self.files.put(command, wrapper, 0o755) in {"preserve", "protected"}:
                raise SafetyError(f"Helper command conflict preserved: {command}")
        elif method in {"archive", "font"}:
            preserved = archives.install(entry, self.files)
            self.preserved.extend(preserved)
            if preserved:
                raise SafetyError(
                    "Archive installation preserved conflicts: " + ", ".join(preserved)
                )
            if method == "font" and self.executable("fc-cache"):
                self.command(
                    [
                        "fc-cache",
                        "-f",
                        str(self.files.home / ".local/share/fonts/JetBrainsMonoNerd"),
                    ]
                )
        else:
            raise SafetyError(f"No installer for method: {method}")
        if method == "python-helper":
            if not self.helper_installed(entry):
                raise SafetyError(f"{entry['id']}: helper verification failed")
        elif not self.is_installed(entry):
            # Package state was cached before apply; refresh the relevant manager only.
            self.brew_packages = None
            self.manager_packages.clear()
            if not self.is_installed(entry):
                raise SafetyError(
                    f"{entry['id']}: package manager did not confirm the requested installation"
                )
        print(f"CONFIRMED {entry['id']}", flush=True)
        if entry["id"] == "llama-cpp-vulkan":
            result = self.run(["llama-cli", "--list-devices"], capture=True)
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            if result.returncode or not re.search(r"(?m)^\s*Vulkan\d+\s*:", result.stdout):
                self.files.target(archives.receipt_path(entry)).unlink(missing_ok=True)
                raise SafetyError(
                    "The Vulkan build was installed, but no working Vulkan device was detected; check Aurora GPU drivers before rerunning"
                )

    def apply(self):
        lock = self.files.target(".local/state/vixygrey-setup/lock")
        lock.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SafetyError("Another setup process holds the setup lock") from None
            # Replan inside the lock, not from stale preflight state.
            self.steps.clear()
            self.blocks.clear()
            self.preserved.clear()
            self.dependencies.clear()
            self.brew_packages = None
            self.manager_packages.clear()
            self.plan()
            if self.blocks:
                raise SafetyError("Preflight changed; no installation was started")
            for kind, payload in self.steps:
                if kind == "dependency":
                    self.command(["brew", "install", "--formula", payload])
                elif kind == "flathub":
                    self.command(
                        [
                            "flatpak",
                            "remote-add",
                            "--user",
                            "--if-not-exists",
                            "flathub",
                            "https://dl.flathub.org/repo/flathub.flatpakrepo",
                        ]
                    )
                elif kind == "app":
                    self.install_app(payload)
                elif kind == "file":
                    name, data, mode = payload
                    status = self.files.put(name, data, mode)
                    print(f"{status.upper()} {name}")
                    if status in {"preserve", "protected"}:
                        self.preserved.append(name)
                elif kind == "desktop":
                    self.command(["plasma-apply-colorscheme", "DraculaSakura"])
                    self.command(
                        [
                            "plasma-apply-wallpaperimage",
                            str(self.files.home / ".local/share/wallpapers/DraculaSakura.jpg"),
                        ]
                    )
                elif kind == "bat-cache":
                    self.command(["bat", "cache", "--build"])

    def plan(self):
        for entry in self.selected:
            self.plan_app(entry)
            for name, data, mode in launchers(entry, self.files.home):
                self.plan_file(name, data, mode)
        if not self.args.apps_only:
            self.plan_theme()
        for kind, payload in self.steps:
            if kind == "app":
                print(
                    f"INSTALL {payload['id']} via {payload['method']}: {payload['package']} {payload.get('version', '')}".rstrip()
                )
            elif kind not in {"file"}:
                print(f"PLAN {kind}: {payload or ''}")
        for block in self.blocks:
            print("BLOCKED " + block)
        print(
            f"Plan: {len(self.steps)} actions, {len(self.blocks)} blockers, {len(self.preserved)} preserved conflicts."
        )


def main(argv=None) -> int:
    if sys.version_info < (3, 11):
        raise SafetyError("Python 3.11+ is required")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Execute the plan; otherwise read-only"
    )
    parser.add_argument("--apply-plan", metavar="FILE", help="Apply a reviewed JSON plan")
    parser.add_argument("--format", choices=("text", "json"), default=None)
    parser.add_argument("--plan-out", metavar="FILE", help="Write the JSON plan artifact")
    parser.add_argument(
        "--list", action="store_true", help="Print catalog with install methods, notes, and sources"
    )
    parser.add_argument(
        "--validate-catalog", action="store_true", help="Validate catalog data without planning"
    )
    parser.add_argument(
        "--status", action="store_true", help="Report read-only installation status"
    )
    parser.add_argument("--doctor", action="store_true", help="Report read-only machine readiness")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="ID[,ID]",
        help="Select specific catalog IDs or aliases",
    )
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        metavar="ID[,ID]",
        help="Explicitly exclude apps, including blocked entries",
    )
    parser.add_argument(
        "--trust",
        action="append",
        default=[],
        metavar="ID[,ID]",
        help="Approve the named third-party sources for this run",
    )
    parser.add_argument(
        "--include-optional", action="store_true", help="Include tentative requests such as mkcert"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apps-only", action="store_true")
    group.add_argument("--theme-only", action="store_true")
    parser.add_argument(
        "--replace",
        action="append",
        default=[],
        metavar="RELATIVE_PATH",
        help="Back up and replace exactly this conflicting home file; never symlinks",
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Activate KDE colors and wallpaper, preserving other desktop settings",
    )
    args = parser.parse_args(argv)
    if args.validate_catalog:
        if any(
            (
                args.apply,
                args.apply_plan,
                args.format,
                args.plan_out,
                args.list,
                args.status,
                args.doctor,
                args.only,
                args.skip,
                args.trust,
                args.include_optional,
                args.apps_only,
                args.theme_only,
                args.replace,
                args.desktop,
            )
        ):
            parser.error("--validate-catalog cannot be combined with other options")
        print(f"Catalog valid: {len(catalog())} entries")
        return 0
    if args.apply_plan and any(
        (
            args.apply,
            args.status,
            args.doctor,
            args.list,
            args.format is not None,
            args.plan_out,
            args.only,
            args.skip,
            args.trust,
            args.include_optional,
            args.apps_only,
            args.theme_only,
            args.replace,
            args.desktop,
        )
    ):
        parser.error("--apply-plan cannot be combined with other plan options")
    if args.status and any(
        (
            args.apply,
            args.apply_plan,
            args.doctor,
            args.list,
            args.plan_out,
            args.replace,
            args.desktop,
        )
    ):
        parser.error(
            "--status cannot be combined with apply, planning, replacement, or desktop options"
        )
    if args.doctor and any(
        (
            args.apply,
            args.apply_plan,
            args.status,
            args.list,
            args.plan_out,
            args.only,
            args.skip,
            args.trust,
            args.include_optional,
            args.apps_only,
            args.theme_only,
            args.replace,
            args.desktop,
        )
    ):
        parser.error("--doctor cannot be combined with selection, apply, or planning options")
    if args.list and args.format is not None:
        parser.error("--list does not support --format")
    if args.plan_out and args.format != "json":
        parser.error("--plan-out requires --format json")
    args.format = args.format or "text"
    approved = load_plan(args.apply_plan) if args.apply_plan else None
    if approved:
        for name, value in approved["intent"].items():
            setattr(args, name, value)
        args.apply = True
    if args.only and not tokens(args.only):
        parser.error("--only requires at least one application")
    if args.desktop and args.apps_only:
        parser.error("--desktop cannot be used with --apps-only")
    if args.theme_only and (args.only or args.skip or args.trust or args.include_optional):
        parser.error("Application selection flags cannot be used with --theme-only")
    entries = catalog()
    aliases = {}
    for entry in entries:
        for name in [entry["id"], entry["name"], *entry.get("aliases", [])]:
            key = name.lower().strip()
            if key in aliases and aliases[key] != entry["id"]:
                raise SafetyError(f"Ambiguous catalog alias: {name}")
            aliases[key] = entry["id"]
    for flag in ("only", "skip", "trust"):
        raw = {name.lower() for name in tokens(getattr(args, flag))}
        unknown = raw - aliases.keys()
        if unknown:
            parser.error(f"Unknown --{flag} entries: {', '.join(sorted(unknown))}; use --list")
        setattr(args, flag, [aliases[name] for name in raw])
    if args.list:
        for entry in entries:
            print(
                f"{entry['id']} [{entry['method']}{'; optional' if entry.get('optional') else ''}] {entry['package']}\n  {entry['notes']}\n  {entry['source']}"
            )
        return 0
    setup = Setup(args)
    value = intent(args)
    setup.selected = select(entries, value)
    if args.doctor:
        print_report(setup.doctor_document(), args.format)
        return 0
    if args.status:
        print_report(setup.status_document(), args.format)
        return 0
    if approved and approved["catalog_digest"] != catalog_digest():
        raise SafetyError("Plan catalog digest does not match this checkout")
    if args.apply and (os.geteuid() == 0 or not aurora()):
        raise SafetyError(
            "Apply requires Aurora Linux and a non-root user. Preview is supported on other hosts."
        )
    if approved and approved["selected_ids"] != sorted(entry["id"] for entry in setup.selected):
        raise SafetyError("Plan selection intent does not match the current catalog")
    if args.format == "json":
        with contextlib.redirect_stdout(None):
            setup.plan()
        document = plan_document(setup, value)
        output = plan_bytes(document)
        if args.plan_out:
            write_plan(args.plan_out, output)
        sys.stdout.buffer.write(output)
    elif approved:
        setup.apply()
        return 3 if setup.preserved else 0
    else:
        setup.plan()
    if setup.blocks:
        return 2
    if args.apply:
        setup.apply()
    return 3 if setup.preserved else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SafetyError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
    except KeyboardInterrupt:
        print("Interrupted. Completed changes remain; rerun to reconcile.", file=sys.stderr)
        raise SystemExit(130)
