# Test plan: issue 8

| Scenario                                         | Risk | Evidence                                    | Owner               |
| ------------------------------------------------ | ---- | ------------------------------------------- | ------------------- |
| Locked Prettier install is reproducible          | P1   | `npm ci`                                    | formatter-toolchain |
| Supported files are formatted                    | P1   | `npm run format:check` after one write pass | formatter-toolchain |
| Existing installer safety behavior remains green | P1   | `./scripts/verify`                          | shared-gate         |
| Workflow installs Node and shares the same gate  | P1   | Actionlint and green GitHub Actions job     | workflow            |
