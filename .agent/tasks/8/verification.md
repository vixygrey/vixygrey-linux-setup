# Verification evidence: issue 8

- **Verified at:** 2026-10-17T03:10:30Z
- **Risk:** P1
- **Verifier:** local formatter, quality, and workflow checks

## Formatter toolchain

- **Commands:** `npm ci`, `npm run format:check`
- **Expected:** exact locked Prettier installs and all supported files conform.
- **Actual:** both commands exited 0. Prettier 3.9.10 is locked in `package-lock.json`; all matched files use the configured style.
- **Result:** PASS

## Shared quality gate

- **Command:** `./scripts/verify`
- **Expected:** formatter check, isolated Python compilation, 15 safety tests, shell checks, catalog validation, and no-write previews pass.
- **Actual:** exit 0. All 15 tests passed, shell checks passed, catalog validation passed, and preview homes remained empty.
- **Result:** PASS

## Workflow syntax

- **Command:** `actionlint .github/workflows/test-build-release-python.yml`
- **Expected:** valid workflow syntax and action references.
- **Actual:** exit 0 with no diagnostics.
- **Result:** PASS

## TrueNorth gate

- **Command:** `truenorth_verify_gate` with phase `verify`
- **Expected:** configured quality gate exits 0.
- **Actual:** exit 1 with a truncated Rust compiler command fragment and no actionable diagnostic. The repository-local quality checks above passed. Reported as [vixygrey/truenorth-mcp#552](https://github.com/vixygrey/truenorth-mcp/issues/552).
- **Result:** BLOCKED EXTERNALLY

## Pending evidence

The GitHub-hosted verification job must pass on this pull request and again after merge to `main` before issue 8 is complete.

## Hosted verification and external blocker resolution (2026-10-18)

The pending hosted evidence above is resolved. [PR #10](https://github.com/vixygrey/vixygrey-linux-setup/pull/10) merged final head `6c1f1b87fa37559dc7309f57b77f1f925be5f87d` as `f99d225064ccbe7696ee485926199574b303a4a4` on `main`. Its [pull-request run](https://github.com/vixygrey/vixygrey-linux-setup/actions/runs/38997804021) (`pull_request`, final head) and [post-merge main run](https://github.com/vixygrey/vixygrey-linux-setup/actions/runs/38997926082) (`push`, merge commit) both concluded success; the [PR verify job](https://github.com/vixygrey/vixygrey-linux-setup/actions/runs/38997804021/job/117294091142) and [main verify job](https://github.com/vixygrey/vixygrey-linux-setup/actions/runs/38997926082/job/117294475310) each concluded success, including the `./scripts/verify` step. The historical TrueNorth failure above was not rerun: external [#552](https://github.com/vixygrey/truenorth-mcp/issues/552) is now closed as completed, not retroactively a successful gate result. Hosted checks do not establish Aurora, GUI, fontconfig, Docker, Vulkan, or KDE target acceptance.
