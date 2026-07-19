"""클라이언트 페이즈 전환·도킹 디버그 — UI 터미널이 아닌 실제 stderr.

복붙 디버그: ``set PIPELA_DEBUG_CLIENT_TRANSITION=1`` 후 ``python main.py`` — stderr에만 상세 로그가 나갑니다.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import traceback
from contextlib import contextmanager, nullcontext


def _truthy(raw: str) -> bool:
    return raw.strip().lower() in ("1", "true", "yes", "on", "y")


def _falsy_explicit(raw: str) -> bool:
    return raw.strip().lower() in ("0", "false", "no", "off", "n")


def _parse_enabled() -> bool:
    k1 = os.environ.get("PIPELA_DEBUG_CLIENT_TRANSITION", "").strip()
    k2 = os.environ.get("PIPELA_DEBUG_CLIENT_DOCK", "").strip()
    if _falsy_explicit(k1) or _falsy_explicit(k2):
        return False
    if _truthy(k1) or _truthy(k2):
        return True
    return False


_ENABLED = _parse_enabled()


def is_enabled() -> bool:
    return bool(_ENABLED)


_logged_banner = False


def _emit_banner_once() -> None:
    global _logged_banner
    if _logged_banner or not _ENABLED:
        return
    _logged_banner = True
    try:
        sys.__stderr__.write(
            "[Pipela:CLIENT_TRANSITION] stderr 디버그 출력 ON. "
            "끄려면 PIPELA_DEBUG_CLIENT_TRANSITION=0 (또는 CLIENT_DOCK=0).\n",
        )
        sys.__stderr__.flush()
    except Exception:
        pass


def log(msg: str) -> None:
    if not _ENABLED:
        return
    _emit_banner_once()
    try:
        tid = threading.get_ident()
        sys.__stderr__.write(
            f"[Pipela:CLIENT_TRANSITION t={time.perf_counter():9.4f}s tid={tid}] {msg}\n",
        )
        sys.__stderr__.flush()
    except Exception:
        pass


def log_exc(where: str, exc: BaseException) -> None:
    if not _ENABLED:
        return
    try:
        log(f"EXCEPTION @ {where}: {exc!r}")
        sys.__stderr__.write(traceback.format_exc())
        sys.__stderr__.flush()
    except Exception:
        pass


@contextmanager
def _span_traced(label: str):
    t0 = time.perf_counter()
    log(f"--> {label}")
    try:
        yield
    except BaseException as e:
        log(f"!! span fail {label!r}: {e!r}")
        try:
            sys.__stderr__.write(traceback.format_exc())
            sys.__stderr__.flush()
        except Exception:
            pass
        raise
    finally:
        log(f"<-- {label} dt_ms={(time.perf_counter() - t0) * 1000.0:.2f}")


def span(label: str):
    """OFF일 때는 nullcontext — I/O·타이밍 없음, CM 오버헤드만."""
    if not _ENABLED:
        return nullcontext()
    return _span_traced(label)
