"""User launchers for portable GUI bundles and Flatpak CLI entry points."""

from pathlib import Path


def desktop_quote(value: str) -> str:
    if any(ord(character) < 32 for character in value):
        raise ValueError("Desktop launcher paths cannot contain control characters")
    value = (
        value.replace("\\", "\\\\\\\\")
        .replace('"', '\\\\"')
        .replace("`", "\\\\`")
        .replace("$", "\\\\$")
    )
    return '"' + value.replace("%", "%%") + '"'


def launchers(entry: dict, home: Path):
    identifier = entry["id"]
    if entry["method"] == "web":
        content = (
            "[Desktop Entry]\nType=Application\n"
            f"Name={entry['name']}\nExec=xdg-open {desktop_quote(entry['package'])}\n"
            "Icon=web-browser\nTerminal=false\nCategories=Office;\n"
        )
        yield f".local/share/applications/vixygrey-{identifier}.desktop", content.encode(), 0o644
        return
    if entry["method"] == "flatpak":
        names = {"libreoffice": ["libreoffice", "soffice"], "vlc": ["vlc"]}.get(identifier, [])
        for name in names:
            yield (
                f".local/bin/{name}",
                f'#!/bin/sh\nexec flatpak run {entry["package"]} "$@"\n'.encode(),
                0o755,
            )
    if identifier not in {"kitty", "kiro", "zed", "bruno"}:
        return
    base = home / ".local/share/vixygrey/apps" / identifier / entry["version"]
    if identifier == "kitty":
        name, command, icon, category = (
            "kitty",
            "bin/kitty",
            "share/icons/hicolor/256x256/apps/kitty.png",
            "System;TerminalEmulator;",
        )
    elif identifier == "zed":
        name, command, icon, category = (
            "Zed",
            "zed.app/bin/zed",
            "zed.app/share/icons/hicolor/512x512/apps/zed.png",
            "Utility;TextEditor;Development;IDE;",
        )
    elif identifier == "bruno":
        name, command, icon, category = (
            "Bruno",
            "opt/Bruno/bruno",
            "usr/share/icons/hicolor/512x512/apps/bruno.png",
            "Development;",
        )
    else:
        name, command, icon, category = (
            "Kiro",
            "Kiro/kiro",
            "Kiro/resources/app/resources/linux/code.png",
            "Development;IDE;",
        )
    arguments = " %U" if identifier in {"zed", "bruno"} else ""
    content = (
        "[Desktop Entry]\nType=Application\n"
        f"Name={name}\nExec={desktop_quote(str(base / command))}{arguments}\n"
        f"Icon={base / icon}\nTerminal=false\nCategories={category}\n"
    )
    if identifier == "zed":
        content += (
            "StartupNotify=true\nMimeType=text/plain;application/x-zerosize;x-scheme-handler/zed;\n"
        )
    elif identifier == "bruno":
        content += "StartupWMClass=Bruno\nMimeType=x-scheme-handler/bruno;\n"
    yield f".local/share/applications/vixygrey-{identifier}.desktop", content.encode(), 0o644
