# Test plan: issue 3

| Scenario                                             | Risk | Evidence                                                     | Owner          |
| ---------------------------------------------------- | ---- | ------------------------------------------------------------ | -------------- |
| Python modules compile without repository bytecode   | P1   | `./scripts/verify` with temporary `PYTHONPYCACHEPREFIX`      | local-verifier |
| Existing safety and preview behavior remains green   | P1   | `./scripts/verify`                                           | local-verifier |
| Workflow syntax and action references are valid      | P1   | `actionlint .github/workflows/test-build-release-python.yml` | workflow       |
| CI runs the same local gate with minimal permissions | P1   | Green GitHub Actions job and workflow source review          | hosted-run     |
