"""User launchers for portable GUI bundles and Flatpak CLI entry points."""
from pathlib import Path


def desktop_quote(value: str) -> str:
    if any(ord(character) < 32 for character in value):
        raise ValueError('Desktop launcher paths cannot contain control characters')
    value = value.replace('\\', '\\\\\\\\').replace('"', '\\\\"').replace('`', '\\\\`').replace('$', '\\\\$')
    return '"' + value.replace('%', '%%') + '"'


def launchers(entry: dict, home: Path):
    identifier = entry['id']
    if entry['method'] == 'flatpak':
        names = {'libreoffice': ['libreoffice', 'soffice'], 'mpv': ['mpv'], 'vlc': ['vlc']}.get(identifier, [])
        for name in names:
            yield f'.local/bin/{name}', f'#!/bin/sh\nexec flatpak run {entry["package"]} "$@"\n'.encode(), 0o755
    if identifier not in {'kitty', 'kiro'}:
        return
    base = home / '.local/share/vixygrey/apps' / identifier / entry['version']
    if identifier == 'kitty':
        name, command, icon, category = 'kitty', 'bin/kitty', 'share/icons/hicolor/256x256/apps/kitty.png', 'System;TerminalEmulator;'
    else:
        name, command, icon, category = 'Kiro', 'Kiro/kiro', 'Kiro/resources/app/resources/linux/code.png', 'Development;IDE;'
    content = (
        '[Desktop Entry]\nType=Application\n'
        f'Name={name}\nExec={desktop_quote(str(base / command))}\n'
        f'Icon={base / icon}\nTerminal=false\nCategories={category}\n'
    )
    yield f'.local/share/applications/vixygrey-{identifier}.desktop', content.encode(), 0o644
