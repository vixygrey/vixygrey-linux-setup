# Test plan: issue 11

| Scenario                                        | Risk | Evidence                                | Owner            |
| ----------------------------------------------- | ---- | --------------------------------------- | ---------------- |
| Locked Ruff environment is reproducible         | P1   | `uv sync --locked --group dev`          | locked-toolchain |
| Python formatting is non-mutating in check mode | P1   | `./scripts/format-python --check`       | locked-toolchain |
| Existing safety behavior remains green          | P1   | `./scripts/verify`                      | canonical-gate   |
| CI uses the same locked formatter gate          | P1   | Actionlint and green GitHub Actions job | workflow         |
