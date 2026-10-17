# Test plan: issue 2

| Scenario | Risk | Evidence | Owner |
| --- | --- | --- | --- |
| Existing archive and file safety behavior remains green | P1 | `python3 -B -m unittest discover -s tests -v` | quality-gate |
| Managed Zsh files parse | P1 | `zsh -n dotfiles/.zshrc dotfiles/.config/vixygrey/setup.zsh` | quality-gate |
| Shell entry points are lint-clean | P1 | `shellcheck setup.sh scripts/verify` | quality-gate |
| Catalog parses without mutation | P1 | `./setup.sh --list` | quality-gate |
| Trusted archive preview writes nothing | P1 | Temporary-home `omp` preview within `./scripts/verify` | quality-gate |
| Theme preview writes nothing | P1 | Temporary-home theme preview within `./scripts/verify` | quality-gate |
