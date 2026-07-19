"""킬 카운터 등급 호칭별 전경색 — 등급 구간 표·패널 «다음 구간까지» 라벨 공통."""

from __future__ import annotations

import re
from typing import Final

_TIER_TITLE_PREFIX_RE: Final[re.Pattern[str]] = re.compile(r"^(.+?)(\d+)$")

# WoW 품질 느낌, 어두운 패널 기준 가독색.
KILL_COUNTER_TIER_HONORIFIC_FG_HEX: dict[str, str] = {
    "견습생": "#9ca3af",
    "초보자": "#e5e7eb",
    "숙련자": "#4ade80",
    "전문가": "#60a5fa",
    "장인": "#c084fc",
    "달인": "#e879f9",
    "대가": "#fb923c",
    "명인": "#fde047",
    "명장": "#e07c4c",
    "거장": "#ea580c",
    "귀인": "#22d3ee",
    "초인": "#f87171",
}


def kill_counter_honorific_key(title: str) -> str:
    t = (title or "").strip()
    m = _TIER_TITLE_PREFIX_RE.match(t)
    if m:
        return m.group(1)
    return t


def kill_counter_tier_fg_hex_for_rank_title(title: str) -> str | None:
    """'견습생3' 형태 → 호칭 그룹 색 hex. 매칭 없으면 None."""
    k = kill_counter_honorific_key(title)
    return KILL_COUNTER_TIER_HONORIFIC_FG_HEX.get(k)
