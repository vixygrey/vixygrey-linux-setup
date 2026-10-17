# Test plan: issue 12

| Scenario                                            | Risk | Evidence                                              | Owner            |
| --------------------------------------------------- | ---- | ----------------------------------------------------- | ---------------- |
| Pinned shfmt install is reproducible                | P1   | `go install mvdan.cc/sh/v3/cmd/shfmt@v3.14.1`         | locked-toolchain |
| Explicit Bash and Zsh paths are formatted           | P1   | `./scripts/format-shell --check` after one write pass | locked-toolchain |
| Missing and mismatched shfmt fail before formatting | P1   | isolated command invocation with substituted `PATH`   | locked-toolchain |
| Existing installer safety behavior remains green    | P1   | `./scripts/verify`                                    | canonical-gate   |
| Workflow provisions Go and shares the verifier      | P1   | Actionlint and green GitHub Actions job               | workflow         |
