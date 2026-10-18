# Vixygrey Linux Setup

Personal setup for **Aurora Linux** as a graphical workstation with selected useful CLI and TUI tools, Aurora DX's Docker Engine, and the Dracula-Sakura appearance from the existing Mac setup.

The catalog explicitly lists the selected applications and their installation sources. `soffice` is part of LibreOffice. Docker Engine is the explicitly approved replacement for Docker Desktop. Notion is available through an official-web-app launcher; Zed and Bruno use pinned upstream Linux payloads. OMP remains the primary AI development tool alongside Kiro and Zed.

## Before using it

- Run as your normal user, **never with `sudo`**.
- Complete Aurora's normal provisioning first. Python 3.11+, Homebrew, and Flatpak must be available for the relevant selections. This repository does not bootstrap them with downloaded shell scripts.
- The catalog includes architecture-specific x86_64 and aarch64 vendor artifacts. Preview uses the current machine's architecture.
- The standard `~/.config` and `~/.local/share` locations are supported. Equivalent canonical paths, including Aurora's `/home` aliases, are accepted. A genuinely different XDG location is blocked rather than written incorrectly.
- Review the catalog and the plan before applying. The setup is not an OS installer or a replacement for system backups.

Before the first apply on any machine, complete the [machine commissioning runbook](docs/machine-commissioning.md). It keeps storage, encryption, backup, power, and optional capability decisions per-machine without changing installer defaults.

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
./setup.sh --apps-only --only notion,zed,bruno --trust notion,zed,bruno --apply

# Individual IDs can refine a profile; --skip always wins.
./setup.sh --apps-only --profile developer --only git --skip gh
```

The `desktop` profile includes Notion, Zed, and Bruno; `developer` also includes Zed and Bruno.
To preview only these additions without deploying the rest of the theme:

```sh
./setup.sh --apps-only --only notion,zed,bruno --trust notion,zed,bruno --format json
```

A preview can run on this Mac; `--apply` requires Aurora and a non-root user. Read-only package
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

`--doctor` reports the current Aurora, architecture, Homebrew, Flatpak, Docker, Plasma, Vulkan,
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

Start Zsh to use it. The setup does not call `chsh`. Shell integration includes stable Linuxbrew and user tool paths, the themed prompt, direnv, mise, the Zsh plugins, and Granted's interactive `assume` alias. Interactive hooks require an actual terminal. Existing direnv/mise trust checks remain in force; nothing authorizes project scripts automatically.

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
| Homebrew        | CLI formulas, never casks. Existing formulas are skipped. Missing manager prerequisites are planned explicitly. No automatic global upgrade or cleanup.                                                                                |
| Flatpak         | Missing apps install per user from Flathub. An existing system installation is left in place. A conflicting user `flathub` URL blocks installation. LibreOffice/`soffice` and VLC receive conflict-preserving CLI wrappers.            |
| Vendor archives | Versioned HTTPS downloads with catalog SHA256 checks. Payloads stay in versioned user directories, with executable wrappers and GUI launchers. No archive install hooks, device nodes, escaping paths, escaping links, or setuid bits. |
| uv / npm        | Exact top-level package versions in user-owned locations. Cheznav requests Python 3.14 through uv. Python tools may download a compatible managed interpreter.                                                                         |
| `yaml-py`       | A private uv environment containing PyYAML, exposed as a Python interpreter command, matching the Mac helper rather than substituting a different YAML CLI.                                                                            |
| Web app         | Installs a menu launcher for the official HTTPS app in the configured default browser. Requires `xdg-open`; no unofficial native wrapper, browser profile changes, or automatic sign-in.                                               |

### Special applications

- **llama.cpp:** the pinned upstream Vulkan bundle is used, not a CPU-only Homebrew substitute. Installation must detect a Vulkan device with `llama-cli --list-devices`. A working host Vulkan driver and compatible runtime libraries are required. No model downloads or server services are configured.
- **Kiro:** the official portable Linux bundle is installed user-locally. It needs the host's normal Electron desktop libraries and unprivileged user namespaces. The setup never adds `--no-sandbox`, sets a root-owned sandbox helper, or disables OS security policy.
- **AWS Session Manager Plugin:** the official versioned Debian payload is unpacked into a private application directory. No Debian maintainer scripts run and nothing is written to host `/usr` or `/etc`.
- **DBeaver Community:** the desktop profile selects the publisher-listed Flathub package, with explicit `--trust dbeaver` approval. It replaces Harlequin, usql, and the standalone DuckDB CLI for graphical work. Configure a DuckDB connection and download its JDBC driver inside DBeaver. Dataset access may require Flatpak permissions, especially on additional drives. The retired command-line clients are not available to scripts or OMP through this setup.
- **Discord:** included in the default catalog and `desktop` profile through [Flathub's `com.discordapp.Discord` wrapper](https://flathub.org/apps/com.discordapp.Discord), with explicit `--trust discord` approval. The package is [x86_64-only](https://github.com/flathub/com.discordapp.Discord/blob/master/flathub.json); on aarch64, use `--skip discord` and the browser client instead. Game Activity, file access, and Rich Presence have sandbox limitations. The setup does not import accounts, configure autostart, or broaden sandbox permissions.
- **Notion:** the application-menu entry opens its [official web app](https://www.notion.com/help/notion-for-web) in your default browser. Notion does not provide a native Linux desktop download. Internet access, a supported browser, and your own sign-in are required; this is not an offline desktop client.
- **Zed:** official versioned tarballs for both supported architectures are deployed user-locally, with `zed` and an application-menu entry. No downloaded installer script runs. A working Vulkan driver, desktop portals, and the host's normal Linux libraries remain prerequisites. This native route lets Zed use host development tools without a Flatpak sandbox.
- **Bruno:** official versioned Debian payloads for both architectures are extracted user-locally, without maintainer scripts or host writes. The publisher-documented Flatpak is x86_64-only, so it is not used here. The native application requires compatible host Electron libraries and unprivileged user namespaces for Chromium sandboxing; the setup never adds `--no-sandbox`. Accounts, collections, environments, and credentials are not imported. The separate Bruno CLI is not installed.
- **Granted / AWS / Bitwarden / OMP:** credentials, accounts, tokens, profiles, and login flows remain yours to configure. No credentials are imported from the Mac.
- **Backups:** backup software and policy are outside this setup. Choose destinations, encryption, credentials, retention, and scheduling separately, then validate restoration using the machine commissioning runbook.
- **Network diagnostics / Caligula:** no uinput permissions, network capabilities, or disk writes are enabled by setup. Privileged runtime actions remain explicit user decisions.

To preview or install Discord alone on an eligible x86_64 Aurora machine:

```sh
./setup.sh --apps-only --only discord --trust discord
./setup.sh --apps-only --only discord --trust discord --apply
```

### Repeated runs, changes, and failure

Package-manager state is inspected rather than trusting a generic "done" marker. Archive receipts also check deployed file hashes and executable permissions. Existing Homebrew and Flatpak installations are not upgraded automatically. Registry installs use their pinned versions; if a manager refuses a conflicting existing version, the setup stops rather than forcing replacement.

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

Fonts stay in `~/.local/share/fonts/JetBrainsMonoNerd`; existing installations do not need a
directory migration. Source approval still requires `--trust jetbrains-mono-nerd-font` when
downloading a release.

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

```sh
./setup.sh --apps-only --only jetbrains-mono-nerd-font --trust jetbrains-mono-nerd-font
./setup.sh --status --apps-only --only jetbrains-mono-nerd-font --format json
```

## Security model

Review this repository and its catalog before execution. Homebrew core and the Flathub remote are baseline package sources; catalog-marked additional sources require explicit approval. Package-manager builds, package install scripts, application binaries, and shell initialization hooks still execute code as your user. **Approval is not sandboxing or a security audit.**

TLS and hashes protect downloads against unexpected changes. Hashes are publisher-provided where available, or computed from the versioned official HTTPS artifact where noted. They do not independently prove publisher identity or make a compromised upstream safe. A changed artifact fails closed; refreshing a pin requires reviewing the source and replacing its checksum deliberately.

Top-level registry versions and vendor assets are pinned, but this is not a fully reproducible supply-chain lock: Homebrew/Flatpak use their current catalogs, and registry transitive dependencies can change. OS updates and application vulnerability maintenance remain necessary.

### Refreshing catalog pins

Catalog and profile changes are deliberately manual. Do not use Dependabot or another automated
updater for `catalog/*.json`, `profiles.json`, vendor artifact URLs, SHA-256 values, Flatpak IDs,
Homebrew formulas, or source-approval classifications.

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

The Notion/Zed/Bruno additions were smoke-checked with both architecture previews and explicit
source approval. Notion launcher provisioning and its URL handoff were exercised with an isolated
browser handler. Both official Zed tarballs and Bruno Debian payloads passed checksum verification
and deployment through a local HTTPS fixture, including relocated launchers/icons, receipt checks,
repeat planning, and preservation of an existing command, under home paths containing spaces and
percent signs. These checks did not execute Linux binaries or validate Aurora's application menu.

**The full application install, Linux binary execution, Vulkan device detection, and KDE desktop activation have not been run on an Aurora target.** A local Docker daemon was unavailable. Validate the plan on the intended machine before approving an apply run, and validate the desktop there before treating its appearance as verified.

## License

This repository is licensed under the [MIT License](LICENSE). Third-party applications and
dependencies installed or used by this setup retain their own licenses.
