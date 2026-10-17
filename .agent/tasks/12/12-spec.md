# Add a pinned shell formatter quality gate

## Requirement delta

- ADDED: Pinned, development-only `shfmt` tooling and explicit Bash/Zsh formatting commands.
- MODIFIED: The canonical local and CI verifier checks supported shell formatting.

## Acceptance criteria

1. `shfmt` 3.14.1 installs reproducibly through the exact Go module command.
2. Explicit Bash and Zsh dialect checks format all tracked repository shell sources at two-space indentation.
3. The formatter exposes opt-in `--check` and `--write` commands and rejects a missing or mismatched binary.
4. The verifier and CI share the same pinned formatting gate while retaining `zsh -n` and ShellCheck.
5. Installer runtime dependencies, preview-first behavior, and shell safety controls remain unchanged.

## Risk

P1. Formatter configuration or dialect selection can create broad non-functional churn or misparse Zsh-specific syntax. Explicit per-file dialects, no simplification option, and the canonical verifier limit that risk.
