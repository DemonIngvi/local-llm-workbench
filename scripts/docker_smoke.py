#!/usr/bin/env python3
"""Opt-in test using an isolated Compose project; pulls images when missing."""
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PROJECT = 'llm-smoke-' + secrets.token_hex(6)
BASE = ['docker', 'compose', '-p', PROJECT, '-f', str(ROOT / 'tests/docker-smoke/compose.yaml')]


def main():
    print('Isolated test project:', PROJECT, flush=True)
    try:
        return subprocess.run(BASE + ['up', '--abort-on-container-exit', '--exit-code-from', 'verify'], cwd=ROOT).returncode
    finally:
        result = subprocess.run(BASE + ['down', '--volumes', '--remove-orphans'], cwd=ROOT)
        if result.returncode:
            print('Cleanup failed for project ' + PROJECT, file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
