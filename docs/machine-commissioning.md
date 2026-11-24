# Machine commissioning

Use this runbook before the first `--apply` on any Ryoku machine. It is a manual checklist,
not installer behavior. It does not choose partitions, mount points, power policy, backup
locations, or credentials for you.

Keep the machine decision record and unredacted evidence outside this repository. Do not commit
host names, drive serials, repository URLs, passwords, recovery material, credentials, or command
output that contains them.

## 1. Firmware, boot, and encryption

Before writing data:

1. Record the current firmware or BIOS version and whether an update is required according to the
   hardware vendor's guidance.
2. Follow Ryoku's [installation guide](https://ryoku.dev) (the CachyOS edition ISO, or the
   [existing-CachyOS one-liner](https://github.com/Ryoku-dev/ryoku/blob/main/docs/install-without-iso.md#existing-cachyos)),
   including its current Secure Boot guidance. Do not copy changing installer steps or recovery
   material into this repository.
3. Record the encryption decision for every internal storage device. Ryoku's installer configures
   encrypted Btrfs with automatic snapper/snap-pac snapshots unless turned off; this repository's
   installer does not create, modify, or unlock encrypted volumes itself.
4. Ryoku ships `power-profiles-daemon` by default; use it for the machine's power profile. Do not
   add a competing power-tuning daemon without a separate, reviewed decision.
5. On an AMD APU system with a large unified-memory pool (for example, a Framework Desktop's
   Ryzen AI Max), raising the GTT/TTM limits lets Vulkan address more of system RAM as VRAM for
   local inference. This is a kernel command-line change, not something `./setup.sh` touches:
   - The parameters: `amdgpu.gttsize=<MiB>` and `ttm.pages_limit=<4KiB pages>`. Size both to the
     fraction of total RAM you want reservable as GPU memory (for example, on a 64 GiB machine,
     `amdgpu.gttsize=57344 ttm.pages_limit=14680064` reserves roughly 56 GiB); do not reserve more
     than the system needs to keep running.
   - Ryoku's CachyOS edition boots Limine. CachyOS's own `limine-entry-tool` regenerates
     `/boot/limine.conf` (or `/boot/efi/limine.conf`) from live `/proc/cmdline` state unless
     `/etc/default/limine` exists; editing `/boot/limine.conf` directly gets silently overwritten
     on the next kernel/initramfs rebuild. Create or edit `/etc/default/limine` and **append** with
     `KERNEL_CMDLINE[default]+="amdgpu.gttsize=57344 ttm.pages_limit=14680064"` (`+=`, not `=`, or
     you will drop the existing `root=`/`rootflags=`/etc. parameters), then run
     `sudo limine-update`. Follow
     [CachyOS's current boot-manager documentation](https://wiki.cachyos.org/configuration/boot_manager_configuration/)
     for the exact procedure on your installed version, and verify with
     `cat /boot/limine.conf | grep cmdline` before rebooting.
   - After reboot, confirm with `dmesg | grep -i gtt`. Record the chosen values in the private
     decision record; reverting requires removing the line from `/etc/default/limine` and rerunning
     `sudo limine-update`.

## 2. Storage decision record

Complete a private row for every internal storage device before placing models, containers,
workspaces, or large caches on it.

| Field            | Record privately for each device                        |
| ---------------- | ------------------------------------------------------- |
| Role             | System/home, data/workspace, removable, or unused       |
| Encryption       | Encryption state and recovery process                   |
| Mount point      | Chosen path and mount ownership                         |
| Capacity         | Total, free capacity, and expected growth               |
| Data classes     | Models, containers, worktrees, caches, backups, or none |
| Backup inclusion | Included, excluded, and reason                          |
| Recovery         | How the data is restored after loss or replacement      |

Do not assume a particular drive count, filesystem, mount point, or capacity. A second internal
drive can improve capacity or local recovery options, but it is not an independent backup.

After normal Ryoku provisioning, capture the read-only result of:

```sh
./setup.sh --doctor --format json
```

Use its root and home free-space values with the decision record. Re-check capacity before a large
model download, container image pull, or workspace migration.

## 3. Data placement

The setup owns only its existing user-state locations:

- Receipts: `~/.local/state/vixygrey-setup/receipts/`
- Explicit replacement backups: `~/.local/state/vixygrey-setup/backups/`
- Portable application payloads: `~/.local/share/vixygrey/apps/`

Choose the location for every other large data class per machine:

- **Worktrees and reproducible build caches:** use the data location selected in the private record.
- **Container images and volumes:** inspect the selected Podman storage driver before reserving
  space or configuring bind mounts. This repository does not assume a runtime storage path.
- **Local models:** choose a data location only when the machine uses a supported local-model path.
  Record the capacity requirement and revisit it during the target-specific model validation.

Do not make a path a repository default merely because it suits one machine.

## 4. Backup and restore

Backup software is not installed or configured by this setup. Choose it separately; the installer
does not configure credentials, write retention policy, enable timers, or run backups. Ryoku's own
snapper/snap-pac snapshots around pacman transactions are a rollback convenience, not a backup:
they live on the same disk and do not protect against drive failure.

Before relying on a machine:

1. Choose an encrypted external or remote backup destination outside the machine's internal storage.
2. Record privately which data is included, which reproducible caches are excluded, the retention
   policy, and where passphrases and recovery material are stored.
3. Perform and record a restore drill for one representative configuration file and one workspace
   file. A completed backup job without a restore drill is not sufficient evidence.

Keep backup destination details, credentials, passphrases, and restore evidence out of this repository.

## 5. Ryoku and developer prerequisites

Complete Ryoku's normal installation first. `pacman`, `yay`, and `flatpak` ship with every Ryoku
CachyOS install; this setup does not bootstrap them. Ryoku's own
[preinstalled inventory](https://github.com/Ryoku-dev/ryoku/blob/main/docs/preinstalled.md)
already covers a broad base, developer-toolchain, and CLI/TUI set; this catalog adds only what is
not already there, plus the pinned/versioned entries this setup wants exact control over
(archive-method apps, uv/npm tools). Unlike Aurora's `ujust bbrew`/`ujust cncf` convenience
bundles, Ryoku has no equivalent single-command extra-bundle installer: anything beyond this
catalog and Ryoku's own defaults is a manual `pacman`/`yay`/RyoStore decision, not something
`./setup.sh` runs or checks for you.

Podman is installed by the normal catalog/profile flow (a plain `pacman` package, no manual group
or service setup, unlike Docker Engine). If a selected tool needs Podman's Docker-API-compatible
socket (lazydocker, oxker), enable it yourself:

```sh
systemctl --user enable --now podman.socket
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
```

This is an unprivileged per-user systemd unit, not a root-equivalent group grant; `./setup.sh`
still never runs `systemctl enable` for you, consistent with every other application.

The theme deployment installs `.zshrc` and `~/.config/vixygrey/setup.zsh`, but the setup never
runs `chsh` or otherwise changes your login shell. Ryoku is a normal mutable Arch/CachyOS system,
so `chsh` is fully available (unlike Aurora's Fedora Kinoite-family atomic desktop, which
deliberately did not ship `util-linux-user` and warned against changing the login shell on
atomic-desktop images at all). Changing the login shell here carries none of that specific risk,
but this setup still does not do it for you, since it is a machine-wide, login-affecting change
that deserves an explicit decision:

```sh
sudo usermod --shell "$(command -v zsh)" "$USER"
```

Confirm the path is listed in `/etc/shells` first (Arch's `zsh`/`fish` packages register
themselves there automatically), or `pkexec` and other PAM-aware tools will error afterward. Log
out and back in before the change takes effect. If you would rather not touch the account's login
shell, activate Zsh per terminal profile instead (for example, Kitty's `shell` setting, or your
terminal's equivalent profile command field); new windows then start Zsh interactively, which
sources `.zshrc` and activates the deployed prompt, aliases, and Zoxide/fzf hooks exactly as if it
were the login shell.

After prerequisites are present, use this sequence:

```sh
# Observe readiness. No installation or configuration writes.
./setup.sh --doctor --format json

# Review a narrow catalog selection. No installation or configuration writes.
./setup.sh --apps-only --only micro,bat,eza,git,starship

# Save a reviewed selection artifact before an explicit apply.
./setup.sh --apps-only --only omp --trust omp --format json --plan-out omp-plan.json
```

Run `--apply` only after reviewing the selection and plan. Source approval, conflict preservation,
and explicit replacement rules remain in force. `--apply` itself will prompt for your password
once per `sudo pacman`/`yay`-sourced catalog entry it installs; review the printed command before
approving each prompt.

## 6. Cross-machine dotfile sync (chezmoi)

This setup deploys the Dracula-Sakura theme and catalog applications; it does not sync general
personal configuration across your workstations. If you keep several machines aligned, do that
with `chezmoi` as a separate, manual step run **after** `./setup.sh --apply` on each machine.
`chezmoi` is a plain catalog entry (`pacman`, not in any profile), so select it explicitly:

```sh
./setup.sh --apps-only --only chezmoi --apply
chezmoi init --apply <your-dotfiles-remote>
```

Keep ownership of every path non-overlapping, so the two tools never fight over the same file:

- This repository owns everything under `dotfiles/`: `.zshrc`, `~/.config/vixygrey/setup.zsh`,
  the Ryoku-owned overlay files under `~/.config/ryoku/user_edits/` (Kitty, Fastfetch, Yazi,
  Starship), and the remaining Dracula-Sakura app configs (Bat, Micro, btop, Lazydocker, Trippy,
  and the Kiro/OMP theme files). They are generated from `theme/palette.json` and reproduced
  identically by `./setup.sh --theme-only --apply` on every workstation; that command already is
  your cross-machine sync for appearance. Do not also put these paths under chezmoi: `chezmoi
apply` overwrites to match its source, and this setup's conflict-preserving deploy would then
  treat the chezmoi-written file as a permanently preserved divergence on every later run. Also
  keep chezmoi out of `~/.config/ryoku/` entirely: `ryoku materialize`/`ryoku update` already own
  parts of that tree outside the `user_edits` overlay.
- `dotfiles/.zshrc` sources `~/.zshrc.local` when present, and this setup never creates or
  writes that file. Point chezmoi at `~/.zshrc.local` and any other personal configuration this
  repository does not manage: git identity, SSH config, personal shell functions/aliases,
  secrets, and anything outside `dotfiles/`.

On a new machine, run `./setup.sh --apply` (and `--theme-only --apply` if deploying the theme
separately) first, then `chezmoi init --apply`; chezmoi layers your synced personal
configuration on top without touching anything this repository manages.

## 7. Target-specific follow-ons

Keep target-specific validation separate from this machine-neutral runbook:

- Ryoku install, desktop, Podman, and Vulkan acceptance: issue #25.
- AMD Radeon local-model validation and model capacity evidence: issue #18.
- Additional storage and GPU presentation in Fastfetch or btop: issue #24.

Each target should supply only sanitized facts to those follow-ons: Ryoku version, architecture,
selected catalog IDs, free-space evidence, and the private decision record's conclusions. Do not
commit private machine identifiers or secrets.
