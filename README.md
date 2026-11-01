# Vixygrey Linux Setup

Personal setup for **CachyOS** as a KDE Plasma workstation with selected CLI and TUI tools, local Docker Engine, and the Dracula-Sakura appearance from the existing Mac setup.

The catalog explicitly lists selected applications and installation sources. `soffice` is part of LibreOffice. Docker Engine is the approved replacement for Docker Desktop. Obsidian, Discord, Zed, Kitty, and DBeaver use official native packages; Todoist uses per-user Flathub and Bruno retains a pinned upstream Linux payload. OMP remains the primary AI development tool alongside Kiro and Zed.

## Before using it

- Run as your normal user, **never with `sudo`**.
- Complete CachyOS installation first. Python 3.11+, pacman, and sudo are required for native package installation. Flatpak and Homebrew are needed only for selections using those routes; no downloaded bootstrap scripts run.
- CachyOS apply targets x86_64. Retained vendor artifacts also include aarch64 payloads for cross-platform preview; those do not imply CachyOS ARM support.
- The standard `~/.config` and `~/.local/share` locations are supported. Equivalent canonical home paths are accepted. A genuinely different XDG location is blocked rather than written incorrectly.
- Review the catalog and the plan before applying. The setup is not an OS installer or a replacement for system backups.

Before the first apply on any machine, complete the [machine commissioning runbook](docs/machine-commissioning.md). It keeps storage, encryption, backup, power, and optional capability decisions per-machine without changing installer defaults.

Official CachyOS/Arch repository packages are preferred where available. Native application installs require explicit `--apply` and use sudo for a pacman full system upgrade plus the selected packages, avoiding [unsupported partial upgrades](https://wiki.archlinux.org/title/System_maintenance#Partial_upgrades_are_unsupported). Review pacman's transaction before accepting it. This can update packages beyond the selection. There is no AUR automation. The setup never alters groups, enables system services, changes the desktop, or changes your login shell.

### Docker Engine

Provision Docker Engine separately using the [Arch Docker guidance](https://wiki.archlinux.org/title/Docker). Install the official `docker` package and explicitly decide whether to enable its service and grant user access to the local daemon.

**Docker group access is effectively root access.** These operations are deliberately not automated. The setup checks `/usr/bin/docker` and `/usr/bin/dockerd`, then queries only the local `/var/run/docker.sock`, not an existing remote Docker context. Missing or inaccessible Engine access blocks the full plan unless `docker-engine` is explicitly skipped.

## Preview and install

```sh
# Application IDs, sources, methods, and notes. No installation.
./setup.sh --list

# Preview the entire catalog and theme. No installation or configuration writes.
./setup.sh
```

### Profiles

Profiles are checked-in canonical catalog IDs: `base`, `terminal`, `developer`, `cloud`,
`security`, `desktop`, and `ai`. `--list` shows every profile containing each application.
Use the staged order `base`, then `terminal` or `developer`, then only the domain profile you
need. Profiles only select applications; third-party sources still require per-ID `--trust`.

```sh
# Start with an explicit, reviewable profile. Profiles select apps but never trust sources.
./setup.sh --apps-only --profile base --format json
./setup.sh --apps-only --profile base,terminal --skip btop

# Apply only after reviewing the plan and approving its reported third-party IDs.
./setup.sh --apps-only --only obsidian,todoist --trust todoist --apply

# Individual IDs can refine a profile; --skip always wins.
./setup.sh --apps-only --profile developer --only git --skip gh
```

The `desktop` profile includes Obsidian, Todoist, Zed, and Bruno; `developer` also includes Zed and Bruno.
To preview the note-taking and task applications without deploying the rest of the theme:

```sh
./setup.sh --apps-only --only obsidian,todoist --trust todoist --format json
```

The `developer` profile also includes gitlogue, oxker, grex, Kondo, Worktrunk, and the
existing Mike Farah yq entry. `terminal` adds VisiData and croc, `cloud` adds dnsglobe,
and `ai` adds llmfit. The catalog records each tool's explicit native or fallback route.
Both catalog files participate in the default full selection; `extended` does not mean opt-in.
Preview this group without deploying configuration:

```sh
./setup.sh --apps-only \
  --only gitlogue,visidata,dnsglobe,oxker,llmfit,croc,grex,kondo,worktrunk,yq \
  --format json
```

`vd` and `wt` are selection aliases for VisiData and Worktrunk. Catalog and profile edits
invalidate saved plans; regenerate them before applying.

The `base` profile includes zoxide and fzf; `developer` includes delta (`git-delta`).
Bat, ripgrep, and fd remain in `base`, and btop remains in `terminal`.
These tools use official native repository packages without per-ID source approval.

```sh
./setup.sh --apps-only --only zoxide,fzf,bat,btop,ripgrep,fd,delta --format json
```

A preview can run on this Mac; `--apply` requires CachyOS x86_64 and a non-root user.
Read-only package queries may use package managers' own caches or locks.

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

`--doctor` reports CachyOS, architecture, native package manager, fallback Homebrew, Flatpak, Docker, Plasma, Vulkan,
and root/home free-space readiness. It never installs, repairs, downloads, locks, or creates
state. Both commands are observation-only and cannot be combined with `--apply`, replacement,
desktop activation, or plan-writing options.

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

Third-party taps, registries, vendor artifacts, and catalog-marked Flatpaks need explicit source approval. Approval is per application and per invocation:

```sh
./setup.sh --apps-only --only omp,kiro --trust omp,kiro
./setup.sh --apps-only --only omp,kiro --trust omp,kiro --apply
```

For the full catalog, omit `--only` and approve each reported third-party ID with `--trust`. Flags accept comma-separated IDs and can be repeated. There is no implicit trust-all or ignore-errors mode. **Any blocker prevents installation from starting.** Use `--skip` only for applications you intentionally exclude:

```sh
./setup.sh --skip docker-engine
```

### Theme and existing machines

```sh
# Preview or deploy appearance files without installing packages.
./setup.sh --theme-only
./setup.sh --theme-only --apply

# Also activate the KDE color scheme in an active Plasma session.
./setup.sh --theme-only --desktop
./setup.sh --theme-only --desktop --apply
```

Appearance files use the local Mac palette, with Linux-specific adaptations. Your desktop wallpaper is left unchanged.

- KDE colors; Kitty and JetBrainsMono Nerd Font settings.
- Starship, Micro, Bat, btop, Yazi, Lazydocker, and Fastfetch.
- Kiro editor and terminal colors, plus Trippy. Apps without a custom palette inherit terminal colors where supported; this does not claim to recolor every Flatpak or web interface.

Missing files are installed; identical files are left unchanged. Different existing files are **preserved**, including on repeat runs. Symlink destinations and symlink ancestors are protected, even with replacement consent. No configuration merge is attempted.

Inspect an exact managed configuration path before deciding whether to replace it:

```sh
./setup.sh --theme-only --diff .config/kitty/kitty.conf
./setup.sh --theme-only --diff .zshrc --diff .config/starship.toml
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

Start Zsh to use it. The setup does not call `chsh`. Shell integration includes user tool paths, optional Linuxbrew paths, the themed prompt, direnv, mise, native Zsh plugins with a Homebrew fallback, and Granted's interactive `assume` alias. Interactive hooks require an actual terminal. Existing direnv/mise trust checks remain in force; nothing authorizes project scripts automatically.

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

`ps`, `df`, `find`, and `grep` are not replaced. Use `rg`, `fd`, `ouch`, `rsync`, and `rclone`
directly. Procs and duf are not included in the catalog. These aliases do not affect scripts or
agent shells, and removing catalog entries does not uninstall tools already on a machine.

## Package behavior and important constraints

The complete source of truth is [`catalog/core.json`](catalog/core.json),
[`catalog/extended.json`](catalog/extended.json), and [`profiles.json`](profiles.json).
`--list` shows every requested application and its profile membership. Sources were resolved using
the Mac Brewfile, installed configuration, existing Mac setup implementation, and upstream Linux
documentation.

| Route           | Behavior                                                                                                                                                                                                                               |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| pacman          | Explicit official repository packages. Apply uses sudo and a full system upgrade with `--needed`; no partial upgrades, AUR helpers, group changes, or service activation. Rolling repository versions are not pinned.                  |
| Homebrew        | CLI formulas, never casks. Existing formulas are skipped. Missing manager prerequisites are planned explicitly. No automatic global upgrade or cleanup.                                                                                |
| Flatpak         | Remaining sandboxed apps install per user from Flathub. An existing system installation is left in place. A conflicting user `flathub` URL blocks installation.                                                                        |
| Vendor archives | Versioned HTTPS downloads with catalog SHA256 checks. Payloads stay in versioned user directories, with executable wrappers and GUI launchers. No archive install hooks, device nodes, escaping paths, escaping links, or setuid bits. |
| uv / npm        | Exact top-level package versions in user-owned locations. Cheznav requests Python 3.14 through uv. Python tools may download a compatible managed interpreter.                                                                         |
| `yaml-py`       | A private uv environment containing PyYAML, exposed as a Python interpreter command, matching the Mac helper rather than substituting a different YAML CLI.                                                                            |

### Special applications

- **llama.cpp:** the pinned upstream Vulkan bundle is used, not a CPU-only Homebrew substitute. Installation must detect a Vulkan device with `llama-cli --list-devices`. A working host Vulkan driver and compatible runtime libraries are required. No model downloads or server services are configured.
- **Kiro:** the official portable Linux bundle is installed user-locally. It needs the host's normal Electron desktop libraries and unprivileged user namespaces. The setup never adds `--no-sandbox`, sets a root-owned sandbox helper, or disables OS security policy.
- **AWS Session Manager Plugin:** the official versioned Debian payload is unpacked into a private application directory. No Debian maintainer scripts run and nothing is written to host `/usr` or `/etc`.
- **DBeaver Community:** the desktop profile selects the official Arch `dbeaver` package. Configure a DuckDB connection and download its JDBC driver inside DBeaver. The retired Harlequin, usql, and standalone DuckDB clients are not available to scripts or OMP through this setup.
- **Discord:** the desktop profile selects the official Arch `discord` package for x86_64. Accounts, autostart, and permissions are not configured. The previous Flatpak route and its sandbox restrictions no longer describe this selection.
- **Obsidian:** the desktop profile selects the official Arch `obsidian` package. No vaults, plugins, sync accounts, or credentials are configured. This is a native application, not the previous community Flatpak.
- **Todoist:** the [community Flathub package](https://github.com/flathub/com.todoist.Todoist) repackages the vendor desktop client and requires `--trust todoist`. It is [x86_64-only](https://github.com/flathub/com.todoist.Todoist/blob/master/flathub.json); on aarch64, use `--skip todoist` and the browser client instead. [Upstream documents Snap/AppImage and officially supports Ubuntu GNOME only](https://www.todoist.com/help/todoist/get-started/install-todoist-for-linux-KgKaJa6H). This setup does not install snapd, import accounts, configure autostart, or add permission overrides.
- **Retired Notion launcher:** Notion is no longer in the catalog or profiles. Existing files are not automatically removed. If previously installed, review `~/.local/share/applications/vixygrey-notion.desktop` and remove that menu entry manually if no longer wanted. Browser data and accounts are untouched. Regenerate saved plans after this catalog change.
- **Zed:** the official Arch `zed` package supplies the editor and application-menu integration. A working Vulkan driver, desktop portals, and compatible host libraries remain prerequisites. No downloaded installer script runs.
- **Bruno:** official versioned Debian payloads for both architectures are extracted user-locally, without maintainer scripts or host writes. The publisher-documented Flatpak is x86_64-only, so it is not used here. The native application requires compatible host Electron libraries and unprivileged user namespaces for Chromium sandboxing; the setup never adds `--no-sandbox`. Accounts, collections, environments, and credentials are not imported. The separate Bruno CLI is not installed.
- **Granted / AWS / Bitwarden / OMP:** credentials, accounts, tokens, profiles, and login flows remain yours to configure. No credentials are imported from the Mac.
- **Backups:** backup software and policy are outside this setup. Choose destinations, encryption, credentials, retention, and scheduling separately, then validate restoration using the machine commissioning runbook.
- **Network diagnostics / Caligula:** no uinput permissions, network capabilities, or disk writes are enabled by setup. Privileged runtime actions remain explicit user decisions.
- **gitlogue:** replays local Git history and requires Git plus a repository with commits. Setup does not set its theme or start watch mode.
- **VisiData:** the selected package manager supplies its Python environment and commands. Optional formats such as XLSX and Parquet need additional dependencies; setup does not add them or promise every upstream format.
- **dnsglobe:** queries public DNS resolvers, including direct DNS on port 53, which restricted networks may block. Displayed resolver regions are not independent probes physically running in those regions. Setup does not change firewall rules or configure EDNS Client Subnet.
- **oxker:** can control containers through an accessible Docker daemon. Socket access can be root-equivalent; setup does not change Docker groups, sockets, services, or contexts. Lazydocker remains available.
- **llmfit:** recommends models from detected hardware; GPU detection depends on host drivers and probes. Recommendations do not prove Vulkan llama.cpp compatibility. Setup does not download models, configure providers, or start services.
- **croc:** encrypted transfers can use public relays. Protect transfer codes and use trusted endpoints. Setup does not configure a relay, open firewall ports, or start transfers.
- **grex:** generates candidate regular expressions from examples. Review unintended matches and compatibility with the intended regex engine.
- **Kondo:** installs only the `kondo` CLI. Cleanup deletes dependencies and build artifacts; upstream describes it as essentially `rm -rf` with a prompt. Back up projects and review targets. Setup never runs cleanup or installs `kondo-ui`.
- **Worktrunk:** installs `wt` for Git worktree management. Resolve package conflicts explicitly rather than forcing replacement. Directory-changing integration is an optional user step, `wt config shell install`, which modifies shell configuration and is never run by setup. Project hooks, agent plugins, LLM providers, and existing worktrees are not configured or changed.
- **yq:** the existing entry is Mike Farah's Go implementation, not Python yq. Setup does not force replacement of conflicting packages. The separate `yaml-py` interpreter helper remains available.

To preview or install Discord alone on an eligible x86_64 CachyOS machine:

```sh
./setup.sh --apps-only --only discord
./setup.sh --apps-only --only discord --apply
```

### Repeated runs, changes, and failure

Package-manager state is inspected rather than trusting a generic "done" marker. Archive receipts also check deployed file hashes and executable permissions. Native installs include a full system upgrade; existing Homebrew and Flatpak installations are not upgraded automatically. Registry installs use their pinned versions; if a manager refuses a conflicting existing version, the setup stops rather than forcing replacement.

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

### Fonts and existing installations

The CachyOS catalog uses the official `ttf-jetbrains-mono-nerd` package. Pacman owns its
system font files and font-cache hooks; setup no longer deploys a private font ZIP for this
selection. No per-ID source approval is needed.

Existing user-local fonts, archive payloads, wrappers, desktop launchers, and Flatpaks from an
older setup are not deleted automatically. Before applying to an existing home, review
`~/.local/bin`, `~/.local/share/applications/vixygrey-*.desktop`, and
`~/.local/share/fonts/JetBrainsMonoNerd` for old copies that can shadow native packages.
Remove only confirmed obsolete files after backing them up. Changing the catalog does not
migrate application data or uninstall a previous package route.

```sh
./setup.sh --apps-only --only jetbrains-mono-nerd-font
./setup.sh --status --apps-only --only jetbrains-mono-nerd-font --format json
```

## Security model

Review this repository and its catalog before execution. Official CachyOS/Arch repositories, Homebrew core, and the Flathub remote are baseline package sources; catalog-marked additional sources require explicit approval. Native package install scripts execute with root privileges through sudo; other package-manager builds, application binaries, and shell initialization hooks execute as your user. **Approval is not sandboxing or a security audit.**

TLS and hashes protect downloads against unexpected changes. Hashes are publisher-provided where available, or computed from the versioned official HTTPS artifact where noted. They do not independently prove publisher identity or make a compromised upstream safe. A changed artifact fails closed; refreshing a pin requires reviewing the source and replacing its checksum deliberately.

Top-level registry versions and vendor assets are pinned, but this is not a fully reproducible supply-chain lock: pacman, Homebrew, and Flatpak use their current catalogs, and registry transitive dependencies can change. OS updates and application vulnerability maintenance remain necessary.

### Refreshing catalog pins

Catalog and profile changes are deliberately manual. Do not use Dependabot or another automated
updater for `catalog/*.json`, `profiles.json`, vendor artifact URLs, SHA-256 values, Flatpak IDs,
native package names, Homebrew formulas, or source-approval classifications.

For every catalog refresh:

1. Start from the authoritative upstream release page or publisher documentation.
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
npm ci
uv sync --locked --group dev
go install mvdan.cc/sh/v3/cmd/shfmt@v3.14.1
export PATH="$(go env GOPATH)/bin:$PATH"
./scripts/verify
```

This canonical check requires Node 24.18.1, uv 0.13.1, Go 1.26+, Python 3.11+, Zsh, and ShellCheck. Run `npm ci` and `uv sync --locked --group dev` after cloning or changing their lockfiles. Node, Prettier, uv, Ruff, Go, and shfmt are development-only tooling; the installer runtime remains Python standard library. The check validates Prettier, Ruff, and explicitly-dialected Bash/Zsh shfmt formatting; runs the safety suite; validates the catalog with `--list`; checks managed shell files; and previews a trusted archive selection plus theme deployment in empty temporary homes. It never calls `--apply` or installs missing tools. `scripts/format-shell --check` verifies `setup.sh`, the repository Bash helper scripts, and the two managed Zsh files; `--write` is the opt-in normalization command. It uses two-space indentation and does not enable shfmt simplification.

The same gate also runs Ruff correctness linting with the explicit `E9` and `F` rule families.
Linting does not enable auto-fixes, import sorting, or broader modernization rules. Its scope is
the installer modules, the development palette validator, and tests, matching Python formatting.

`python3 -B scripts/validate-palette.py` checks the explicit managed theme inventory against
`theme/palette.json`, including required roles, Starship's palette, ANSI assignments, encoded
KDE/Trippy colors, and theme-name references. `--root PATH` supports isolated fixture copies for
validation. Application files remain explicit, with no generated colors or runtime palette
dependency. Existing app-specific line highlights and active line-number choices are preserved;
pure white is allowed only in Kitty and Kiro's ANSI bright-white slots. The shell's custom Bat
default is checked, but upstream Vivid/LS_COLORS behavior is outside this palette contract.
These static checks do not prove application rendering, contrast, or KDE activation.

The safety suite covers preservation, backups, symlink/traversal rejection, executable modes, archive links and setuid stripping, font filtering and staged upgrades, exact-path font replacement, retirement provenance, cache-only recovery, Debian-container boundaries, invalid selections, source approval, and canonical home aliases. Font deployment tests use isolated homes with local ZIP fixtures and recording cache executables; they do not validate Linux fontconfig or actual rendering.

During development on the reference Mac, isolated smoke runs exercised actual theme deployment and repeat planning; Bat, Starship, lnav, Fastfetch, interactive Zsh, and the btop TUI; PyYAML installation and parsing; and checksum-verified AWS, Eilmeldung, Kitty, OMP, Nerd Font, and Kiro payload installation without executing the Linux binaries. A live local HTTPS fixture also verified executable deployment under a home path containing spaces and rejection of a changed download before any home writes. These historical checks do not establish current catalog support for removed applications.

The Zed/Bruno additions were smoke-checked with both architecture previews and explicit
source approval. Both official Zed tarballs and Bruno Debian payloads passed checksum verification
and deployment through a local HTTPS fixture, including relocated launchers/icons, receipt checks,
repeat planning, and preservation of an existing command, under home paths containing spaces and
percent signs. These historical checks did not execute Linux binaries or validate the target application menu.

**The full application install, Linux binary execution, Vulkan device detection, and KDE desktop activation have not been run on a CachyOS target.** A local Docker daemon was unavailable. Validate the plan on the intended machine before approving an apply run, and validate the desktop there before treating its appearance as verified.

## License

This repository is licensed under the [MIT License](LICENSE). Third-party applications and
dependencies installed or used by this setup retain their own licenses.
