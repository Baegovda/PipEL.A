"""Pipela용 cProfile 래퍼 — `python -m cProfile -o … main.py` 와 유사·dump 실패를 파일로 남김.

`python -m cProfile` 은 `dump_stats` 직전에 내부 오류가 나면 **0바이트 .stats**만 남을 수 있음(파일
열린 뒤 `marshal` 전에 예외). 드라이버는 `dump_stats` 를 try/except 하고, 실패 시
`profiling/pipela_cprofile_last_dump_error.txt` 에 기록한다.
"""
from __future__ import annotations

import cProfile
import os
import runpy
import sys
import traceback

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
_MAIN = os.path.join(_REPO_ROOT, "main.py")
_PROF = os.path.join(_REPO_ROOT, "profiling")
_PENDING = os.path.join(_PROF, "pipela_cprofile_pending.stats")
_ERR = os.path.join(_PROF, "pipela_cprofile_last_dump_error.txt")


def main() -> int:
    if not os.path.isfile(_MAIN):
        print(f"main.py not found: {_MAIN}", file=sys.stderr)
        return 2
    os.chdir(_REPO_ROOT)
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    os.makedirs(_PROF, exist_ok=True)
    try:
        os.remove(_ERR)
    except OSError:
        pass
    prof = cProfile.Profile()
    exit_code = 0
    try:
        prof.enable()
        # `python main.py` 와 맞춤: argv0 = main.py
        _rest = [x for x in sys.argv[1:] if x]
        sys.argv = [_MAIN] + _rest
        runpy.run_path(_MAIN, run_name="__main__")
    except SystemExit as e:
        c = e.code
        if c is None:
            exit_code = 0
        elif isinstance(c, int):
            exit_code = c
        else:
            exit_code = 1
    except KeyboardInterrupt:
        raise
    except Exception:
        print("[cprofile_pipela_driver] run_path failed — see error file or stderr", file=sys.stderr)
        traceback.print_exc()
        with open(_ERR, "w", encoding="utf-8", errors="replace") as ef:
            ef.write("run_path / main failed (before dump_stats):\n")
            ef.write(traceback.format_exc())
        exit_code = 1
    finally:
        try:
            prof.disable()
        except Exception:  # noqa: BLE001
            with open(_ERR, "a" if os.path.isfile(_ERR) else "w", encoding="utf-8", errors="replace") as ef:
                ef.write("\n\nprof.disable failed:\n")
                ef.write(traceback.format_exc())
            exit_code = 1
        try:
            prof.dump_stats(_PENDING)
        except Exception:  # noqa: BLE001
            with open(_ERR, "a" if os.path.isfile(_ERR) else "w", encoding="utf-8", errors="replace") as ef:
                if not os.path.isfile(_ERR) or os.path.getsize(_ERR) < 1:
                    ef.write("dump_stats failed:\n")
                else:
                    ef.write("\n\ndump_stats failed:\n")
                ef.write(traceback.format_exc())
            return 1 if exit_code == 0 else exit_code
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
