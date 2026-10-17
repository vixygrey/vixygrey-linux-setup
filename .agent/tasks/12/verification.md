# Verification evidence: issue 12

- **Verified at:** 2026-10-17T03:26:05Z
- **Risk:** P1
- **Verifier:** pinned shfmt command, canonical quality gate, and Actionlint

## Locked formatter toolchain

- **Commands:** `go install mvdan.cc/sh/v3/cmd/shfmt@v3.14.1`, `SHFMT="$(go env GOPATH)/bin/shfmt" ./scripts/format-shell --check`
- **Expected:** the exact shfmt module version installs and all explicit Bash/Zsh paths conform.
- **Actual:** installation completed; the installed binary reported `v3.14.1`; the formatter accepted the normalized version and exited 0 without a diff.
- **Result:** PASS

## Formatter boundaries

- **Command:** `./scripts/format-shell --write`, followed by `./scripts/format-shell --check`
- **Expected:** only the fixed Bash and Zsh source list is normalized at two-space indentation, and repeat checking is clean.
- **Actual:** `scripts/verify`, `scripts/format-python`, and `scripts/format-shell` normalized; `setup.sh` and both managed Zsh files already conformed. The repeated check exited 0.
- **Result:** PASS

## Failure behavior

- **Commands:** `SHFMT=missing-shfmt ./scripts/format-shell --check`; `SHFMT=/bin/echo ./scripts/format-shell --check`
- **Expected:** unavailable or mismatched binaries fail before formatting with an exact bootstrap command.
- **Actual:** both commands exited 2 with the required `go install mvdan.cc/sh/v3/cmd/shfmt@v3.14.1` remediation.
- **Result:** PASS

## Shared quality gate

- **Command:** `PATH="$(go env GOPATH)/bin:$PATH" ./scripts/verify`
- **Expected:** Prettier, Ruff, shfmt, isolated Python compilation, 15 safety tests, parser/lint checks, catalog validation, and no-write previews pass.
- **Actual:** exit 0. All 15 tests passed, Zsh parsing and ShellCheck passed, catalog validation passed, and preview homes remained empty.
- **Result:** PASS

## Workflow syntax

- **Command:** `actionlint .github/workflows/test-build-release-python.yml && git diff --check`
- **Expected:** valid workflow syntax, pinned action reference, and no whitespace errors.
- **Actual:** exit 0 with no diagnostics.
- **Result:** PASS

## TrueNorth gate

The existing external gate diagnostic defect remains tracked in [vixygrey/truenorth-mcp#552](https://github.com/vixygrey/truenorth-mcp/issues/552). This work does not rerun the known non-actionable failing gate.

## Pending evidence

The GitHub-hosted verification job must pass on this pull request and again after merge to `main` before issue 12 is complete.
