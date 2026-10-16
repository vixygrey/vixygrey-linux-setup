# Vixygrey Linux Setup

Personal setup for **Aurora Linux**, with Aurora DX's Docker Engine and the Dracula-Sakura appearance from the existing Mac setup.

The catalog covers all 123 requested names as 122 distinct applications. `soffice` is part of LibreOffice. Docker Engine is the explicitly approved replacement for Docker Desktop. `mkcert` remains optional.

## Before using it

- Run as your normal user, **never with `sudo`**.
- Complete Aurora's normal provisioning first. Python 3.11+, Homebrew, and Flatpak must be available for the relevant selections. This repository does not bootstrap them with downloaded shell scripts.
- The catalog has x86_64 and aarch64 vendor artifacts. Preview uses the current machine's architecture. Cfait has an official x86_64 binary; its aarch64 route builds the official crate and checks for C development headers.
- The standard `~/.config` and `~/.local/share` locations are supported. Equivalent canonical paths, including Aurora's `/home` aliases, are accepted. A genuinely different XDG location is blocked rather than written incorrectly.
- Review the catalog and the plan before applying. The setup is not an OS installer or a replacement for system backups.

Aurora's recommended software model is [Flatpak, Homebrew, then containers](https://docs.getaurora.dev/guides/software/), not normal host `dnf` installation. This setup never layers RPMs, changes the OS image, alters groups, enables system services, or changes your login shell.

### Docker Engine

Docker Engine is supplied by [Aurora DX](https://docs.getaurora.dev/dx/aurora-dx-intro/). On standard Aurora, run `ujust devmode` separately and follow its reboot instructions. Aurora documents `ujust dx-group` followed by logging out and back in for group access.

**Docker group access is effectively root access.** These operations are deliberately not automated. The setup checks `/usr/bin/docker` and `/usr/bin/dockerd`, then queries only the local `/var/run/docker.sock`, not an existing remote Docker context. Missing or inaccessible Engine access blocks the full plan unless `docker-engine` is explicitly skipped.

## Preview and install

```sh
# Application IDs, sources, methods, and notes. No installation.
./setup.sh --list

# Preview the entire catalog and theme. No installation or configuration writes.
./setup.sh

# Start with a small selection, without changing dotfiles.
./setup.sh --apps-only --only micro,bat,eza,git,starship
./setup.sh --apps-only --only micro,bat,eza,git,starship --apply
```

A preview can run on this Mac; `--apply` requires Aurora and a non-root user. Read-only package queries may use package managers' own caches or locks.

Third-party taps, registries, vendor artifacts, and catalog-marked Flatpaks need explicit source approval. Approval is per application and per invocation:

```sh
./setup.sh --apps-only --only omp,kiro --trust omp,kiro
./setup.sh --apps-only --only omp,kiro --trust omp,kiro --apply
```

For the full catalog, omit `--only` and approve each reported third-party ID with `--trust`. Flags accept comma-separated IDs and can be repeated. There is no implicit trust-all or ignore-errors mode. **Any blocker prevents installation from starting.** Use `--skip` only for applications you intentionally exclude:

```sh
./setup.sh --skip docker-engine
./setup.sh --apps-only --only mkcert --apply
```

`mkcert` is otherwise excluded unless `--include-optional` is passed. Installing its executable does **not** run `mkcert -install` or alter certificate trust.

### Theme and existing machines

```sh
# Preview or deploy appearance files without installing packages.
./setup.sh --theme-only
./setup.sh --theme-only --apply

# Also activate the KDE color scheme and wallpaper in an active Plasma session.
./setup.sh --theme-only --desktop
./setup.sh --theme-only --desktop --apply
```

Appearance files use the local Mac palette and wallpaper, with Linux-specific adaptations:

- KDE colors and wallpaper; Kitty and JetBrainsMono Nerd Font settings.
- Starship, Micro, Bat, btop, Yazi, Zellij, Lazygit, Lazydocker, Atuin, Posting, and Fastfetch.
- Kiro editor and terminal colors; lnav, Trippy, Chawan, E1s, Claws, and Eilmeldung.
- Cfait's supported built-in Dracula theme and Leaf's Micro editor handoff. Apps without a custom palette inherit terminal colors where supported; this does not claim to recolor every Flatpak or web interface.

Missing files are installed; identical files are left unchanged. Different existing files are **preserved**, including on repeat runs. Symlink destinations and symlink ancestors are protected, even with replacement consent. No configuration merge is attempted.

To replace one particular regular file after reviewing it, use its exact path relative to your home:

```sh
./setup.sh --theme-only --replace .config/kitty/kitty.conf
./setup.sh --theme-only --replace .config/kitty/kitty.conf --apply
```

Original bytes are backed up privately under:

```text
~/.local/state/vixygrey-setup/backups/<unique-id>/<original-home-relative-path>
```

The command prints the exact backup path. Restore a file by reviewing that backup and copying it to its original location. Backups can contain personal configuration; keep this state directory private and outside this repository.

### Shell activation

The managed `.zshrc` is installed only if missing or explicitly approved for replacement. It sources `~/.config/vixygrey/setup.zsh` and, if present, your `~/.zshrc.local`.

If preserving an existing `.zshrc`, add this line yourself after reviewing the fragment:

```zsh
source "$HOME/.config/vixygrey/setup.zsh"
```

Start Zsh to use it. The setup does not call `chsh`. Shell integration includes stable Linuxbrew and user tool paths, the themed prompt, FZF colors, Atuin, direnv, mise, the Zsh plugins, and Granted's interactive `assume` alias. Interactive hooks require an actual terminal. Existing direnv/mise trust checks remain in force; nothing authorizes project scripts automatically.

Atuin cloud sync is disabled in the shipped config. An existing conflicting Atuin config is preserved, so its existing settings still govern behavior.

## Package behavior and important constraints

The complete source of truth is [`catalog/core.json`](catalog/core.json) and [`catalog/extended.json`](catalog/extended.json). `--list` shows every requested application. Sources were resolved using the Mac Brewfile, installed configuration, existing Mac setup implementation, and upstream Linux documentation.

| Route | Behavior |
| --- | --- |
| Homebrew | CLI formulas, never casks. Existing formulas are skipped. Missing manager prerequisites are planned explicitly. No automatic global upgrade or cleanup. |
| Flatpak | Missing apps install per user from Flathub. An existing system installation is left in place. A conflicting user `flathub` URL blocks installation. LibreOffice/`soffice`, mpv, and VLC receive conflict-preserving CLI wrappers. |
| Vendor archives | Versioned HTTPS downloads with catalog SHA256 checks. Payloads stay in versioned user directories, with executable wrappers and GUI launchers. No archive install hooks, device nodes, escaping paths, escaping links, or setuid bits. |
| Go | Exact module versions, built into temporary staging before conflict-safe executable deployment. Clipse uses the Wayland build and `wl-clipboard`; no clipboard listener starts automatically. |
| uv / npm | Exact top-level package versions in user-owned locations. Cheznav requests Python 3.14 through uv. Python tools may download a compatible managed interpreter. |
| Cfait source fallback | aarch64 uses Cargo with the upstream lockfile and a user-local build toolchain. Missing native C headers block preflight; no host layering is attempted. |
| `yaml-py` | A private uv environment containing PyYAML, exposed as a Python interpreter command, matching the Mac helper rather than substituting a different YAML CLI. |

### Special applications

- **llama.cpp:** the pinned upstream Vulkan bundle is used, not a CPU-only Homebrew substitute. Installation must detect a Vulkan device with `llama-cli --list-devices`. A working host Vulkan driver and compatible runtime libraries are required. No model downloads or server services are configured.
- **Kiro:** the official portable Linux bundle is installed user-locally. It needs the host's normal Electron desktop libraries and unprivileged user namespaces. The setup never adds `--no-sandbox`, sets a root-owned sandbox helper, or disables OS security policy.
- **AWS Session Manager Plugin:** the official versioned Debian payload is unpacked into a private application directory. No Debian maintainer scripts run and nothing is written to host `/usr` or `/etc`.
- **Granted / AWS / ngrok / Bitwarden / OMP:** credentials, accounts, tokens, profiles, and login flows remain yours to configure. No credentials are imported from the Mac.
- **Borg / borgmatic:** the tools are installed, but no repositories, remote destinations, passphrases, pruning policy, backup jobs, or timers are invented.
- **Clipse / network diagnostics / Caligula:** no background clipboard capture, uinput permissions, network capabilities, or disk writes are enabled by setup. Privileged runtime actions remain explicit user decisions.

### Repeated runs, changes, and failure

Package-manager state is inspected rather than trusting a generic "done" marker. Archive receipts also check deployed file hashes and executable permissions. Existing Homebrew and Flatpak installations are not upgraded automatically. Registry installs use their pinned versions; if a manager refuses a conflicting existing version, the setup stops rather than forcing replacement.

Archive wrapper changes, including version changes, require explicit `--replace .local/bin/<command>` approval. Existing modified payload files remain protected. Older version directories are not pruned automatically. Receipts live under `~/.local/state/vixygrey-setup/receipts/`.

Only one setup process can apply at a time. Commands stop at the first failure. Successfully completed package installs remain; this is **not a transaction across package managers**, and rollback does not uninstall dependencies. Rerun after resolving the reported failure to reconcile state.

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Plan/apply completed without blockers or preserved conflicts |
| 2 | Preflight blocked, invalid input, unsupported platform, or an operation failed |
| 3 | Existing configuration or launcher conflicts were intentionally preserved |
| 130 | Interrupted; completed changes remain |

## Security model

Review this repository and its catalog before execution. Homebrew core and the Flathub remote are baseline package sources; catalog-marked additional sources require explicit approval. Package-manager builds, package install scripts, application binaries, and shell initialization hooks still execute code as your user. **Approval is not sandboxing or a security audit.**

TLS and hashes protect downloads against unexpected changes. Hashes are publisher-provided where available, or computed from the versioned official HTTPS artifact where noted. They do not independently prove publisher identity or make a compromised upstream safe. A changed artifact fails closed; refreshing a pin requires reviewing the source and replacing its checksum deliberately.

Top-level registry versions and vendor assets are pinned, but this is not a fully reproducible supply-chain lock: Homebrew/Flatpak use their current catalogs, and registry transitive dependencies can change. OS updates and application vulnerability maintenance remain necessary.

Do not put cloud credentials, SSH keys, Bitwarden exports, shell history, Atuin databases, browser profiles, rclone remotes, backup secrets, or generated state in this repository.

## Verification

```sh
python3 -B -m unittest discover -s tests -v
zsh -n dotfiles/.zshrc dotfiles/.config/vixygrey/setup.zsh
shellcheck setup.sh
```

The safety suite covers preservation, backups, symlink/traversal rejection, executable modes, archive links and setuid stripping, font filtering, Debian-container boundaries, invalid selections, source approval, and canonical home aliases.

During development on the reference Mac, isolated smoke runs exercised actual theme deployment and repeat planning; Bat, Starship, lnav, Fastfetch, interactive Zsh, and the btop TUI; PyYAML installation and parsing; staged Clipse compilation; and checksum-verified AWS, Eilmeldung, Kitty, OMP, Nerd Font, and Kiro payload installation without executing the Linux binaries. A live local HTTPS fixture also verified executable deployment under a home path containing spaces and rejection of a changed download before any home writes.

**The full application install, Linux binary execution, Vulkan device detection, and KDE desktop activation have not been run on an Aurora target.** A local Docker daemon was unavailable. Validate the plan on the intended machine before approving an apply run, and validate the desktop there before treating its appearance as verified.
