"""AGENT: Automated preflight before manual WORKER_PARITY_CHECKLIST in-game pass."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str) -> int:
    print(f"\n=== {script} ===", flush=True)
    return subprocess.call([sys.executable, str(ROOT / "tools" / script)], cwd=str(ROOT))


def main() -> int:
    scripts = [
        "verify_native_workers.py",
        "audit_app_state_keys.py",
        "golden_registry_snapshot_diff.py",
    ]
    failed = 0
    for name in scripts:
        if _run(name) != 0:
            failed += 1

    print("\n=== Manual (owner, in-game) ===", flush=True)
    print("See docs/cpp_migration/WORKER_PARITY_CHECKLIST.md", flush=True)
    print("Compare launch configs:", flush=True)
    print("  - Pipela: Build and Run (C++ workers auto)", flush=True)
    print("  - Pipela: Python workers (PIPELA_NATIVE_WORKERS=0)", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
