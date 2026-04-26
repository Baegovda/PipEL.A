"""터미널 로그 한 줄 → HTML (`[기능명]` → 대표 아이콘 img)."""

from __future__ import annotations

import html
import os
import re
from typing import Pattern

from PyQt6.QtCore import QUrl

from pipela_qt import theme as T
from pipela_core.paths import (
    CURSOR_RIDE_ICON_PATH,
    PIPELA_APP_ICON_PATH,
    FIRE_ICON_PATH,
    MOVE_ICON_PATH,
    START_GAME_IMAGE_PATH,
    UI_ICON_AMMO_PATH,
    UI_ICON_FLAME_PATH,
    UI_ICON_HP_REFILL_PATH,
    UI_ICON_KILL_COUNTER_PATH,
    UI_ICON_MERC_PATH,
    UI_ICON_RELOAD_PATH,
    UI_ICON_SETTINGS_PATH,
)
from pipela_core.version_info import PIPELA_APP_DISPLAY_NAME

_BRACKET_HEAD: Pattern[str] = re.compile(r"^\[([^\]]+)\]\s*(.*)\s*$", re.DOTALL)

_EXACT_TAG_ICON: dict[str, str] = {
    "LeftClick": MOVE_ICON_PATH,
    "RightHold": FIRE_ICON_PATH,
    "Flame Trigger": UI_ICON_FLAME_PATH,
    "Reload": UI_ICON_RELOAD_PATH,
    "HP Refill": UI_ICON_HP_REFILL_PATH,
    "Ammo Restock": UI_ICON_AMMO_PATH,
    "Ride": CURSOR_RIDE_ICON_PATH,
    "Kill Counter": UI_ICON_KILL_COUNTER_PATH,
    "START GAME": START_GAME_IMAGE_PATH,
    "Pipela": PIPELA_APP_ICON_PATH,
    PIPELA_APP_DISPLAY_NAME: PIPELA_APP_ICON_PATH,
    "템플릿 감지": UI_ICON_RELOAD_PATH,
    "캡처": UI_ICON_SETTINGS_PATH,
}


def _path_if_file(p: str) -> str | None:
    if p and os.path.isfile(p):
        return p
    return None


def bracket_tag_to_icon_path(tag: str) -> str | None:
    """`[...]` 안의 문자열 → `icon/`·`templates/` PNG 경로."""
    t = tag.strip()
    tl = t.lower()
    if t in _EXACT_TAG_ICON:
        return _path_if_file(_EXACT_TAG_ICON[t])
    if "kill" in tl and "counter" in tl:
        return _path_if_file(UI_ICON_KILL_COUNTER_PATH)
    if tl.startswith("reload") or "nobullet" in tl or "vault" in tl:
        return _path_if_file(UI_ICON_RELOAD_PATH)
    if "hp" in tl and "refill" in tl:
        return _path_if_file(UI_ICON_HP_REFILL_PATH)
    if "ammo" in tl or "구매" in t or "인벤" in t or "은행" in t:
        return _path_if_file(UI_ICON_AMMO_PATH)
    if "merc" in tl or "용병" in t or "호출" in t or "계약" in t or "닫기" in t:
        return _path_if_file(UI_ICON_MERC_PATH)
    if "ride" in tl:
        return _path_if_file(CURSOR_RIDE_ICON_PATH)
    if "flame" in tl:
        return _path_if_file(UI_ICON_FLAME_PATH)
    if "right" in tl and "hold" in tl:
        return _path_if_file(FIRE_ICON_PATH)
    if "left" in tl and "click" in tl:
        return _path_if_file(MOVE_ICON_PATH)
    if "start" in tl or "intro" in tl or "accept" in tl or "런처" in t:
        return _path_if_file(START_GAME_IMAGE_PATH)
    if "ocr" in tl:
        return _path_if_file(UI_ICON_SETTINGS_PATH)
    if "템플릿" in t or "감지" in t:
        return _path_if_file(UI_ICON_RELOAD_PATH)
    if "캡처" in t:
        return _path_if_file(UI_ICON_SETTINGS_PATH)
    return None


def format_terminal_log_line_html(
    time_prefix: str,
    raw_line: str,
    *,
    icon_px: int,
) -> str:
    """시간 접두(절대 시각 또는 `line_mono` 기준 경과) + 본문 한 줄 → HTML (줄 끝 `<br/>` 없음)."""
    fg = T.TERMINAL_FG
    tp = time_prefix or ""
    time_html = (
        f'<span style="color:{fg}; opacity:0.88;">{html.escape(tp)}</span>'
    )
    if not raw_line:
        return time_html
    m = _BRACKET_HEAD.match(raw_line)
    if not m:
        return time_html + f'<span style="color:{fg};">{html.escape(raw_line)}</span>'
    tag, rest = m.group(1), m.group(2)
    ipath = bracket_tag_to_icon_path(tag)
    if ipath:
        url = QUrl.fromLocalFile(os.path.normpath(os.path.abspath(ipath))).toString()
        img = (
            f'<img src="{html.escape(url)}" width="{int(icon_px)}" height="{int(icon_px)}" '
            f'style="vertical-align:middle; margin-right:{max(4, icon_px // 4)}px;" />'
        )
    else:
        img = f'<span style="color:{fg};">[{html.escape(tag)}]</span>'
    rest_html = f'<span style="color:{fg};">{html.escape(rest)}</span>'
    return time_html + img + " " + rest_html
