# Vixygrey Linux Setup

Personal setup for **Ryoku 1.0 (Amaterasu), CachyOS edition**, as a graphical workstation with selected useful CLI and TUI tools, Podman, and the Dracula-Sakura appearance from the existing Mac setup.

The catalog explicitly lists the selected applications and their installation sources. `soffice` is part of LibreOffice. Podman installs like any other `pacman` package, no group or service setup required. Kiro and iamlive use pinned upstream Linux payloads. OMP remains the primary AI development tool.

## Before using it

- Run `./setup.sh` as your normal user, **never prefixed with `sudo` yourself**. `--apply` shells out to `sudo pacman`/`yay` for individual package installs when a selected entry needs one, prompting for your password per normal Arch convention; the script itself always refuses to run as root (`geteuid() == 0` is rejected outright), so there is no way to make the whole run privileged.
- Complete Ryoku's normal installation first (the CachyOS edition, with Hyprland, niri, or Wayfire). Python 3.11+, `pacman`, and `yay` ship with every Ryoku CachyOS install; `flatpak` also ships by default. This repository does not bootstrap any of them with downloaded shell scripts.
- The catalog includes architecture-specific x86_64 and aarch64 vendor artifacts for pinned archive entries. Preview uses the current machine's architecture. Ryoku 1.0 itself ships `x86_64` only; `--apply` is refused on any other architecture.
- The standard `~/.config` and `~/.local/share` locations are supported. A genuinely different XDG location is blocked rather than written incorrectly. Config paths Ryoku's own package ships a base file for (Kitty, Fastfetch, Yazi, Starship) deploy under `~/.config/ryoku/user_edits/...`, the documented override overlay `ryoku materialize`/`ryoku update` never clobbers or prunes; everything else deploys to its literal home-relative path.
- Review the catalog and the plan before applying. The setup is not an OS installer or a replacement for system backups.

Before the first apply on any machine, complete the [machine commissioning runbook](docs/machine-commissioning.md). It keeps storage, encryption, backup, power, and optional capability decisions per-machine without changing installer defaults.

Ryoku/CachyOS's software model is `pacman` and AUR (via `yay`) for system packages, with Flatpak available as a secondary sandboxed-app channel it ships by default. This setup never changes your login shell, never alters groups, and never runs `systemctl enable` itself; the only privileged commands it ever issues are the single reviewed `sudo pacman -S --needed <package>` or `yay -S --needed <package>` call for each selected catalog entry that needs one.

### Podman

Podman is a daemonless, rootless-by-default container engine; the `podman` catalog entry installs
it as a normal `pacman -S --needed podman` package, since rootless `podman run`/`podman build`
need no group membership, systemd service, or privilege escalation the way Docker Engine did.
Rootless mode relies on per-user `/etc/subuid`/`/etc/subgid` ranges, which modern
`useradd`/`systemd-sysusers` allocate automatically for normal accounts; nothing else to set up.

`podman-docker` and `podman-compose` are separate opt-in catalog entries: the former emulates the
`docker`/`docker-compose` CLI as thin wrappers over Podman (conflicts with the real `docker`
package, which is not in this catalog); the latter runs `docker-compose.yml` files against Podman.
Neither exposes the Docker Engine HTTP API socket.

Some third-party TUIs (lazydocker, oxker) speak that HTTP API directly rather than shelling out to
a `docker`-named binary, so they need Podman's own compatible socket instead:

```sh
systemctl --user enable --now podman.socket
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
```

This is an unprivileged per-user systemd unit, not a root-equivalent group grant the way Docker's
was, but this setup still never runs `systemctl enable` for you, consistent with every other
application in the catalog; enable it yourself if you select one of those tools.

## Preview and install

```sh
# Application IDs, sources, methods, and notes. No installation.
./setup.sh --list

# --list honors --profile/--only/--skip for a narrower view, and --format json for scripting.
./setup.sh --list --profile base
./setup.sh --list --only kiro,posting --format json

# Preview the entire catalog and theme. No installation or configuration writes.
./setup.sh
```

### Profiles

Profiles are checked-in canonical catalog IDs: `base`, `terminal`, `developer`, `cloud`,
`security`, `desktop`, and `ai`. `--list` shows every profile containing each application.
Use the staged order `base`, then `terminal` or `developer`, then only the domain profile you
need. Profiles only select applications; third-party sources (including every AUR entry) still require per-ID `--trust`.

```sh
# Start with an explicit, reviewable profile. Profiles select apps but never trust sources.
./setup.sh --apps-only --profile base --format json
./setup.sh --apps-only --profile base,terminal --skip btop

# Apply only after reviewing the plan and approving its reported third-party IDs.
./setup.sh --apps-only --only kiro,posting --trust kiro,posting --apply

# Individual IDs can refine a profile; --skip always wins.
./setup.sh --apps-only --profile developer --only git --skip gh
```

The `developer` profile includes Posting. `desktop` includes the pinned Dracula-Sakura
wallpaper (`dracula-sakura-wallpaper`), applied by `--desktop` (see
[Theme and existing machines](#theme-and-existing-machines)).
To preview Kiro and Posting without deploying the rest of the theme:

```sh
./setup.sh --apps-only --only kiro,posting --trust kiro,posting --format json
```

The `developer` profile also includes gitlogue, Lazygit, oxker, grex, Kondo, Worktrunk, Rust, xh,
mkcert, pnpm, d2, and the existing Mike Farah yq entry. `terminal` adds VisiData, croc, atuin,
glow, Zellij, procs, duf, Harlequin, aerc, ncdu, lnav, jless, and bandwhich; `cloud` adds
dnsglobe, aws-vault, kubectl, Helm, k9s, OpenTofu, and stu; `ai` adds llmfit; `desktop` adds
Syncthing, Thunderbird, and Satty alongside Obsidian.
All use Arch's official `extra` repo or an actively-maintained AUR package (flagged `third_party`
where AUR-sourced), without a custom
repository. Both catalog files participate in the default full selection;
`extended` does not mean opt-in. Preview this group without deploying configuration:

```sh
./setup.sh --apps-only \
  --only gitlogue,visidata,dnsglobe,oxker,llmfit,croc,grex,kondo,worktrunk,rust,xh,mkcert,pnpm,yq,d2,atuin,glow,aws-vault \
  --format json
```

`vd` and `wt` are selection aliases for VisiData and Worktrunk. `gcalcli` is a standalone entry
in no profile; select it explicitly with `--only gcalcli --trust gcalcli`. Catalog and profile
edits invalidate saved plans; regenerate them before applying.

The `base` profile includes zoxide, fzf, and Neovim; `developer` includes delta (Arch package
`git-delta`). Bat, ripgrep, and fd remain in `base`, and btop remains in
`terminal`. These tools install from Arch's official `extra` repo, with no custom repository or
per-ID source approval. Several of them (bat, eza, fd, fzf, ripgrep, zoxide, starship, fastfetch,
btop, yazi, neovim) already ship by default on a fresh Ryoku install; selecting them here is
still explicit and reviewable, and `pacman -S --needed` is a harmless no-op when a package is
already present.

```sh
./setup.sh --apps-only --only zoxide,fzf,bat,btop,ripgrep,fd,delta,neovim --format json
```

A preview can run on this Mac; `--apply` requires Ryoku (CachyOS edition) and a non-root user. Read-only package
queries may use package managers' own caches or locks.

### Status and readiness

`--status` inspects selected applications and managed files without writing to your home. It reports
installed, missing, blocked, stale-receipt, command-conflict, cache-pending, preserved, and protected
states. Font status separates current payload files, retained retired fonts, and cache readiness.
Use JSON when another tool needs a stable record:

```sh
./setup.sh --status --apps-only --only omp --trust omp --format json
./setup.sh --doctor --format json
```

`yaml-py` status verifies the helper ownership marker, executable wrapper, private interpreter,
and pinned PyYAML version using the same check as installation planning. An intact helper reports
`installed` without renewed source approval; missing or invalid helpers still require approval
and uv before repair.

`--doctor` reports the current Ryoku/CachyOS, architecture, pacman, yay, Flatpak, theme
(Ryogami availability), Vulkan, and root/home free-space readiness. It never installs, repairs,
downloads, locks, or creates state. Both commands are observation-only and cannot be combined
with `--apply`, replacement, desktop activation, or plan-writing options.

### Reviewable JSON plans

Keep the default text preview for interactive use. To attach a deterministic review artifact, request JSON explicitly:

```sh
./setup.sh --apps-only --only omp --trust omp --format json --plan-out omp-plan.json
./setup.sh --apply-plan omp-plan.json
```

`--apply-plan` is an application mode. It accepts no additional selection or approval flags, checks the artifact schema, catalog digest, and canonical selection intent, then re-plans under the existing setup lock before mutation. The artifact records actions and preflight facts for review, but is never executed directly. A catalog edit invalidates it; mutable package and file state are checked again during the locked re-plan. Plan files are created only at an explicitly requested new path and can include local conflict metadata.

Profile selections are saved in the plan too. For example, create a base-profile plan with
`./setup.sh --apps-only --profile base --format json --plan-out base-plan.json`, then apply it
with `./setup.sh --apply-plan base-plan.json`. Do not repeat profile or approval flags when applying.

Regenerate saved plans after a schema change. The catalog no longer has an optional selection
tier; use profiles, `--only`, and `--skip` to choose applications.

Third-party AUR packages, vendor artifacts, and catalog-marked Flatpaks need explicit source approval. Approval is per application and per invocation:

```sh
./setup.sh --apps-only --only omp,kiro --trust omp,kiro
./setup.sh --apps-only --only omp,kiro --trust omp,kiro --apply
```

For the full catalog, omit `--only` and approve each reported third-party ID with `--trust`. Flags accept comma-separated IDs and can be repeated. There is no implicit trust-all or ignore-errors mode. **Any blocker prevents installation from starting.** Use `--skip` only for applications you intentionally exclude:

```sh
./setup.sh --skip podman
```

### Theme and existing machines

```sh
# Preview or deploy appearance files without installing packages.
./setup.sh --theme-only
./setup.sh --theme-only --apply

# Also set the Dracula-Sakura wallpaper via ryogami (requires dracula-sakura-wallpaper selected and trusted).
./setup.sh --apps-only --only dracula-sakura-wallpaper --trust dracula-sakura-wallpaper --apply
./setup.sh --theme-only --desktop --apply
```

Appearance files use the local Mac palette, with Linux-specific adaptations.

- Kitty, Fastfetch, Yazi, Starship, and Neovim deploy under Ryoku's `~/.config/ryoku/user_edits/...`
  override overlay, since Ryoku's own package ships a base config at those paths and
  `ryoku materialize`/`ryoku update` would otherwise clobber a direct write on the next update.
  **Ryoku's `matugen` pipeline re-renders Kitty's and Starship's colors from the active wallpaper
  on every theme/wallpaper change**, which can recolor them away from the exact Dracula-Sakura
  values even after this setup deploys them; select **Fixed** theme mode for those surfaces in
  Ryoku Settings if you want the shipped files to stick.
- `--desktop` sets the pinned `dracula-sakura-wallpaper` catalog entry's image via
  `ryogami wallpaper set --screen '*'`, so matugen derives the live desktop palette from it. This
  is an approximation of `theme/palette.json`, not an exact static colorscheme: Ryoku has no
  shipped API for dropping in an arbitrary fixed palette the way KDE's `plasma-apply-colorscheme`
  did on Aurora. `--desktop` requires the wallpaper entry to already be selected, trusted, and
  installed, and requires `ryogami` to be available (an active Ryoku desktop session).
- Neovim: Ryoku ships its own LazyVim-based `~/.config/nvim` by default, so this setup does not
  replace it with a separate LazyVim starter clone. It layers three files through the
  `user_edits` overlay: `lua/plugins/omp.lua` (the `l3aro/omp.nvim` plugin spec, `<leader>om` to
  ask omp from the buffer or a visual selection; requires Neovim 0.11+), `lua/plugins/obsidian.lua`
  (`obsidian-nvim/obsidian.nvim`, for editing your Obsidian vault from Neovim; ships with no
  vault path configured, since this setup never creates or locates one — add your vault to its
  `workspaces` table yourself, or open Neovim from inside it), and `lazyvim.json`
  declaring the `lang.rust`, `lang.python`, `lang.typescript`, `lang.tailwind`, `lang.docker`, and
  `lang.markdown` LazyVim extras, the same mechanism `:LazyExtras` itself writes to. Run
  `:checkhealth omp_nvim` after the first launch to confirm the bridge installed correctly.
- Btop, Bat, Micro, Lazydocker, and Trippy are not Ryoku-owned paths, so they deploy to their
  literal `~/.config/<app>/...` location unchanged and are never touched by `ryoku update`.
- Kiro gets a full Dracula-Sakura color theme extension (`~/.kiro/extensions/vixygrey.dracula-sakura-1.0.0`: a manifest plus a 140-color, semantic-highlighting-aware theme), activated via `workbench.colorTheme` in its settings; the existing inline `workbench.colorCustomizations`/`editor.tokenColorCustomizations` overrides stay in place alongside it. OMP gets its own theme file at `~/.omp/agent/themes/dracula-sakura.json`, authored against OMP's own schema. Trippy also has a managed palette. Apps without a custom palette inherit terminal colors where supported; this does not claim to recolor every Flatpak or web interface.

Missing files are installed; identical files are left unchanged. Different existing files are **preserved**, including on repeat runs. Symlink destinations and symlink ancestors are protected, even with replacement consent. No configuration merge is attempted.

Inspect an exact managed configuration path before deciding whether to replace it:

```sh
./setup.sh --theme-only --diff .config/ryoku/user_edits/kitty/kitty.conf
./setup.sh --theme-only --diff .zshrc --diff .config/ryoku/user_edits/starship.toml
```

`--diff` is a dedicated read-only comparison mode. It supports selected managed dotfiles and
generated launchers, not arbitrary home files, receipts, or downloaded application payloads.
It does not query package managers, download, lock, migrate receipts, back up, or write files.
Repeated paths are shown once. A successful comparison, including ordinary differences, exits
0; invalid or unsuitable requests exit 2 without printing a partial diff.

Only printable UTF-8 text and newline characters are eligible. Binary data, invalid UTF-8,
other control characters (including tabs and carriage returns), symlinks, and nonstandard XDG
locations are refused. Each current or desired file is limited to 64 KiB, and the complete output
is limited to 256 KiB. Every requested path is validated before content is printed.

**Explicit diff output can contain personal secrets.** Review it before sharing or redirecting
it; there is no automatic redaction. Normal preview, status, JSON, and saved-plan artifacts stay
content-free. Diff mode cannot be combined with apply, saved-plan application/output, JSON,
status/doctor reports, listing/catalog validation, desktop activation, or replacement consent.
A comparison never approves replacement; use a separate explicit `--replace` invocation below.

To replace one particular regular file after reviewing it, use its exact path relative to your home:

```sh
./setup.sh --theme-only --replace .config/ryoku/user_edits/kitty/kitty.conf
./setup.sh --theme-only --replace .config/ryoku/user_edits/kitty/kitty.conf --apply
```

Original bytes are backed up privately under:

```text
~/.local/state/vixygrey-setup/backups/<unique-id>/<original-home-relative-path>
```

The command prints the exact backup path. Restore a file by reviewing that backup and copying it to its original location. Backups can contain personal configuration; keep this state directory private and outside this repository.

### Shell activation

The managed `.zshrc` is installed only if missing or explicitly approved for replacement. It sources `~/.config/vixygrey/setup.zsh` and, if present, your `~/.zshrc.local`. Ryoku's default account shell is Fish or Zsh depending on what you chose during install; if Ryoku's own skeleton already wrote a `~/.zshrc`, it is treated like any other existing file and preserved unless you explicitly `--replace` it.

If preserving an existing `.zshrc`, add this line yourself after reviewing the fragment:

```zsh
source "$HOME/.config/vixygrey/setup.zsh"
```

Start Zsh to use it. The setup does not call `chsh`. Shell integration includes stable user tool paths, the themed prompt, direnv, mise, the Zsh plugins, and Granted's interactive `assume` alias. Interactive hooks require an actual terminal. Existing direnv/mise trust checks remain in force; nothing authorizes project scripts automatically.

Separately, `./setup.sh --completion {bash,zsh}` prints a completion script for `setup.sh`'s own
flags, catalog IDs, and profile names, read live from the current catalog. It is a plain stdout
print with no home writes; wire it into your shell yourself, for example
`source <(./setup.sh --completion zsh)` or `eval "$(./setup.sh --completion bash)"`. It cannot be
combined with `--diff`, `--validate-catalog`, `--apply-plan`, `--status`, or `--doctor`.

Zoxide and fzf hooks load only in interactive terminal sessions without an
`AI_AGENT` marker, when their executables are available. Zoxide adds `z` for
directory jumps and `zi` for selection with fzf; native `cd` is unchanged.
Fzf adds fuzzy completion, Ctrl+R history search, Ctrl+T file selection, and
Alt+C directory selection. Existing `FZF_*` settings are respected.
Skipping fzf does not disable ordinary zoxide directory jumps.

`--apps-only` installs binaries, not shell configuration. Preview deployment with
`./setup.sh --theme-only`. On existing machines, review
`./setup.sh --theme-only --diff .config/vixygrey/setup.zsh` before using the
existing explicit `--replace .config/vixygrey/setup.zsh` mechanism with `--apply`.
Different existing files remain preserved unless replacement is explicitly approved.

Delta is installed without changing Git configuration or a global pager.
To opt in, add these settings to your own Git configuration after installation:

```gitconfig
[core]
    pager = delta
[interactive]
    diffFilter = delta --color-only
```

Command aliases are enabled only in interactive Zsh shells with no `AI_AGENT` marker, and only
when the target executable is available:

| Command | Runs                           |
| ------- | ------------------------------ |
| `cat`   | `bat --paging=never`           |
| `ls`    | `eza --icons`                  |
| `ll`    | `eza -la --icons --git`        |
| `la`    | `eza -a --icons`               |
| `lt`    | `eza --tree --icons --level=3` |
| `top`   | `btop`                         |
| `dl`    | `aria2c`                       |
| `y`     | `yazi`                         |
| `ping`  | `gping`                        |
| `dig`   | `doggo`                        |

`ps`, `df`, `find`, and `grep` are not replaced by aliases. Use `rg`, `fd`, `ouch`, `rsync`, and
`rclone` directly; `procs` and `duf` are separate catalog entries (`terminal` profile) rather than
aliases over `ps`/`df`. These command aliases do not affect scripts or
agent shells, and removing catalog entries does not uninstall tools already on a machine.

## Package behavior and important constraints

The complete source of truth is [`catalog/core.json`](catalog/core.json),
[`catalog/extended.json`](catalog/extended.json), and [`profiles.json`](profiles.json).
`--list` shows every requested application and its profile membership. Sources were resolved using
the Mac Brewfile, installed configuration, existing Mac setup implementation, Arch's official package
search, the AUR, and upstream Linux documentation.

| Route           | Behavior                                                                                                                                                                                                                               |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| pacman          | Official Arch `core`/`extra`/`multilib` or CachyOS repo packages, via `sudo pacman -S --needed <package>`. Existing packages are skipped (`--needed`). No automatic `-Syu`, cleanup, or orphan removal.                                |
| aur             | AUR packages via `yay -S --needed <package>`, run as your own user (yay escalates to `sudo pacman -U` internally for the final install step only). Always flagged `third_party`; community PKGBUILDs are not maintainer-reviewed.      |
| Flatpak         | Missing apps install per user from Flathub. An existing system installation is left in place. A conflicting user `flathub` URL blocks installation. `soffice`/LibreOffice receives a conflict-preserving CLI wrapper.                  |
| Vendor archives | Versioned HTTPS downloads with catalog SHA256 checks. Payloads stay in versioned user directories, with executable wrappers and GUI launchers. No archive install hooks, device nodes, escaping paths, escaping links, or setuid bits. |
| uv / npm        | Exact top-level package versions in user-owned locations. Cheznav requests Python 3.14 through uv. Python tools may download a compatible managed interpreter.                                                                         |
| `yaml-py`       | A private uv environment containing PyYAML, exposed as a Python interpreter command, matching the Mac helper rather than substituting a different YAML CLI.                                                                            |

### Special applications

- **llama.cpp:** Arch's official `extra`-repo build is used (natively compiled against Arch's current `openssl`, no Ubuntu-binary OpenSSL 3/4 mismatch to work around). `runtime_libs` installs the optional `ggml-vulkan` backend package alongside it. Installation must still detect a Vulkan device with `llama-cli --list-devices`; a working host Vulkan driver is required, and this does not substitute a CPU-only build. No model downloads or server services are configured, though the package itself ships `llama-server.service` systemd units (system and user) you can enable yourself.
- **Kiro:** the official portable Linux bundle is installed user-locally. It needs the host's normal Electron desktop libraries and unprivileged user namespaces. The setup never adds `--no-sandbox`, sets a root-owned sandbox helper, or disables OS security policy.
- **AWS Session Manager Plugin:** the official versioned Debian payload is unpacked into a private application directory. No Debian maintainer scripts run and nothing is written to host `/usr` or `/etc`.
- **iamlive:** no official Arch or AUR package exists, so this pins the upstream project's own GitHub release Linux tarballs directly, the same pattern used for Kiro.
- **DBeaver Community:** the desktop profile selects the publisher-listed Flathub package, with explicit `--trust dbeaver` approval. Configure a DuckDB connection and download its JDBC driver inside DBeaver. Dataset access may require Flatpak permissions, especially on additional drives. Harlequin (below) covers the same ground from the terminal instead.
- **Obsidian:** Arch's official `extra` repo packages Obsidian directly (not an AppImage wrapper), so it installs via `pacman` with explicit `--trust obsidian` approval, since it is a proprietary vendor application. Sync, plugins, and vault location remain yours to configure; no vault data is imported. **Excalidraw** (and every other Obsidian community plugin) cannot be installed by this setup: Obsidian plugins are fetched from inside the app into a specific vault's `.obsidian/plugins/` directory, and this setup never creates or locates a vault. Once you have one, install Excalidraw from Settings → Community plugins → Browse inside Obsidian itself.
- **Removed applications:** Todoist, Discord, Google Chrome, Zed, Bruno, and draw.io are no longer in the catalog or profiles. Chrome is redundant with Chromium, which Ryoku can already install as its selected default browser during setup. Bruno was replaced by Posting; draw.io was replaced by the Excalidraw Obsidian plugin (see the Obsidian entry above). Existing installations and personal data are untouched. Regenerate saved plans after this catalog change; the removed IDs are no longer valid selection or approval arguments.
- **Retired Notion launcher:** Notion is no longer in the catalog or profiles. Existing files are not automatically removed. If previously installed, review `~/.local/share/applications/vixygrey-notion.desktop` and remove that menu entry manually if no longer wanted. Browser data and accounts are untouched. Regenerate saved plans after this catalog change.
- **Posting:** a terminal HTTP client installed as a uv tool; no Electron sandbox, desktop portal, or GUI launcher is needed. Collections are plain YAML files you manage yourself; none are imported.
- **Granted / AWS / Bitwarden / OMP:** credentials, accounts, tokens, profiles, and login flows remain yours to configure. No credentials are imported from the Mac.
- **OMP theme activation:** the theme deploys `~/.omp/agent/themes/dracula-sakura.json`, but does not edit `~/.omp/agent/config.yml` to activate it, since that file also carries model routing and provider settings this setup never touches (same boundary as the credentials note above). Add `theme: {dark: dracula-sakura, light: dracula-sakura}` to that file yourself to turn it on.
- **Backups:** backup software and policy are outside this setup. Choose destinations, encryption, credentials, retention, and scheduling separately, then validate restoration using the machine commissioning runbook.
- **Network diagnostics / Caligula:** no uinput permissions, network capabilities, or disk writes are enabled by setup. Privileged runtime actions remain explicit user decisions.
- **gitlogue:** replays local Git history and requires Git plus a repository with commits. Setup does not set its theme or start watch mode.
- **VisiData:** Arch's official package manages the Python environment and supplies `vd` and `visidata`. Optional formats such as XLSX and Parquet need dependencies in that environment; setup does not add them or promise every upstream format.
- **dnsglobe:** queries public DNS resolvers, including direct DNS on port 53, which restricted networks may block. Displayed resolver regions are not independent probes physically running in those regions. Setup does not change firewall rules or configure EDNS Client Subnet. Sourced from AUR; approve it with `--trust dnsglobe`.
- **oxker:** speaks the Docker Engine HTTP API like lazydocker, so it needs Podman's compatible socket (see Podman above) to manage Podman containers; setup does not enable that socket or change groups. Lazydocker remains available. Sourced from AUR; approve it with `--trust oxker`.
- **llmfit:** recommends models from detected hardware; GPU detection depends on host drivers and probes. Recommendations do not prove Vulkan llama.cpp compatibility. Setup does not download models, configure providers, or start services.
- **croc:** encrypted transfers can use public relays. Protect transfer codes and use trusted endpoints. Setup does not configure a relay, open firewall ports, or start transfers.
- **grex:** generates candidate regular expressions from examples. Review unintended matches and compatibility with the intended regex engine.
- **Kondo:** installs only the `kondo` CLI. Cleanup deletes dependencies and build artifacts; upstream describes it as essentially `rm -rf` with a prompt. Back up projects and review targets. Setup never runs cleanup or installs `kondo-ui`.
- **Worktrunk:** installs `wt` for Git worktree management. Directory-changing integration is an optional user step, `wt config shell install`, which modifies shell configuration and is never run by setup. Project hooks, agent plugins, LLM providers, and existing worktrees are not configured or changed.
- **Rust:** Arch's official `rust` package installs `rustc`, `cargo`, and the bundled `rustfmt`/`clippy` tools as a single stable toolchain, to `/usr`. This is not `rustup`; it does not manage multiple toolchains, channels, or cross-compilation targets. Link it under `rustup` yourself with `rustup toolchain link system /usr` if you also install `rustup`.
- **mkcert:** installs the CLI only. Running `mkcert -install` changes your local trust store and is never done automatically by this setup.
- **pnpm / corepack:** Arch's official `pnpm` package has no declared conflict with Node's bundled `corepack`. If you already manage pnpm through `corepack`, skip this entry rather than installing a second copy.
- **yq:** the existing entry is Mike Farah's Go implementation, packaged on Arch as `go-yq` (Arch's own `yq` package is the unrelated Python kislyuk/yq). Installing both registers conflicting `/usr/bin/yq` binaries; pacman will refuse the second one rather than silently overwrite it. The separate `yaml-py` interpreter helper remains available.
- **Neovim / LazyVim / omp.nvim:** see [Theme and existing machines](#theme-and-existing-machines) for how the `omp.nvim` plugin and LazyVim extras are deployed through the `user_edits` overlay rather than a separate starter clone.
- **atuin:** shell history sync and search. `atuin register`/`atuin login` to sync across machines is a manual, credential-bearing step; this setup only installs the binary.
- **Syncthing:** peer-to-peer file sync. Pairing devices (including the Android companion app), folder shares, and enabling the `syncthing.service` user unit are manual steps this setup never performs.
- **Thunderbird:** mail and calendar client. Accounts and sync are yours to configure; none are imported.
- **Satty:** a Wayland screenshot annotation tool meant to be piped from `grim`/`slurp` (`grim -g "$(slurp)" - | satty --filename -`). No capture keybinding is configured; wire one into your compositor's own config if wanted.
- **d2:** no official Arch package; AUR `d2-bin` is a maintained prebuilt binary. Approve it with `--trust d2`.
- **gcalcli:** no official Arch package; AUR `gcalcli` is a maintained package. The first run needs your own Google OAuth client setup; this setup does not configure Google credentials. Approve it with `--trust gcalcli`.
- **aws-vault:** stores AWS credentials in the OS keystore rather than plaintext files; profiles and credential setup remain yours to configure.
- **glow:** renders Markdown in the terminal; read-only, no configuration deployed.
- **Lazygit / Zellij / procs / duf:** standard Arch `extra` CLI/TUI tools with no configuration deployed and no accounts to set up.
- **Harlequin:** a terminal SQL IDE; ships with DuckDB and SQLite adapters, other databases need their own adapter package installed separately into the same uv environment (`uv tool install 'harlequin[postgres]'` etc.), which this setup does not do for you. Covers the same use case as DBeaver, from the terminal instead of a GUI.
- **kubectl / Helm / k9s:** none of the three configure a kubeconfig, cluster context, or cloud credentials; they use whatever is already on the system.
- **OpenTofu:** an open-source Terraform fork; state backends, providers, and cloud credentials remain yours to configure. This setup does not run `init`/`plan`/`apply` for you.
- **aerc:** a terminal email client; it does not import Thunderbird's accounts, and has no calendar support (keep Thunderbird for that). Accounts and PGP keys are yours to configure.
- **stu:** browses S3 using whatever AWS credentials/profile are already active in your shell; does not configure credentials itself. Sourced from AUR; approve it with `--trust stu`.
- **ncdu / lnav / jless / bandwhich:** read-only inspection tools (disk usage, log files, JSON, network bandwidth); none deploy configuration or need source approval.

### Repeated runs, changes, and failure

Package-manager state is inspected rather than trusting a generic "done" marker. Archive receipts also check deployed file hashes and executable permissions. Existing pacman, AUR, and Flatpak installations are not upgraded automatically. Registry installs use their pinned versions; if a manager refuses a conflicting existing version, the setup stops rather than forcing replacement.

Archive wrapper changes, including version changes, require explicit `--replace .local/bin/<command>` approval. Existing modified payload files remain protected. Older version directories are not pruned automatically. Receipts live under `~/.local/state/vixygrey-setup/receipts/`.

Only one setup process can apply at a time. Commands stop at the first failure. Successfully completed package installs remain; this is **not a transaction across package managers**, and rollback does not uninstall dependencies. Rerun after resolving the reported failure to reconcile state.

Exit codes:

| Code | Meaning                                                                        |
| ---- | ------------------------------------------------------------------------------ |
| 0    | Plan/apply completed without blockers or preserved conflicts                   |
| 2    | Preflight blocked, invalid input, unsupported platform, or an operation failed |
| 3    | Existing configuration or launcher conflicts were intentionally preserved      |
| 130  | Interrupted; completed changes remain                                          |

### Receipt identity and migration

Archive and font receipts use deployment identity version 1 (`spec_version: 1`). Their `spec`
digest covers the application ID, method, version, selected artifact URL and checksum, and the
route's deployment parameters. Archive identity also covers the selected architecture, effective
extraction format, raw destination filename when applicable, and effective command mapping.
Defaults and relative paths are normalized to match deployment semantics. Fonts use the shared
ZIP layout without an architecture-specific identity.

Notes, display names, aliases, human-facing source documentation, approval classification, and
inactive-architecture artifact edits do not invalidate a versioned receipt. Deployed-file hashes
and executable permissions are still checked. Required downloads still need the same source
approval; receipt identity does not grant new trust or replacement permission. GUI launchers
remain subject to their independent planning and conflict safeguards.

Legacy receipts hash the whole catalog entry. If that hash still matches the current entry and
the artifact checksum and deployed files are intact, preview reports a `receipt-migrate` action.
Status and preview never migrate receipts. Explicit apply revalidates under the setup lock and
replaces only the receipt, with a private backup and no payload download or rewrite. Font retired
provenance and pending cache work are preserved; pending cache work follows migration as a
separate cache-only action.

If the legacy hash already mismatches, the receipt stays stale and may need one final approved
refresh. Its opaque hash cannot prove that only documentation changed. The installer does not
accept it solely because the old artifact and recorded files still match, since a new command
mapping could require a wrapper that is not present. Unsupported identity versions and malformed
or protected receipts fail closed.

Saved review plans still use the strict whole-catalog digest. A catalog edit can invalidate a
saved plan even when it no longer invalidates an intact application installation.

### Font upgrades and recovery

No catalog entry currently uses the `font` method. The mechanism below remains live
infrastructure (exercised by the test suite) for any future font catalog addition — for example,
if a Nerd Font variant Ryoku does not already ship becomes a selected dependency.

Fonts deploy to `~/.local/share/fonts/JetBrainsMonoNerd` (a fixed directory, not per-entry);
existing installations would not need a directory migration. Source approval requires
`--trust <id>` when downloading a release, same as any other third-party entry.

Offline preview inspects recorded current and retired font paths, reporting missing, modified,
or protected files without downloads or home writes. It cannot produce a complete target-file
diff because the catalog pins the ZIP checksum, not its member inventory. JSON install actions
include `font_readiness` with `payload_preflight_required: true`.

During apply, the complete checksum-verified font archive is validated and staged in temporary
files. Every destination and the receipt are checked before font deployment. A known conflict
stops deployment without changing installed fonts or the receipt, even when some other paths
have replacement approval. Review the reported paths and approve each intended replacement
with `--replace .local/share/fonts/JetBrainsMonoNerd/<filename>`. Original bytes are backed up
using the same private backup mechanism as other managed files. Receipt ownership never grants
permission to overwrite fonts, and symlinks remain protected even with explicit consent.

Fonts removed from a new upstream release are **retained**, not deleted. Their original recorded
hashes remain in a separate retired inventory across upgrades. Text status labels them
`RETAINED FONT`; JSON status exposes `retired_fonts`. Editing or removing a retired font does not
invalidate the current release. Review any variants you no longer want and remove them manually;
retained variants remain available to the font system and may affect selection.

After deployment, the receipt records pending cache work before running `fc-cache -f` on the
font directory. A failed or unavailable `fc-cache` leaves the payload intact and reports
`cache-pending`. Once the tool is available or its error resolved, rerun the same selection with
`--apply`: an intact payload gets a cache-only retry, without downloading or redeploying fonts.
Successful cache work clears pending state. Legacy receipts without cache metadata do not force
a rebuild. This preflight is not a transaction: I/O failures or external filesystem changes after
preflight can still interrupt deployment, and the installer stops rather than bypassing safeguards.

## Security model

Review this repository and its catalog before execution. Arch's official repos, the CachyOS repo, and the Flathub remote are baseline package sources; AUR entries and catalog-marked additional sources require explicit approval. Package-manager builds (including AUR PKGBUILDs, which run arbitrary build-time code as your user before the final `sudo pacman -U`), package install scripts, application binaries, and shell initialization hooks still execute code as your user. **Approval is not sandboxing or a security audit.**

TLS and hashes protect downloads against unexpected changes. Hashes are publisher-provided where available, or computed from the versioned official HTTPS artifact where noted. They do not independently prove publisher identity or make a compromised upstream safe. A changed artifact fails closed; refreshing a pin requires reviewing the source and replacing its checksum deliberately.

Top-level registry versions and vendor assets are pinned, but this is not a fully reproducible supply-chain lock: pacman/AUR/Flatpak use their current repository state, and registry transitive dependencies can change. OS updates and application vulnerability maintenance remain necessary.

### Refreshing catalog pins

Catalog and profile changes are deliberately manual. Do not use Dependabot or another automated
updater for `catalog/*.json`, `profiles.json`, vendor artifact URLs, SHA-256 values, Flatpak IDs,
pacman/AUR package names, or source-approval classifications.

For every catalog refresh:

1. Start from the authoritative upstream release page, Arch's official package search, or the AUR.
2. Review the version, URL, architecture artifacts, commands, install method, and source
   classification before changing the catalog entry.
3. Download each target artifact from its official URL and calculate its SHA-256 locally. Compare
   that value with an upstream publisher checksum when one is available.
4. Update the version, URL, and checksum together in one reviewable pull request. A publisher
   checksum is evidence of artifact consistency, not proof of publisher identity.
5. Run `./setup.sh --validate-catalog` and `./scripts/verify`, then preview the changed selection
   before any explicit `--apply`.

Do not put cloud credentials, SSH keys, Bitwarden exports, shell history, browser profiles, rclone remotes, backup secrets, or generated state in this repository.

## Verification

```sh
mise install  # or otherwise provide Node 24.18.1, uv 0.13.1, and Go 1.26+
npm ci
uv sync --locked --group dev
go install mvdan.cc/sh/v3/cmd/shfmt@v3.14.1
export PATH="$(go env GOPATH)/bin:$PATH"
./scripts/verify
```

This canonical check requires Node 24.18.1, uv 0.13.1, Go 1.26+, Python 3.11+, Zsh, and ShellCheck. `mise.toml` pins the Node, uv, and Go versions; `mise install` provisions them without hunting for the right combination. Run `npm ci` and `uv sync --locked --group dev` after cloning or changing their lockfiles. Node, Prettier, uv, Ruff, Go, and shfmt are development-only tooling; the installer runtime remains Python standard library. The check validates Prettier, Ruff, and explicitly-dialected Bash/Zsh shfmt formatting; runs the safety suite; validates the catalog with `--list`; checks managed shell files; and previews a trusted archive selection plus theme deployment in empty temporary homes. It never calls `--apply` or installs missing tools. `scripts/format-python` and `scripts/format-shell` share the same formatting contract in `--write` mode.

The same gate also runs Ruff correctness linting with the explicit `E9` and `F` rule families.
Linting does not enable auto-fixes, import sorting, or broader modernization rules. Its scope is
the installer modules, the development palette validator, and tests, matching Python formatting.

`python3 -B scripts/validate-palette.py` checks the explicit managed theme inventory against
`theme/palette.json`, including required roles, Starship's palette, ANSI assignments, and
theme-name references. `--root PATH` supports isolated fixture copies for validation. Application
files remain explicit, with no generated colors or runtime palette dependency. Existing
app-specific line highlights and active line-number choices are preserved; pure white is allowed
only in Kitty and Kiro's ANSI bright-white slots. The shell's custom Bat default is checked, but
upstream Vivid/LS_COLORS behavior is outside this palette contract. These static checks do not
prove application rendering, contrast, or whether Ryoku's matugen pipeline has since recolored a
managed surface at runtime.

The safety suite covers preservation, backups, symlink/traversal rejection, executable modes, archive links and setuid stripping, font filtering and staged upgrades, exact-path font replacement, retirement provenance, cache-only recovery, Debian-container boundaries, invalid selections, source approval, and canonical home aliases. Font deployment tests use isolated homes with local ZIP fixtures and recording cache executables; they do not validate Linux fontconfig or actual rendering.

During development on the reference Mac, isolated smoke runs exercised actual theme deployment and repeat planning; Bat, Starship, lnav, Fastfetch, interactive Zsh, and the btop TUI; PyYAML installation and parsing; and checksum-verified AWS, Eilmeldung, Kitty, OMP, Nerd Font, Kiro, and iamlive payload installation without executing the Linux binaries. A live local HTTPS fixture also verified executable deployment under a home path containing spaces and rejection of a changed download before any home writes. These historical checks do not establish current catalog support for removed applications.

**The full application install, Linux binary execution, Vulkan device detection, `sudo pacman`/`yay` privilege escalation, and Ryogami wallpaper activation have not been run on a Ryoku target.** A local Podman install was unavailable. Validate the plan on the intended machine before approving an apply run, and validate the desktop there before treating its appearance as verified.

## License

This repository is licensed under the [MIT License](LICENSE). Third-party applications and
dependencies installed or used by this setup retain their own licenses.
