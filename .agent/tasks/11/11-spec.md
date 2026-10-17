# Add a pinned Python formatter quality gate

## Requirement delta

- ADDED: Locked, development-only Ruff formatter tooling and explicit Python format commands.
- MODIFIED: The canonical local and CI verifier check Python formatting.

## Acceptance criteria

1. uv locks Ruff 0.17.1 without declaring runtime dependencies.
2. Python format check and opt-in write commands target only tracked runtime modules and tests.
3. Existing Python files are normalized and behavior remains unchanged.
4. Local and CI gates invoke the same Python formatting check.

## Risk

P1. Formatting shared safety-sensitive modules creates broad non-functional churn. Checks must preserve compilation, tests, shell behavior, and installer safety semantics.
