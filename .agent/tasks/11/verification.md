# Verification evidence: issue 11

- **Verified at:** 2026-10-17T03:17:40Z
- **Risk:** P1
- **Verifier:** locked Ruff environment, canonical quality gate, and Actionlint

## Locked formatter toolchain

- **Commands:** `uv sync --locked --group dev`, `./scripts/format-python --check`
- **Expected:** locked Ruff 0.17.1 syncs and all declared Python paths conform.
- **Actual:** both commands exited 0; five runtime and test paths are already formatted.
- **Result:** PASS

## Shared quality gate

- **Command:** `./scripts/verify`
- **Expected:** Prettier and Ruff checks, isolated Python compilation, 15 safety tests, shell checks, catalog validation, and no-write previews pass.
- **Actual:** exit 0. All 15 tests passed, shell checks passed, catalog validation passed, and preview homes remained empty.
- **Result:** PASS

## Workflow syntax

- **Command:** `actionlint .github/workflows/test-build-release-python.yml`
- **Expected:** valid workflow syntax and action references.
- **Actual:** exit 0 with no diagnostics.
- **Result:** PASS

## TrueNorth gate

The existing external gate diagnostic defect remains tracked in [vixygrey/truenorth-mcp#552](https://github.com/vixygrey/truenorth-mcp/issues/552). This work does not rerun the known non-actionable failing gate.

## Pending evidence

The GitHub-hosted verification job must pass on this pull request and again after merge to `main` before issue 11 is complete.

## Hosted verification and external blocker resolution (2026-10-18)

The pending hosted evidence above is resolved. [PR #13](https://github.com/vixygrey/vixygrey-linux-setup/pull/13) merged final head `58da2a5588a00b5acf297cdbb653c4c423d0ebc7` as `25e9e914f67909a951e0fc56330752fb52838214` on `main`. Its [pull-request run](https://github.com/vixygrey/vixygrey-linux-setup/actions/runs/38998253118) (`pull_request`, final head) and [post-merge main run](https://github.com/vixygrey/vixygrey-linux-setup/actions/runs/38998298582) (`push`, merge commit) both concluded success; the [PR verify job](https://github.com/vixygrey/vixygrey-linux-setup/actions/runs/38998253118/job/117295482090) and [main verify job](https://github.com/vixygrey/vixygrey-linux-setup/actions/runs/38998298582/job/117295623514) each concluded success, including the `./scripts/verify` step. External [#552](https://github.com/vixygrey/truenorth-mcp/issues/552) is closed as completed; the historical TrueNorth failure was not rerun or reclassified as success. Aurora, GUI, fontconfig, Docker, Vulkan, and KDE target acceptance remains unexercised.
