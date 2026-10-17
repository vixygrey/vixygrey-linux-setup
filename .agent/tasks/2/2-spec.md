# Establish a TrueNorth project cockpit and canonical quality gate

## Requirement delta

- ADDED: Repository-local TrueNorth project scope, conventions, release plan, and session state.
- ADDED: `./scripts/verify` as the canonical local quality command.
- MODIFIED: README verification instructions now name the canonical command.

## Acceptance criteria

1. The repository contains a scoped `.agent/` cockpit and root project conventions.
2. `./scripts/verify` runs the safety suite, catalog validation, Zsh parsing, ShellCheck, and two
   no-write previews.
3. The verifier never calls `--apply` and cleans temporary homes.
4. Verification evidence records actual command output and result.
5. Runtime installer modules retain standard-library-only and preview-first behavior.

## Risk

P1. The new shell entry point performs checks on a safety-sensitive installer. Its behavior must be
proven through the real command surface.
