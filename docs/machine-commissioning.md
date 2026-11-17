# Machine commissioning

Use this runbook before the first `--apply` on any Aurora machine. It is a manual checklist,
not installer behavior. It does not choose partitions, mount points, power policy, backup
locations, or credentials for you.

Keep the machine decision record and unredacted evidence outside this repository. Do not commit
host names, drive serials, repository URLs, passwords, recovery material, credentials, or command
output that contains them.

## 1. Firmware, boot, and encryption

Before writing data:

1. Record the current firmware or BIOS version and whether an update is required according to the
   hardware vendor's guidance.
2. Follow Aurora's [installation guide](https://docs.getaurora.dev/guides/install-guide), including
   its current Secure Boot guidance. Do not copy changing installer steps or recovery material into
   this repository.
3. Record the encryption decision for every internal storage device. The installer does not create,
   modify, or unlock encrypted volumes.
4. Select the desktop-managed power profile appropriate for the machine. Do not add a competing
   power-tuning daemon without a separate, reviewed decision.

## 2. Storage decision record

Complete a private row for every internal storage device before placing models, containers,
workspaces, or large caches on it.

| Field            | Record privately for each device                        |
| ---------------- | ------------------------------------------------------- |
| Role             | System/home, data/workspace, removable, or unused       |
| Encryption       | Encryption state and recovery process                   |
| Mount point      | Chosen path and mount ownership                         |
| Capacity         | Total, free capacity, and expected growth               |
| Data classes     | Models, containers, worktrees, caches, backups, or none |
| Backup inclusion | Included, excluded, and reason                          |
| Recovery         | How the data is restored after loss or replacement      |

Do not assume a particular drive count, filesystem, mount point, or capacity. A second internal
drive can improve capacity or local recovery options, but it is not an independent backup.

After normal Aurora provisioning, capture the read-only result of:

```sh
./setup.sh --doctor --format json
```

Use its root and home free-space values with the decision record. Re-check capacity before a large
model download, container image pull, or workspace migration.

## 3. Data placement

The setup owns only its existing user-state locations:

- Receipts: `~/.local/state/vixygrey-setup/receipts/`
- Explicit replacement backups: `~/.local/state/vixygrey-setup/backups/`
- Portable application payloads: `~/.local/share/vixygrey/apps/`

Choose the location for every other large data class per machine:

- **Worktrees and reproducible build caches:** use the data location selected in the private record.
- **Container images and volumes:** inspect the selected Aurora DX, Docker, or Podman runtime before
  reserving space or configuring bind mounts. This repository does not assume a runtime storage path.
- **Local models:** choose a data location only when the machine uses a supported local-model path.
  Record the capacity requirement and revisit it during the target-specific model validation.

Do not make a path a repository default merely because it suits one machine.

## 4. Backup and restore

Backup software is not installed or configured by this setup. Choose it separately; the installer
does not configure credentials, write retention policy, enable timers, or run backups.

Before relying on a machine:

1. Choose an encrypted external or remote backup destination outside the machine's internal storage.
2. Record privately which data is included, which reproducible caches are excluded, the retention
   policy, and where passphrases and recovery material are stored.
3. Perform and record a restore drill for one representative configuration file and one workspace
   file. A completed backup job without a restore drill is not sufficient evidence.

Keep backup destination details, credentials, passphrases, and restore evidence out of this repository.

## 5. Aurora and developer prerequisites

Complete Aurora's normal provisioning first. Follow Aurora's [software guidance](https://docs.getaurora.dev/guides/software)
for Flatpak, Homebrew, and containers. The setup does not bootstrap those prerequisites.

When the machine needs Docker Engine, use Aurora DX according to its
[developer-mode guidance](https://docs.getaurora.dev/dx/aurora-dx-intro). This is a manual host
choice. On a standard Aurora image, it includes `ujust devmode`; Aurora then requires `ujust dx-group`
and a logout/login before Docker access works. Docker group access is effectively root-equivalent.

After prerequisites are present, use this sequence:

```sh
# Observe readiness. No installation or configuration writes.
./setup.sh --doctor --format json

# Review a narrow catalog selection. No installation or configuration writes.
./setup.sh --apps-only --only micro,bat,eza,git,starship

# Save a reviewed selection artifact before an explicit apply.
./setup.sh --apps-only --only omp --trust omp --format json --plan-out omp-plan.json
```

Run `--apply` only after reviewing the selection and plan. Source approval, conflict preservation,
and explicit replacement rules remain in force.

## 6. Target-specific follow-ons

Keep target-specific validation separate from this machine-neutral runbook:

- Aurora install, desktop, Docker, and Vulkan acceptance: issue #25.
- AMD Radeon local-model validation and model capacity evidence: issue #18.
- Additional storage and GPU presentation in Fastfetch or btop: issue #24.

Each target should supply only sanitized facts to those follow-ons: Aurora version, architecture,
selected catalog IDs, free-space evidence, and the private decision record's conclusions. Do not
commit private machine identifiers or secrets.
