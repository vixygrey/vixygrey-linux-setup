# Add Prettier as the repository formatter

## Requirement delta

- ADDED: Pinned, development-only Prettier tooling with deterministic format commands.
- MODIFIED: The canonical local and CI verifier checks supported formatting.

## Acceptance criteria

1. Prettier 3.9.10 and its lockfile install through `npm ci`.
2. Supported Markdown, JSON, JSONC, YAML, and YML files are normalized.
3. Generated, binary, lockfile, and unsupported files are explicitly excluded.
4. The verifier and CI share one formatter check.
5. Installer runtime dependencies and behavior remain unchanged.

## Risk

P1. A repository-wide formatting pass can create broad non-functional churn. The final check and file-class review must prove no parser or behavior regression.
