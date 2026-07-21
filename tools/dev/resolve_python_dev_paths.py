"""Print Python include + import lib paths for native builds (one line each)."""
from __future__ import annotations

import pathlib
import sys
import sysconfig


def main() -> int:
    include = pathlib.Path(sysconfig.get_path("include"))
    lib = pathlib.Path(sys.base_prefix) / "libs" / f"python{sys.version_info.major}{sys.version_info.minor}.lib"
    print(include)
    print(lib)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
