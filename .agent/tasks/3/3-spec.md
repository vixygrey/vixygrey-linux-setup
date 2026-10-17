# Add a CI quality gate for installer safety and configuration checks

## Requirement delta

- ADDED: A least-privilege GitHub Actions verification workflow for pull requests and `main`.
- MODIFIED: `./scripts/verify` compiles runtime modules in a managed temporary pycache.

## Acceptance criteria

1. The workflow grants only `contents: read` and has no secrets or write-capable trigger.
2. CI invokes only `./scripts/verify` after installing Zsh and ShellCheck.
3. The canonical verifier checks Python compilation without writing bytecode to the repository.
4. Local workflow syntax validation and the first hosted run provide durable evidence.

## Risk

P1. CI controls whether safety regressions reach `main`; local and hosted commands must remain identical.
