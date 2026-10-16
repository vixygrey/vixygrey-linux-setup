#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Python 3.11+ is required. This script does not bootstrap system dependencies.' >&2
  exit 2
fi
exec python3 "$ROOT/setup.py" "$@"
