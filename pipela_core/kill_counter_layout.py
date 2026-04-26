"""킬 통계 패널 행 순서·랩 일시정지 구간 — 레지/UI와 무관한 순수 데이터·정규화."""

from __future__ import annotations

from typing import Any

KILL_COUNTER_STAT_ROW_KEYS_DEFAULT: tuple[str, ...] = (
    "1h",
    "6h",
    "24h",
    "today",
    "week",
    "month",
    "dod",
)
# 예전 행 키 `kph`(시간당 평균 표시) → `6h` 롤링 합으로 대체됨. 저장된 순서 JSON 호환.
KILL_COUNTER_STAT_ROW_LEGACY_KEY_MAP: dict[str, str] = {"kph": "6h", "manual": "lap"}
# 「최근」롤링 행 — 짧은 구간부터(1h→6h→24h) 항상 앞에 붙임
KILL_COUNTER_STAT_ROLLING_KEYS_TIME_ORDER: tuple[str, ...] = ("1h", "6h", "24h")


def kill_counter_stat_row_order_normalize(order: Any) -> list[str]:
    """킬 통계 행 키 순서: 유효 키만 유지, 누락분은 기본 뒤에 붙임.
    롤링(1h·6h·24h)은 짧은 시간창 순으로 목록 맨 앞에 고정."""
    default = list(KILL_COUNTER_STAT_ROW_KEYS_DEFAULT)
    if not isinstance(order, (list, tuple)):
        return default[:]
    seen: set[str] = set()
    out: list[str] = []
    for k in order:
        if isinstance(k, str):
            k = KILL_COUNTER_STAT_ROW_LEGACY_KEY_MAP.get(k, k)
        if k in KILL_COUNTER_STAT_ROW_KEYS_DEFAULT and k not in seen:
            out.append(k)
            seen.add(k)
    for k in default:
        if k not in seen:
            out.append(k)
    rk_set = set(KILL_COUNTER_STAT_ROLLING_KEYS_TIME_ORDER)
    head = [k for k in KILL_COUNTER_STAT_ROLLING_KEYS_TIME_ORDER if k in out]
    tail = [k for k in out if k not in rk_set]
    return head + tail


def kill_counter_lap_pause_segments_normalize(segments: Any) -> list[list[Any]]:
    """[[pause_start, pause_end|None], ...] 검증. 잘못된 항목은 제거."""
    if not segments:
        return []
    out: list[list[Any]] = []
    try:
        for item in segments:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                continue
            p = float(item[0])
            r = item[1]
            if r is not None:
                r = float(r)
                if r < p:
                    continue
            out.append([p, r])
    except (TypeError, ValueError):
        return []
    return out
