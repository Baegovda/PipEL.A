"""UI 글꼴 — Qt·`pipela_mod`·스타일시트 공통.

정책(AGENTS.md «Typography»): 라틴/영문은 모노스페이스, 한글은 맑은 고딕(Malgun Gothic).
`FONT_QT_FAMILY_STACK` 순서대로 글리프를 찾으므로 ASCII는 앞선 모노 후보가,
한글은 Malgun Gothic(및 Gulim 등 폴백)이 쓰인다.
"""

from __future__ import annotations

FONT_FAMILY_KO = "Malgun Gothic"

# Windows에서 자주 쓰이는 모노스페이스(선호 순). 없으면 다음 후보로 넘어간다.
FONT_MONO_CANDIDATES: tuple[str, ...] = (
    "Cascadia Mono",
    "Cascadia Code",
    "JetBrains Mono",
    "Consolas",
)

FONT_UI_KO = FONT_FAMILY_KO
FONT_UI_MONO = FONT_MONO_CANDIDATES[0]
FONT_UI = FONT_UI_KO

FONT_QT_FAMILY_STACK: tuple[str, ...] = (
    *FONT_MONO_CANDIDATES,
    FONT_FAMILY_KO,
    "Gulim",
)


def qt_stylesheet_font_family() -> str:
    """Qt `font-family:` 값(속성명 제외)."""
    parts = [f"'{n}'" for n in FONT_QT_FAMILY_STACK]
    return ", ".join(parts) + ", monospace, sans-serif"
