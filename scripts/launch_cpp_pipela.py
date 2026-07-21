"""Launch C++ Pipela.exe from F5 (debugpy / Cursor-compatible)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "cpp" / "build" / "release" / "src" / "app"
EXE = APP_DIR / "Pipela.exe"


def main() -> int:
    if not EXE.is_file():
        print(
            f"Pipela.exe not found:\n  {EXE}\n\nBuild first: scripts\\build_cpp_release.bat",
            file=sys.stderr,
        )
        return 1
    env = os.environ.copy()
    env.setdefault("PIPELA_DEV_UI", "1")
    proc = subprocess.Popen([str(EXE)], cwd=str(APP_DIR), env=env)
    return int(proc.wait())


if __name__ == "__main__":
    raise SystemExit(main())
