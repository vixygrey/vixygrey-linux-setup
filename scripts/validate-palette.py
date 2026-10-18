#!/usr/bin/env python3
"""Validate managed Dracula-Sakura colors without modifying application configuration."""

import argparse
import configparser
import json
import plistlib
import re
import sys
import tomllib
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CONFIG = Path("dotfiles/.config")
KITTY = CONFIG / "kitty/kitty.conf"
KIRO = CONFIG / "Kiro/User/settings.json"
STARSHIP = CONFIG / "starship.toml"
BAT = CONFIG / "bat/themes/Dracula-Sakura.tmTheme"
MICRO = CONFIG / "micro/colorschemes/dracula-sakura.micro"
BTOP = CONFIG / "btop/themes/dracula-sakura.theme"
KDE = Path("dotfiles/.local/share/color-schemes/DraculaSakura.colors")
SURFACES = (
    KITTY,
    KIRO,
    STARSHIP,
    BAT,
    MICRO,
    BTOP,
    KDE,
    CONFIG / "bat/config",
    CONFIG / "micro/settings.json",
    CONFIG / "btop/btop.conf",
    CONFIG / "fastfetch/config.jsonc",
    CONFIG / "lazydocker/config.yml",
    CONFIG / "trippy/trippy.toml",
    CONFIG / "yazi/theme.toml",
    CONFIG / "vixygrey/setup.zsh",
)
HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
BARE = re.compile(r"[0-9a-fA-F]{6}\Z")
ANSI = (
    "panel_soft",
    "red",
    "mint",
    "yellow",
    "lilac",
    "rose",
    "cyan",
    "fg",
    "comment",
    "red",
    "mint",
    "yellow",
    "lilac",
    "blush",
    "cyan",
    None,
)
CORE = {
    KITTY: {
        "background": "bg",
        "foreground": "fg",
        "selection_background": "selection",
        "cursor": "rose",
        "url_color": "cyan",
    },
    KIRO: {
        "editor.background": "bg",
        "editor.foreground": "fg",
        "editor.selectionBackground": "selection",
        "editor.lineHighlightBackground": "panel_soft",
        "editorLineNumber.foreground": "comment",
        "editorLineNumber.activeForeground": "lilac",
        "terminal.background": "bg",
        "terminal.foreground": "fg",
    },
    BAT: {
        "background": "bg",
        "foreground": "fg",
        "lineHighlight": "panel",
        "selection": "selection",
        "caret": "rose",
    },
    MICRO: {
        "default": "fg",
        "comment": "comment",
        "constant.string": "yellow",
        "statement": "rose",
        "type": "cyan",
        "special": "mint",
        "current-line-number": "rose",
        "cursor-line": "panel",
    },
    BTOP: {
        "main_bg": "bg",
        "main_fg": "fg",
        "selected_bg": "selection",
        "inactive_fg": "comment",
        "meter_bg": "panel",
    },
    KDE: {
        "Colors:Window.BackgroundNormal": "bg",
        "Colors:Window.ForegroundNormal": "fg",
        "Colors:Selection.BackgroundNormal": "selection",
        "Colors:Selection.ForegroundNormal": "fg",
        "WM.activeBackground": "panel",
        "WM.inactiveBackground": "bg",
    },
}
SYNTAX = {
    "comments": "comment",
    "keywords": "rose",
    "strings": "yellow",
    "numbers": "lilac",
    "functions": "mint",
    "types": "cyan",
    "variables": "fg",
}


def require(condition, path, role, explanation):
    if not condition:
        raise ValueError(f"{path}: {role}: {explanation}")


def mapping(value, path, role) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{path}: {role}: expected object")
    return value


def role(values, key, expected, palette, path):
    require(key in values, path, key, "missing required role")
    require(
        values[key] == palette[expected],
        path,
        key,
        f"expected {expected} ({palette[expected]}), got {values[key]!r}",
    )


def colors(values, palette, path, exception=()):
    for key, color in values.items():
        require(
            isinstance(color, str) and HEX.fullmatch(color),
            path,
            key,
            f"invalid color {color!r}; expected #RRGGBB",
        )
        require(
            color.lower() in palette.values() or (key in exception and color.lower() == "#ffffff"),
            path,
            key,
            f"color {color!r} is not in palette",
        )


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def line_fields(path, pattern):
    result = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = pattern.fullmatch(line.strip())
        require(match is not None, path, f"line {number}", "invalid themed field")
        key, value = match.groups()
        require(key not in result, path, key, "duplicate role")
        result[key] = value
    return result


def nested_colors(value, path, palette, prefix=""):
    if isinstance(value, dict):
        for key, child in value.items():
            nested_colors(child, path, palette, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            nested_colors(child, path, palette, f"{prefix}[{index}]")
    elif isinstance(value, str) and value.startswith("#"):
        colors({prefix: value}, palette, path)


def validate(root):
    palette_path = root / "theme/palette.json"
    canonical = mapping(read_json(palette_path), palette_path, "palette")
    palette = mapping(canonical.get("colors"), palette_path, "colors")
    require(
        canonical.get("name") == "Dracula-Sakura", palette_path, "name", "unexpected palette name"
    )
    require(
        set(palette)
        == {
            "bg",
            "panel",
            "panel_soft",
            "current",
            "selection",
            "fg",
            "muted",
            "dim",
            "comment",
            "cyan",
            "mint",
            "peach",
            "rose",
            "blush",
            "lilac",
            "red",
            "yellow",
        },
        palette_path,
        "colors",
        "missing or extra named roles",
    )
    colors(palette, palette, palette_path)
    require(
        len(set(palette.values())) == len(palette), palette_path, "colors", "duplicate named colors"
    )
    for relative in SURFACES:
        require((root / relative).is_file(), root / relative, "surface", "missing themed file")
    shell = root / CONFIG / "vixygrey/setup.zsh"
    bat_default = re.search(
        r'^export BAT_THEME="\$\{BAT_THEME:-([^}]+)\}"$', shell.read_text(encoding="utf-8"), re.M
    )
    require(
        bat_default is not None and bat_default[1] == canonical["name"],
        shell,
        "BAT_THEME",
        "default must reference the managed Bat theme",
    )

    def check(relative, values):
        colors(
            values,
            palette,
            root / relative,
            ("color15",)
            if relative == KITTY
            else ("terminal.ansiBrightWhite",)
            if relative == KIRO
            else (),
        )
        for key, expected in CORE.get(relative, {}).items():
            role(values, key, expected, palette, root / relative)

    starship = mapping(
        tomllib.loads((root / STARSHIP).read_text(encoding="utf-8")), root / STARSHIP, "document"
    )
    require(
        starship.get("palette") == "dracula_sakura",
        root / STARSHIP,
        "palette",
        "wrong palette reference",
    )
    embedded = mapping(
        starship.get("palettes", {}).get("dracula_sakura"),
        root / STARSHIP,
        "palettes.dracula_sakura",
    )
    require(
        embedded == palette,
        root / STARSHIP,
        "palettes.dracula_sakura",
        "must exactly match named palette",
    )
    kitty = line_fields(root / KITTY, re.compile(r"([^\s#]+)\s+(.+)"))
    kitty_colors = {
        k: v
        for k, v in kitty.items()
        if k in CORE[KITTY]
        or k.startswith("color")
        or k.endswith("_color")
        or k.endswith("_background")
        or k.endswith("_foreground")
        or k == "cursor"
    }
    check(KITTY, kitty_colors)
    kiro = mapping(read_json(root / KIRO), root / KIRO, "document")
    workbench = mapping(
        kiro.get("workbench.colorCustomizations"), root / KIRO, "workbench.colorCustomizations"
    )
    check(KIRO, workbench)
    syntax = mapping(
        kiro.get("editor.tokenColorCustomizations"), root / KIRO, "editor.tokenColorCustomizations"
    )
    colors(syntax, palette, root / KIRO)
    for key, expected in SYNTAX.items():
        role(syntax, key, expected, palette, root / KIRO)
    for index, expected in enumerate(ANSI):
        if expected:
            role(kitty_colors, f"color{index}", expected, palette, root / KITTY)
        suffix = ("Black", "Red", "Green", "Yellow", "Blue", "Magenta", "Cyan", "White")[index % 8]
        key = "terminal.ansi" + ("Bright" if index >= 8 else "") + suffix
        if expected:
            role(workbench, key, expected, palette, root / KIRO)
        else:
            require(
                kitty_colors.get("color15") == "#ffffff",
                root / KITTY,
                "color15",
                "expected bright white",
            )
            require(workbench.get(key) == "#ffffff", root / KIRO, key, "expected bright white")

    bat_data = mapping(plistlib.loads((root / BAT).read_bytes()), root / BAT, "plist")
    require(bat_data.get("name") == "Dracula-Sakura", root / BAT, "name", "wrong theme name")
    settings = bat_data.get("settings")
    require(
        isinstance(settings, list) and settings, root / BAT, "settings", "missing syntax settings"
    )
    bat_base = mapping(
        mapping(settings[0], root / BAT, "settings[0]").get("settings"),
        root / BAT,
        "settings[0].settings",
    )
    check(BAT, bat_base)
    scopes = {}
    for entry in settings[1:]:
        entry = mapping(entry, root / BAT, "scope")
        scope = entry.get("scope")
        if not isinstance(scope, str) or scope in scopes:
            raise ValueError(f"{root / BAT}: scope: missing/duplicate scope")
        scopes[scope] = mapping(entry.get("settings"), root / BAT, scope)
        nested_colors(scopes[scope], root / BAT, palette, scope)
    for scope, expected in {
        "comment": "comment",
        "string": "yellow",
        "constant.numeric, constant.language": "lilac",
        "keyword, storage": "rose",
        "entity.name.function, support.function": "mint",
        "entity.name.type, support.type, storage.type": "cyan",
        "variable, variable.parameter": "fg",
    }.items():
        role(scopes.get(scope, {}), "foreground", expected, palette, root / BAT)

    micro = {}
    for key, value in line_fields(
        root / MICRO, re.compile(r'color-link\s+(\S+)\s+"([^"]+)"')
    ).items():
        parts = value.split(",")
        require(len(parts) == 2, root / MICRO, key, "expected foreground,background")
        for part in parts:
            color = part.removeprefix("bold ")
            colors({key: color}, palette, root / MICRO)
        micro[key] = parts[0].removeprefix("bold ")
    for key, expected in CORE[MICRO].items():
        role(micro, key, expected, palette, root / MICRO)
    btop = line_fields(root / BTOP, re.compile(r'theme\[([^\]]+)\]="([^"]*)"'))
    check(BTOP, btop)

    kde_path = root / KDE
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = lambda optionstr: optionstr
    with kde_path.open(encoding="utf-8") as source:
        parser.read_file(source)
    kde = {}
    for section in parser.sections():
        for key, value in parser.items(section):
            if (
                section.startswith("Colors:")
                or (
                    section == "WM"
                    and ("Background" in key or "Foreground" in key or "Blend" in key)
                )
                or (section.startswith("ColorEffects:") and key == "Color")
            ):
                chunks = value.split(",")
                require(
                    len(chunks) == 3
                    and all(re.fullmatch(r"\d{1,3}", c) and int(c) <= 255 for c in chunks),
                    kde_path,
                    f"{section}.{key}",
                    f"invalid RGB {value!r}",
                )
                kde[f"{section}.{key}"] = "#" + "".join(f"{int(c):02x}" for c in chunks)
    check(KDE, kde)
    require(
        parser.get("General", "ColorScheme", fallback=None) == "DraculaSakura",
        kde_path,
        "General.ColorScheme",
        "wrong theme name",
    )
    for relative, field, extension in (
        (CONFIG / "bat/config", "--theme", ".tmTheme"),
        (CONFIG / "btop/btop.conf", "color_theme", ".theme"),
    ):
        text = (root / relative).read_text(encoding="utf-8")
        match = re.search(r"^" + re.escape(field) + r'\s*=\s*"([^"]+)"\s*$', text, re.M)
        if match is None:
            raise ValueError(f"{root / relative}: {field}: missing theme reference")
        require(
            (root / relative.parent / "themes" / (match[1] + extension)).is_file(),
            root / relative,
            field,
            f"missing theme {match[1]}{extension}",
        )
    micro_settings = mapping(
        read_json(root / CONFIG / "micro/settings.json"),
        root / CONFIG / "micro/settings.json",
        "document",
    )
    micro_name = micro_settings.get("colorscheme")
    require(
        isinstance(micro_name, str) and (root / MICRO.parent / (micro_name + ".micro")).is_file(),
        root / CONFIG / "micro/settings.json",
        "colorscheme",
        "missing theme file",
    )
    fastfetch = root / CONFIG / "fastfetch/config.jsonc"
    # This managed JSONC contains only trailing commas; remove those outside strings, then use JSON.
    text = fastfetch.read_text(encoding="utf-8")
    text = re.sub(
        r'"(?:\\.|[^"\\])*"|,\s*([}\]])',
        lambda match: match[1] if match[1] else match[0],
        text,
    )
    ff = mapping(json.loads(text), fastfetch, "document")
    logo = mapping(mapping(ff.get("logo"), fastfetch, "logo").get("color"), fastfetch, "logo.color")
    display = mapping(
        mapping(ff.get("display"), fastfetch, "display").get("color"), fastfetch, "display.color"
    )
    for values, required in ((logo, ("1", "2")), (display, ("keys", "title"))):
        colors(values, palette, fastfetch)
        for key in required:
            require(key in values, fastfetch, key, "missing color role")
    nested_colors(ff, fastfetch, palette)
    lazy = root / CONFIG / "lazydocker/config.yml"
    yaml_lines = lazy.read_text(encoding="utf-8").splitlines()
    fields = {}
    for line in yaml_lines:
        match = re.fullmatch(r'    ([A-Za-z]+Color):\s*\["([^"]*)"(?:,\s*bold)?\]', line)
        if match:
            require(match[1] not in fields, lazy, match[1], "duplicate theme color")
            fields[match[1]] = match[2]
        elif re.match(r"    [A-Za-z]+Color:", line):
            raise ValueError(f"{lazy}: {line.strip()}: invalid theme color field")
    colors(fields, palette, lazy)
    for key in (
        "activeBorderColor",
        "inactiveBorderColor",
        "selectedLineBgColor",
        "inactiveViewSelectedLineBgColor",
        "optionsTextColor",
        "defaultFgColor",
    ):
        require(key in fields, lazy, key, "missing theme role")
    for relative, table, required in (
        (
            CONFIG / "trippy/trippy.toml",
            "theme-colors",
            (
                "bg-color",
                "border-color",
                "text-color",
                "tab-text-color",
                "hops-table-header-bg-color",
                "hops-table-header-text-color",
                "hops-table-row-active-text-color",
                "hops-table-row-inactive-text-color",
                "hops-chart-selected-color",
                "hops-chart-unselected-color",
                "hops-chart-axis-color",
                "frequency-chart-bar-color",
                "frequency-chart-text-color",
                "flows-chart-bar-selected-color",
                "flows-chart-bar-unselected-color",
                "flows-chart-text-current-color",
                "flows-chart-text-non-current-color",
                "samples-chart-color",
                "samples-chart-lost-color",
                "help-dialog-bg-color",
                "help-dialog-text-color",
                "settings-dialog-bg-color",
                "settings-tab-text-color",
                "info-bar-bg-color",
                "info-bar-text-color",
                "map-world-color",
                "map-radius-color",
                "map-selected-color",
            ),
        ),
        (CONFIG / "yazi/theme.toml", "app", ("overall",)),
    ):
        path = root / relative
        parsed = mapping(tomllib.loads(path.read_text(encoding="utf-8")), path, "document")
        values = mapping(parsed.get(table), path, table)
        for key in required:
            require(key in values, path, key, "missing theme role")
        if table == "theme-colors":
            normalized = {}
            for key, value in values.items():
                require(
                    isinstance(value, str) and BARE.fullmatch(value),
                    path,
                    key,
                    f"invalid bare RGB hex {value!r}",
                )
                normalized[key] = "#" + value.lower()
            colors(normalized, palette, path)
            role(normalized, "bg-color", "bg", palette, path)
            role(normalized, "text-color", "fg", palette, path)
        else:
            nested_colors(parsed, path, palette)
            role(mapping(values["overall"], path, "app.overall"), "bg", "bg", palette, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=BASE, help="repository root (default: script parent)"
    )
    args = parser.parse_args()
    try:
        validate(args.root)
    except (
        ValueError,
        KeyError,
        OSError,
        json.JSONDecodeError,
        tomllib.TOMLDecodeError,
        plistlib.InvalidFileException,
        configparser.Error,
    ) as exc:
        print(f"palette validation failed: {exc}", file=sys.stderr)
        return 1
    print("palette validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
