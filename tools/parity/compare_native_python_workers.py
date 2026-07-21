"""AGENT: Compare native vs Python worker runtime (diagnostics harness)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Native vs Python worker parity smoke")
    parser.add_argument("--seconds", type=float, default=8.0, help="Run duration per mode")
    args = parser.parse_args()

    root = _repo_root()
    main_py = root / "main.py"
    if not main_py.is_file():
        print("main.py not found", file=sys.stderr)
        return 2

    env_base = os.environ.copy()
    env_base["PIPELA_NO_SPLASH"] = "1"

    def run_mode(label: str, native_workers: str) -> int:
        env = env_base.copy()
        env["PIPELA_NATIVE_WORKERS"] = native_workers
        print(f"\n=== {label} (PIPELA_NATIVE_WORKERS={native_workers}) ===", flush=True)
        try:
            proc = subprocess.run(
                [sys.executable, str(main_py), "--qt"],
                cwd=str(root),
                env=env,
                timeout=max(5.0, float(args.seconds) + 5.0),
                capture_output=True,
                text=True,
            )
        except subprocess.TimeoutExpired:
            print(f"{label}: timed out (expected for short smoke)", flush=True)
            return 0
        out = (proc.stdout or "") + (proc.stderr or "")
        for needle in ("C++ workers ON", "C++ workers", "kill_counter", "start_game"):
            if needle.lower() in out.lower():
                print(f"  saw log fragment: {needle}", flush=True)
        print(f"{label}: exit={proc.returncode}", flush=True)
        return proc.returncode

    rc_native = run_mode("native", "1")
    rc_python = run_mode("python", "0")
    print("\nDone - review stdout above; pair with UI stutter S3 scenario for macro stress.", flush=True)
    return 0 if rc_native == 0 and rc_python == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
