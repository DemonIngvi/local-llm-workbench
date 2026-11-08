#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo 'Python 3 is required'; exit 1; }
command -v docker >/dev/null || { echo 'Docker with Compose is required'; exit 1; }
python3 scripts/setup.py "${1:-start}"
