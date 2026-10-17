# Conventions

- Use Python standard-library APIs in runtime modules.
- Keep package installation, archive handling, and home-file deployment in their existing modules.
- Test observable safety behavior with `unittest` and temporary directories.
- Treat catalog changes as behavior changes and run `./scripts/verify`.
- Do not run the installer with `sudo` or add automatic host mutation.
- Do not weaken symlink, traversal, checksum, conflict-preservation, or explicit-trust checks.
