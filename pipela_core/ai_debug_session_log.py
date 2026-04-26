"""AI·트러블슈팅용 세션 디버그 로그 — 터미널 출력 복제 + 구조화 이벤트 + 주기 스냅샷.

로그 디렉터리: ``%LOCALAPPDATA%\\Pipela\\ai_debug\\`` (``session_*.log``, ``latest.log``).

환경 변수 ``PIPELA_AI_DEBUG=0`` 이면 비활성(기본: 켜짐).
"""

from __future__ import annotations

import atexit
import json
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, IO, TextIO

_lock = threading.RLock()
_file: IO[str] | None = None
_log_path: Path | None = None
_tee_saved: TextIO | None = None
_stdio_tee_installed = False
_enabled = True
_bytes_written = 0
_MAX_BYTES_BEFORE_ROTATE = 16 * 1024 * 1024


def get_session_log_path() -> Path | None:
    return _log_path


def is_ai_debug_enabled() -> bool:
    try:
        return os.environ.get("PIPELA_AI_DEBUG", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )
    except Exception:
        return True


def _local_data_dir() -> Path:
    la = os.environ.get("LOCALAPPDATA") or os.environ.get("HOME") or ""
    if la:
        return Path(la) / "Pipela" / "ai_debug"
    return Path.home() / ".pipela" / "ai_debug"


def _write_file_raw(s: str) -> None:
    global _bytes_written
    if _file is None or not s:
        return
    with _lock:
        try:
            _file.write(s)
            _file.flush()
            _bytes_written += len(s.encode("utf-8", errors="replace"))
        except Exception:
            pass


def _maybe_rotate() -> None:
    global _file, _bytes_written, _log_path
    if _file is None or _bytes_written < _MAX_BYTES_BEFORE_ROTATE:
        return
    try:
        _file.close()
    except Exception:
        pass
    _file = None
    _bytes_written = 0
    stamp = time.strftime("%Y%m%d_%H%M%S")
    _log_path = _local_data_dir() / f"session_{stamp}.log"
    _log_path.parent.mkdir(parents=True, exist_ok=True)
    _file = open(_log_path, "a", encoding="utf-8", buffering=1)
    _write_file_raw(
        f"\n\n### ROTATE size>=16MB t={time.time():.3f} new={_log_path.name}\n",
    )
    _write_readme_if_needed(_log_path.parent)


def _write_readme_if_needed(d: Path) -> None:
    p = d / "README_AI_DEBUG.txt"
    if p.is_file() and p.stat().st_size > 80:
        return
    try:
        p.write_text(
            "\n".join(
                [
                    "Pipela — AI / support debug log",
                    "",
                    "Files:",
                    "  session_YYYYMMDD_HHMMSS.log — full session mirror of console + structured events",
                    "  latest.log — copy of the active session file",
                    "",
                    "Contains:",
                    "  - All stdout/stderr (including Qt terminal decoration after UI starts)",
                    "  - Python unhandled exceptions (traceback)",
                    "  - Threading exception hook (Python 3.8+)",
                    "  - Periodic JSON heartbeats: game HWND, feature flags, window sizes (if Qt running)",
                    "  - Lines between ###AI JSON and ###END — machine-readable for tools",
                    "",
                    "Disable: set environment variable PIPELA_AI_DEBUG=0",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def _write_header() -> None:
    _write_file_raw(
        "\n".join(
            [
                "### Pipela AI debug session",
                f"wall_time={time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())}",
                f"monotonic_start={time.monotonic():.6f}",
                f"pid={os.getpid()}",
                f"python={sys.version.splitlines()[0]}",
                f"platform={sys.platform}",
                f"executable={sys.executable}",
                f"argv={sys.argv!r}",
                f"cwd={os.getcwd()}",
                "",
            ]
        )
    )
    try:
        for k in (
            "PIPELA_AI_DEBUG",
            "PIPELA_QUIET_MACRO",
            "PIPELA_QUIET",
        ):
            if k in os.environ:
                _write_file_raw(f"env {k}={os.environ[k]!r}\n")
    except Exception:
        pass
    _write_file_raw("\n### CONSOLE MIRROR (stdout/stderr via tee / Qt bridge)\n")


def log_ai_json_event(kind: str, data: dict[str, Any]) -> None:
    """구조화 이벤트 — AI가 grep/JSON으로 읽기 쉬움."""
    if not _enabled or _file is None:
        return
    try:
        payload = {
            "t_wall": time.time(),
            "t_mono": time.monotonic(),
            "thread": threading.current_thread().name,
            "kind": kind,
            "data": data,
        }
        txt = json.dumps(payload, ensure_ascii=False, default=str)
        _write_file_raw(f"###AI JSON\n{txt}\n###END\n")
        _maybe_rotate()
    except Exception:
        pass


def log_exception(context: str, exc: BaseException) -> None:
    if not _enabled or _file is None:
        return
    try:
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        log_ai_json_event(
            "exception",
            {"context": context, "type": type(exc).__name__, "str": str(exc), "traceback": tb},
        )
        _write_file_raw(f"\n--- Exception ({context}) ---\n{tb}\n---\n")
    except Exception:
        pass


_old_excepthook: Callable[..., Any] | None = None


def _global_excepthook(etype, value, tb) -> None:
    try:
        log_exception("sys.excepthook", value if isinstance(value, BaseException) else Exception(str(value)))
    except Exception:
        pass
    if _old_excepthook is not None:
        _old_excepthook(etype, value, tb)
    else:
        sys.__excepthook__(etype, value, tb)


_threading_hook_installed = False


def _install_threading_excepthook() -> None:
    global _threading_hook_installed
    if _threading_hook_installed:
        return
    try:
        std = getattr(threading, "excepthook", None)
    except Exception:
        std = None
    if std is None or not callable(std):
        return

    def _hook(args) -> None:  # type: ignore[no-untyped-def]
        try:
            log_exception(
                "threading",
                args.exc_value
                if getattr(args, "exc_value", None) is not None
                else RuntimeError("threading excepthook"),
            )
        except Exception:
            pass
        try:
            std(args)
        except Exception:
            pass

    try:
        threading.excepthook = _hook  # type: ignore[assignment]
        _threading_hook_installed = True
    except Exception:
        pass


class _DebugTee:
    """``sys.stdout``/``sys.stderr`` 래핑: 콘솔로 그대로 보내며 파일에도 동일 바이트 기록."""

    def __init__(self, real: TextIO, *, name: str) -> None:
        self._real = real
        self._name = name

    def write(self, s) -> int:
        if not isinstance(s, str):
            s = str(s)
        n = len(s)
        if n and _enabled:
            _write_file_raw(s)
            _maybe_rotate()
        try:
            return self._real.write(s)
        except Exception:
            return n

    def flush(self) -> None:
        try:
            self._real.flush()
        except Exception:
            pass
        try:
            if _file is not None:
                _file.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        try:
            return self._real.isatty()
        except Exception:
            return False

    @property
    def encoding(self) -> str:  # noqa: D401
        return getattr(self._real, "encoding", "utf-8") or "utf-8"


def install_stdio_tee() -> None:
    """``main_qt`` 최상단에서 호출 — ``StreamBridge`` 전에 콘솔·파일 이중 기록."""
    global _file, _log_path, _tee_saved, _enabled, _old_excepthook, _bytes_written, _stdio_tee_installed
    if _stdio_tee_installed:
        return
    if not is_ai_debug_enabled():
        _enabled = False
        return
    _stdio_tee_installed = True
    _enabled = True
    d = _local_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    _log_path = d / f"session_{stamp}.log"
    _write_readme_if_needed(d)
    try:
        _file = open(_log_path, "a", encoding="utf-8", buffering=1)
    except OSError:
        _enabled = False
        _file = None
        return
    _bytes_written = 0
    _write_header()
    # latest.log 복제
    try:
        import shutil

        latest = d / "latest.log"
        if latest.exists():
            try:
                latest.unlink()
            except OSError:
                pass
        shutil.copy2(_log_path, latest)
    except Exception:
        pass

    _tee_saved = sys.stdout
    try:
        sys.stdout = _DebugTee(_tee_saved, name="stdout")
    except Exception:
        _file = None
        _enabled = False
        return
    try:
        sys.stderr = _DebugTee(sys.__stderr__, name="stderr")
    except Exception:
        pass

    global _old_excepthook
    _old_excepthook = sys.excepthook
    sys.excepthook = _global_excepthook
    _install_threading_excepthook()

    def _close_log() -> None:
        with _lock:
            try:
                if _file is not None:
                    _write_file_raw("\n### atexit / process end\n")
                    _file.close()
            except Exception:
                pass
        try:
            if _log_path is not None and _log_path.is_file():
                import shutil

                shutil.copy2(_log_path, _log_path.parent / "latest.log")
        except Exception:
            pass

    atexit.register(_close_log)
    log_ai_json_event("session_start", {"log_file": str(_log_path), "local_app_data": str(d)})


def build_pipela_mod_snapshot(m: Any) -> dict[str, Any]:
    """`pipela_mod`(main)에서 AI가 참고할 런타임 스냅샷(가능한 한 많이)."""
    out: dict[str, Any] = {"module": "main", "import_name": getattr(m, "__name__", None)}
    keys = (
        "running",
        "target_hwnd",
        "reload_active",
        "ride_feature_enabled",
        "hp_refill_feature_enabled",
        "flame_trigger_feature_enabled",
        "kill_counter_enabled",
        "ammo_restock_active",
        "call_merc_active",
        "left_click_feature_enabled",
        "select_mode",
        "nobullet_detected",
        "pipela_qt_control_win_hwnd",
        "PIPELA_APP_VERSION",
        "PIPELA_STRIP_DISPLAY_VERSION",
    )
    for k in keys:
        try:
            out[k] = getattr(m, k, None)
        except Exception as e:  # noqa: BLE001
            out[k] = f"<err {e!r}>"
    # 창 크기
    th = out.get("target_hwnd")
    if th:
        try:
            sz = m.get_window_size(th)
            out["target_client_size"] = sz
        except Exception:
            out["target_client_size"] = None
    for k in (
        "kill_counter_last_poll_detail",
        "kill_counter_last_progress",
        "call_merc_loop_count",
        "reload_success_count",
        "ammo_restock_loop_count",
    ):
        try:
            out[k] = getattr(m, k, None)
        except Exception as e:  # noqa: BLE001
            out[k] = f"<err {e!r}>"
    return out


def log_heartbeat_pipela_mod(m: Any) -> None:
    log_ai_json_event("heartbeat", build_pipela_mod_snapshot(m))
