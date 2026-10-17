"""User-owned file deployment. Never follow symlinks or overwrite without consent."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile
import uuid


class SafetyError(RuntimeError):
    pass


def relative_path(value: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or path == Path("."):
        raise SafetyError(f"Unsafe relative path: {value!r}")
    return path


class Files:
    def __init__(self, home: Path, replacements=()):
        self.home = home.resolve(strict=True)
        self.replacements = {str(relative_path(p)) for p in replacements}
        self.backups: list[Path] = []

    def target(self, relative: str) -> Path:
        path = self.home / relative_path(relative)
        for parent in [path, *path.parents]:
            if parent == self.home:
                break
            if parent.is_symlink():
                raise SafetyError(f"Refusing symlink: {parent}")
            if parent.exists() and parent != path and not parent.is_dir():
                raise SafetyError(f"Not a directory: {parent}")
        return path

    def status(self, relative: str, data: bytes, mode: int = 0o600) -> str:
        try:
            path = self.target(relative)
        except SafetyError:
            return "protected"
        if not path.exists():
            return "create"
        if not path.is_file():
            return "protected"
        if self.read(path) == data:
            if mode & 0o111 and path.stat().st_mode & 0o777 != mode:
                return "mode"
            return "unchanged"
        return "replace" if relative in self.replacements else "preserve"

    @staticmethod
    def read(path: Path) -> bytes:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise SafetyError(f"Not a regular file: {path}")
            return stream.read()

    def directory(self, relative: str) -> Path:
        path = self.target(relative)
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        return path

    def put(self, relative: str, data: bytes, mode: int = 0o600) -> str:
        status = self.status(relative, data, mode)
        if status == "mode":
            os.chmod(self.target(relative), mode, follow_symlinks=False)
            return status
        if status in {"unchanged", "preserve", "protected"}:
            return status
        path = self.target(relative)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        original = None
        if status == "replace":
            original = self.read(path)
            backup = self.target(
                f".local/state/vixygrey-setup/backups/{uuid.uuid4().hex}/{relative}"
            )
            backup.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(original)
                stream.flush()
                os.fsync(stream.fileno())
            self.backups.append(backup)
            print(f"BACKUP {relative} -> {backup}")
        fd, temporary = tempfile.mkstemp(prefix=".vixygrey-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                os.fchmod(stream.fileno(), mode)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            self.target(relative)
            if original is None:
                # Linking fails atomically if another process created the destination.
                os.link(temporary, path)
            else:
                if self.read(path) != original:
                    raise SafetyError(f"File changed during deployment: {relative}")
                os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return status


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
