"""터미널 로그 줄 접두사 — 절대(월-일 시:분:초) / 상대(줄이 찍힌 뒤 경과·나이)."""

from __future__ import annotations

import time
from typing import Any

from pipela_core.console_log_constants import (
    CONSOLE_LOG_TIME_MODE_ABSOLUTE,
    CONSOLE_LOG_TIME_MODE_RELATIVE,
)


def _format_rel_elapsed_sec(dt: float) -> str:
    """monotonic 차이 dt(초) → `[Ns]` / `[Nm…]` 등(상대=줄·나이, 절대와 동일 괄호 형식)."""
    dt = max(0.0, float(dt))
    if dt < 60.0:
        return f"[{int(dt)}s]"
    if dt < 3600.0:
        m = int(dt // 60)
        s = int(dt % 60)
        return f"[{m}m{s:02d}s]"
    if dt < 86400.0:
        h = int(dt // 3600)
        mi = int((dt % 3600) // 60)
        return f"[{h}h{mi:02d}m]"
    d = int(dt // 86400)
    h = int((dt % 86400) // 3600)
    return f"[{d}d{h}h]"


def _absolute_bracket_now() -> str:
    return "[" + time.strftime("%m-%d %H:%M:%S", time.localtime()) + "]"


def _absolute_bracket_at(wall_t: float) -> str:
    return "[" + time.strftime("%m-%d %H:%M:%S", time.localtime(wall_t)) + "]"


def format_console_log_prefix(
    m: Any,
    *,
    line_mono: float | None = None,
    rel_mono0: float | None = None,
) -> str:
    """한 줄 앞에 붙일 `[…] ` (끝에 공백). 상대 모드: 그 줄이 찍힌 monotonic 기준 '지금까지 경과(나이)'."""
    mode = getattr(
        m,
        "console_log_time_display_mode",
        CONSOLE_LOG_TIME_MODE_ABSOLUTE,
    )
    if mode not in (CONSOLE_LOG_TIME_MODE_ABSOLUTE, CONSOLE_LOG_TIME_MODE_RELATIVE):
        mode = CONSOLE_LOG_TIME_MODE_ABSOLUTE
    if mode == CONSOLE_LOG_TIME_MODE_ABSOLUTE:
        return _absolute_bracket_now() + " "

    ref = line_mono if line_mono is not None else rel_mono0
    if ref is None:
        ref = time.monotonic()
    now = time.monotonic()
    dt = max(0.0, now - float(ref))
    return _format_rel_elapsed_sec(dt) + " "


def format_terminal_log_stored_prefix(
    m: Any,
    *,
    wall_time: float,
    line_monotonic: float,
) -> str:
    """절대/상대 전환·1초 재빌드. 상대: ``line_monotonic`` 이후 흐른 시간(지금-줄시각)."""
    mode = getattr(
        m,
        "console_log_time_display_mode",
        CONSOLE_LOG_TIME_MODE_ABSOLUTE,
    )
    if mode not in (CONSOLE_LOG_TIME_MODE_ABSOLUTE, CONSOLE_LOG_TIME_MODE_RELATIVE):
        mode = CONSOLE_LOG_TIME_MODE_ABSOLUTE
    if mode == CONSOLE_LOG_TIME_MODE_ABSOLUTE:
        return _absolute_bracket_at(wall_time) + " "
    now = time.monotonic()
    dt = max(0.0, now - float(line_monotonic))
    return _format_rel_elapsed_sec(dt) + " "
