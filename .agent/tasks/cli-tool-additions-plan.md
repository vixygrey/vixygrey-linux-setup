# CLI tool additions plan

Status: implemented and locally verified 2026-10-21. Aurora installation remains unverified.

## Repository review

| Requested tool | Current coverage                                                        | Planned change                                                                     |
| -------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| zoxide         | Absent                                                                  | Add Homebrew core entry and base profile membership                                |
| fzf            | Absent                                                                  | Restore Homebrew core entry and add base profile membership                        |
| bat            | core catalog, base profile, managed theme and interactive cat alias     | Preserve existing behavior                                                         |
| btop           | core catalog, terminal profile, managed theme and interactive top alias | Preserve existing behavior                                                         |
| ripgrep        | core catalog, base profile; executable rg                               | Preserve existing behavior                                                         |
| fd             | core catalog, base profile                                              | Preserve existing behavior                                                         |
| delta          | Absent                                                                  | Restore catalog ID delta using formula git-delta; add developer profile membership |

The setup is catalog-driven. Existing brew detection checks installed formula names;
installation runs `brew install --formula <package>`. No new installer method,
Python dependency, downloaded installer, tap, or OS package layering is needed.
Both catalog files participate in the default full selection.

The approved-tool-cuts record in execution-status.yml documents deliberate removal
of fzf, delta, and fzf shell integration. This request proposes their reintroduction;
retain that historical record and append new implementation evidence when complete.

## Implementation sequence

1. Add three explicit entries to catalog/core.json, following adjacent brew entries:
   - ID/package zoxide, source https://github.com/ajeetdsouza/zoxide.
   - ID/package fzf, source https://github.com/junegunn/fzf.
   - ID delta, package git-delta, source https://github.com/dandavison/delta.
   - Use method brew and third_party false. An optional git-delta selection alias
     may follow the existing catalog alias convention.
   - Homebrew core currently publishes Linux arm64 and x86_64 bottles for all
     three. Let Homebrew manage versions and dependencies as with existing brew
     entries; do not claim immutable versions or add decorative version fields.
2. Update profiles.json: zoxide and fzf in base, delta in developer. Leave the
   four existing tools and their memberships unchanged. Selection and --skip
   behavior remain generic, without implicit dependency selection.
3. Add guarded Zsh integration in dotfiles/.config/vixygrey/setup.zsh:
   - Enable only in interactive shells with terminal stdin/stdout and no AI_AGENT
     marker; check each executable independently.
   - Load `source <(fzf --zsh)` after compinit and before syntax highlighting.
     Document its Ctrl+R, Ctrl+T, and Alt+C bindings. Respect upstream user
     FZF_* settings; do not force a file walker or a global preview command.
   - Initialize `eval "$(zoxide init zsh)"` after compinit, near the end of the
     integration block. Keep native cd unchanged; expose z and zi. zi requires
     fzf at runtime, but zoxide remains usable when fzf is skipped.
   - Do not run upstream shell installation scripts or modify shell files outside
     the existing managed-file mechanism.
4. Install delta without automatically rewriting ~/.gitconfig or forcing a pager.
   Document optional user-owned settings `core.pager = delta` and
   `interactive.diffFilter = delta --color-only`. Do not change merge behavior,
   add a global PAGER, or create a managed Git identity/configuration file.
   Git configuration automation is outside this installation request.
5. Update README.md with additions, profile membership, shell shortcuts, optional
   delta activation, and the distinction between --apps-only installation and
   managed shell configuration deployment. Existing shell fragments can be
   preserved as conflicts: explain review with --diff and existing explicit
   replacement consent rather than promising automatic activation. Regenerate
   saved plans after catalog/profile changes. Record completion and verification
   under .agent/tasks/ without rewriting the historical removal record.

## Acceptance and verification

- Run --validate-catalog and --list; check source, formula, and profile data.
- Exercise actual CLI previews for all seven IDs, base/developer profiles, and
  --skip fzf. Confirm no home writes and that no per-ID trust is required for
  these Homebrew core formulas. Use temporary HOME and Homebrew cache locations.
- Exercise installed and missing formula states, especially that delta detection
  uses git-delta rather than the executable name. Reuse generic tests; add a
  permanent regression only if an uncovered behavioral bug is discovered.
- Use an isolated real Zsh TTY with actual fzf/zoxide binaries. Verify z changes
  to a known recorded directory, zi selects a directory, fzf filtering works,
  and the documented key bindings activate. Verify absent binaries,
  noninteractive shells, and AI_AGENT shells introduce no new hooks/bindings.
- Smoke delta on a small real diff with --paging=never. Check optional Git pager
  behavior only with temporary Git configuration, not the user's global config.
- Verify preserved and symlink-protected shell configuration remains protected,
  and explicit replacement retains the existing backup behavior.
- Run ./scripts/verify after implementation. On Aurora, apply the selected tools,
  check executable versions and repeat planning without redundant installs.
  A Mac preview cannot establish Linux installation or TUI rendering correctness.

## Review evidence

Before implementation, ./scripts/verify passed: 72 tests, formatting, linting,
palette validation, compilation, shell checks, catalog validation, and isolated
no-write previews. No tools were added or installed during this review.

Implementation evidence:

- Added zoxide, fzf, and delta to catalog/core.json; zoxide/fzf to base and
  delta to developer. The four existing requested tools remain unchanged.
- Added human-only terminal Zsh hooks, with native cd and user FZF_* settings
  preserved. README documents activation, file conflicts, and optional delta use.
- Actual CLI previews against installed Homebrew selected all seven tools with
  only zoxide pending and no blockers. Controlled formula inventory fixtures
  exercised seven missing actions, git-delta detection, repeat skips, profiles,
  and skip precedence. Preview homes remained empty.
- A real controlling-terminal Zsh smoke used fzf 0.74.5 and a checksum-verified
  temporary zoxide 0.10.0 binary. It exercised z/zi navigation and all three fzf
  bindings. Noninteractive, missing-tool, and AI_AGENT shells had no new hooks.
  Zoxide worked without fzf; user-disabled history binding remained disabled.
- Delta 0.20.1 rendered an actual diff directly and as Git's configured pager
  using temporary Git configuration. No global Git settings were changed.
- Actual managed shell deployment exercised create, repeat, preserve, explicit
  replacement with original-byte backup, and protected symlink states.
- ./scripts/verify passed all 72 tests and the existing formatting, linting,
  palette, compilation, shell, catalog, and no-write preview checks.
- Temporary smoke payloads and files were removed. No machine tools were
  installed. Aurora package application and Linux rendering remain unverified.

## Upstream references

- https://github.com/ajeetdsouza/zoxide#installation
- https://github.com/junegunn/fzf#setting-up-shell-integration
- https://github.com/dandavison/delta#get-started
- https://formulae.brew.sh/api/formula/zoxide.json
- https://formulae.brew.sh/api/formula/fzf.json
- https://formulae.brew.sh/api/formula/git-delta.json
