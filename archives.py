"""Pinned HTTPS artifacts. Extract data, never archive paths, hooks, or device nodes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import posixpath
import shlex
import tarfile
import tempfile
import urllib.request
import zipfile

from safe_files import Files, SafetyError, digest, relative_path

MAX_DOWNLOAD = 512 * 1024 * 1024
MAX_EXPANDED = 2 * 1024 * 1024 * 1024
FONT_DIRECTORY = ".local/share/fonts/JetBrainsMonoNerd"


def _font_name(path: str) -> bool:
    if not isinstance(path, str):
        return False
    prefix = FONT_DIRECTORY + "/"
    return (
        path.startswith(prefix)
        and "/" not in path[len(prefix) :]
        and path[len(prefix) :] not in {"", ".", ".."}
        and path.lower().endswith((".ttf", ".otf"))
    )


def font_receipt(entry: dict, files: Files) -> dict:
    path = files.target(receipt_path(entry))
    if not path.exists():
        return {}
    try:
        receipt = json.loads(files.read(path))
    except (ValueError, UnicodeError) as error:
        raise SafetyError(f"Invalid font receipt: {path}") from error
    if not isinstance(receipt, dict) or not all(
        isinstance(receipt.get(field), str)
        and len(receipt[field]) == 64
        and all(character in "0123456789abcdef" for character in receipt[field])
        for field in ("sha256", "spec")
    ):
        raise SafetyError(f"Invalid font receipt: {path}")
    if (
        not isinstance(receipt.get("files"), dict)
        or not isinstance(receipt.get("retired", {}), dict)
        or type(receipt.get("cache_pending", False)) is not bool
    ):
        raise SafetyError(f"Invalid font receipt: {path}")
    for inventory in (receipt["files"], receipt.get("retired", {})):
        for name, record in inventory.items():
            if (
                not _font_name(name)
                or not isinstance(record, dict)
                or not (
                    isinstance(record.get("sha256"), str)
                    and len(record["sha256"]) == 64
                    and all(character in "0123456789abcdef" for character in record["sha256"])
                    and type(record.get("mode")) is int
                    and 0 <= record["mode"] <= 0o777
                )
            ):
                raise SafetyError(f"Invalid font receipt: {path}")
    if receipt["files"].keys() & receipt.get("retired", {}).keys():
        raise SafetyError(f"Invalid font receipt: {path}")
    return receipt


def _font_receipt_bytes(receipt: dict) -> bytes:
    return json.dumps(receipt, sort_keys=True).encode() + b"\n"


def save_font_receipt(entry: dict, files: Files, receipt: dict) -> None:
    relative = receipt_path(entry)
    font_receipt(entry, files)
    data = _font_receipt_bytes(receipt)
    existing = files.target(relative).exists()
    # A validated, installer-owned receipt may be replaced; this does not approve font paths.
    if existing and relative not in files.replacements:
        files.replacements.add(relative)
        try:
            status = files.put(relative, data)
        finally:
            files.replacements.remove(relative)
    else:
        status = files.put(relative, data)
    if status in {"preserve", "protected"}:
        raise SafetyError(f"Protected font receipt: {relative}")


def machine_arch() -> str:
    return {"AMD64": "x86_64", "arm64": "aarch64"}.get(platform.machine(), platform.machine())


def artifact_for(entry: dict) -> dict:
    if entry["method"] == "font":
        return entry
    architecture = machine_arch()
    artifact = entry.get("artifacts", {}).get(architecture)
    if not artifact:
        raise SafetyError(f"{entry['id']}: no verified artifact for {architecture}")
    return artifact


def commands_for(entry: dict) -> dict[str, str]:
    if entry["method"] == "font":
        return {}
    return artifact_for(entry).get("commands", entry.get("commands", {}))


def receipt_path(entry: dict) -> str:
    return f".local/state/vixygrey-setup/receipts/{entry['id']}.json"


def installed(entry: dict, files: Files) -> bool:
    if entry["method"] == "font":
        receipt = font_receipt(entry, files)
        if not receipt:
            return False
    else:
        path = files.target(receipt_path(entry))
        if not path.is_file():
            return False
        receipt = json.loads(files.read(path))
    if receipt.get("sha256") != artifact_for(entry)["sha256"] or receipt.get("spec") != digest(
        json.dumps(entry, sort_keys=True).encode()
    ):
        return False
    return bool(receipt.get("files")) and all(
        files.target(name).is_file()
        and digest(files.read(files.target(name))) == record["sha256"]
        and (
            not record["mode"] & 0o111
            or files.target(name).stat().st_mode & 0o111 == record["mode"] & 0o111
        )
        for name, record in receipt["files"].items()
    )


def download(artifact: dict, destination: Path) -> None:
    url = artifact["url"]
    if not url.startswith("https://"):
        raise SafetyError("Artifacts must use HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": "vixygrey-linux-setup"})
    import hashlib

    checksum = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("xb") as stream:
        if not response.url.startswith("https://"):
            raise SafetyError("Artifact redirected away from HTTPS")
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_DOWNLOAD:
                raise SafetyError("Artifact exceeds download size limit")
            checksum.update(chunk)
            stream.write(chunk)
    if checksum.hexdigest() != artifact["sha256"]:
        raise SafetyError("Artifact SHA256 mismatch; no payload has been installed")


def tar_payload(path: Path):
    with tarfile.open(path, "r:*") as archive:
        members = {}
        total = 0
        for member in archive:
            name = member.name.removeprefix("./").rstrip("/")
            if name in {"", "."}:
                continue
            relative_path(name)
            if name in members:
                raise SafetyError(f"Duplicate archive path: {name}")
            if not (member.isdir() or member.isfile() or member.issym() or member.islnk()):
                raise SafetyError(f"Unsupported archive entry: {name}")
            total += member.size
            if total > MAX_EXPANDED:
                raise SafetyError("Archive exceeds expanded size limit")
            members[name] = member
        for name, member in members.items():
            if member.isdir():
                continue
            target = member
            seen = set()
            while target.issym() or target.islnk():
                if target.name in seen:
                    raise SafetyError("Archive contains a cyclic link")
                seen.add(target.name)
                parent = posixpath.dirname(target.name) if target.issym() else ""
                if target.linkname.startswith("/"):
                    raise SafetyError("Archive contains an absolute link")
                link = posixpath.normpath(posixpath.join(parent, target.linkname))
                relative_path(link)
                if link not in members:
                    raise SafetyError(f"Archive link target missing: {link}")
                target = members[link]
            if not target.isfile():
                raise SafetyError(f"Archive link is not a regular file: {name}")
            stream = archive.extractfile(target)
            if stream is None:
                raise SafetyError(f"Cannot read archive member: {name}")
            with stream:
                data = stream.read(MAX_EXPANDED + 1)
            if len(data) > MAX_EXPANDED:
                raise SafetyError("Archive member exceeds size limit")
            # Internal links become regular copies, so no deployed link can escape.
            yield name, data, 0o755 if target.mode & 0o111 else 0o600


def payload_for(path: Path, artifact: dict):
    format_name = artifact.get("format", "tar")
    if format_name == "raw":
        name = str(relative_path(artifact["filename"]))
        yield name, path.read_bytes(), 0o755
    elif format_name == "deb":
        # A Debian package is an ar container; only its data archive is used.
        with path.open("rb") as stream:
            if stream.read(8) != b"!<arch>\n":
                raise SafetyError("Invalid Debian ar header")
            while header := stream.read(60):
                if len(header) != 60 or header[58:] != b"`\n":
                    raise SafetyError("Invalid Debian ar member")
                size = int(header[48:58].strip())
                name = header[:16].decode("ascii").strip().rstrip("/")
                if size < 0 or size > MAX_DOWNLOAD:
                    raise SafetyError("Invalid Debian ar member size")
                data = stream.read(size)
                if len(data) != size:
                    raise SafetyError("Truncated Debian ar member")
                if size % 2:
                    stream.read(1)
                if name in {"data.tar", "data.tar.gz", "data.tar.xz", "data.tar.bz2"}:
                    with tempfile.TemporaryDirectory(prefix="vixygrey-deb-") as temporary:
                        payload = Path(temporary) / name
                        payload.write_bytes(data)
                        yield from tar_payload(payload)
                    return
        raise SafetyError("Debian package contains no supported data archive")
    elif format_name == "tar":
        yield from tar_payload(path)
    else:
        raise SafetyError(f"Unsupported archive format: {format_name}")


def wrappers(entry: dict, home: Path) -> dict[str, bytes]:
    base = home / ".local/share/vixygrey/apps" / entry["id"] / entry["version"]
    return {
        f".local/bin/{command}": (
            "#!/bin/sh\nexec " + shlex.quote(str(base / relative_path(member))) + ' "$@"\n'
        ).encode()
        for command, member in commands_for(entry).items()
    }


def _install_font(entry: dict, files: Files) -> list[str]:
    artifact = artifact_for(entry)
    relative = receipt_path(entry)
    receipt_protected = files.status(relative, b"") == "protected"
    old = {} if receipt_protected else font_receipt(entry, files)
    with tempfile.TemporaryDirectory(prefix="vixygrey-font-") as temporary:
        root = Path(temporary)
        source = root / "artifact"
        download(artifact, source)
        staged = root / "staged"
        staged.mkdir()
        outputs = {}
        with zipfile.ZipFile(source) as archive:
            if sum(info.file_size for info in archive.infolist()) > MAX_EXPANDED:
                raise SafetyError("Font archive exceeds expanded size limit")
            expanded = 0
            for info in archive.infolist():
                if info.is_dir() or not info.filename.lower().endswith((".ttf", ".otf")):
                    continue
                relative_path(info.filename)
                name = PurePosixPath(info.filename).name
                destination = f"{FONT_DIRECTORY}/{name}"
                if destination in outputs:
                    raise SafetyError(f"Duplicate font filename: {name}")
                checksum = hashlib.sha256()
                with archive.open(info) as incoming, (staged / name).open("xb") as outgoing:
                    while chunk := incoming.read(1024 * 1024):
                        expanded += len(chunk)
                        if expanded > MAX_EXPANDED:
                            raise SafetyError("Font archive exceeds expanded size limit")
                        checksum.update(chunk)
                        outgoing.write(chunk)
                outputs[destination] = {"sha256": checksum.hexdigest(), "mode": 0o644}
        if not outputs:
            raise SafetyError("Font archive contains no font files")
        retired = {
            name: record
            for name, record in {**old.get("retired", {}), **old.get("files", {})}.items()
            if name not in outputs
        }
        receipt = {
            "sha256": artifact["sha256"],
            "spec": digest(json.dumps(entry, sort_keys=True).encode()),
            "files": outputs,
            "retired": retired,
            "cache_pending": True,
        }
        conflicts = []
        for destination in sorted(outputs):
            name = PurePosixPath(destination).name
            status = files.status(destination, (staged / name).read_bytes(), 0o644)
            if status in {"preserve", "protected"}:
                conflicts.append((destination, status))
        receipt_status = files.status(relative, _font_receipt_bytes(receipt))
        if receipt_status == "protected" or (receipt_status == "preserve" and not old):
            conflicts.append((relative, receipt_status))
        if conflicts:
            for name, status in conflicts:
                advice = (
                    "protected path; remove the symlink or obstruction before retrying"
                    if status == "protected"
                    else f"approve exactly --replace {name}"
                )
                print(f"CONFLICT {name}: {advice}")
            return [name for name, _ in conflicts]
        for destination in sorted(outputs):
            name = PurePosixPath(destination).name
            status = files.put(destination, (staged / name).read_bytes(), 0o644)
            if status in {"preserve", "protected"}:
                raise SafetyError(f"Font destination changed during deployment: {destination}")
        save_font_receipt(entry, files, receipt)
    return []


def install(entry: dict, files: Files) -> list[str]:
    if entry["method"] == "font":
        return _install_font(entry, files)
    artifact = artifact_for(entry)
    outputs = {}
    preserved = []
    for name, data in wrappers(entry, files.home).items():
        if files.status(name, data) in {"preserve", "protected"}:
            raise SafetyError(
                f"Command path conflict: {name}; explicitly --replace it or preserve the existing tool"
            )
    with tempfile.TemporaryDirectory(prefix="vixygrey-download-") as temporary:
        path = Path(temporary) / "artifact"
        download(artifact, path)
        payload = payload_for(path, artifact)
        base = f".local/share/vixygrey/apps/{entry['id']}/{entry['version']}"
        members = set()
        expanded = 0
        for name, data, mode in payload:
            expanded += len(data)
            if expanded > MAX_EXPANDED:
                raise SafetyError("Payload exceeds expanded size limit")
            members.add(name)
            target = f"{base}/{name}"
            status = files.put(target, data, mode)
            if status in {"preserve", "protected"}:
                preserved.append(target)
            else:
                outputs[target] = {"sha256": digest(data), "mode": mode}
        for command, member in commands_for(entry).items():
            if member not in members:
                raise SafetyError(f"Archive does not contain declared command: {member}")
        for name, data in wrappers(entry, files.home).items():
            if files.put(name, data, 0o755) in {"preserve", "protected"}:
                preserved.append(name)
            else:
                outputs[name] = {"sha256": digest(data), "mode": 0o755}
    if not preserved:
        receipt = (
            json.dumps(
                {
                    "sha256": artifact["sha256"],
                    "spec": digest(json.dumps(entry, sort_keys=True).encode()),
                    "files": outputs,
                },
                sort_keys=True,
            ).encode()
            + b"\n"
        )
        relative = receipt_path(entry)
        # Only an installer-owned receipt is automatically updated, never app configuration.
        previous = files.target(relative)
        if previous.exists():
            files.replacements.add(relative)
        files.put(relative, receipt)
    return preserved
