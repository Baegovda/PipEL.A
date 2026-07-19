"""터미널 로그 한 줄 → HTML (`[기능명]` → 대표 아이콘 img)."""

from __future__ import annotations

import base64
import html
import os
import re
from typing import Pattern

from PyQt6.QtCore import QByteArray, QBuffer, Qt, QUrl
from PyQt6.QtGui import QColor, QImage, QPainter

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

# QTextEdit HTML 은 `<img opacity>` 를 거의 무시함 — 픽셀 합성 후 data URL 로 페이드.
_ICON_FADE_CACHE: dict[tuple[str, int, int], str] = {}
_ICON_FADE_CACHE_MAX = 480


def _terminal_icon_faded_data_url(ipath: str, icon_px: int, opacity: float) -> str | None:
    """로컬 PNG 를 `TERMINAL_BG` 위에 그린 뒤 전체를 ``opacity`` 만큼만 남긴 PNG data URL."""
    op = max(0.0, min(1.0, float(opacity)))
    norm = os.path.normpath(os.path.abspath(ipath))
    q = int(round(op * 32))
    key = (norm, int(icon_px), q)
    hit = _ICON_FADE_CACHE.get(key)
    if hit is not None:
        return hit

    src = QImage(norm)
    if src.isNull():
        return None
    ip = max(4, int(icon_px))
    src = src.scaled(
        ip,
        ip,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    w, h = src.width(), src.height()
    out = QImage(ip, ip, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(QColor(T.TERMINAL_BG))
    p = QPainter(out)
    try:
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        p.setOpacity(op)
        p.drawImage((ip - w) // 2, (ip - h) // 2, src)
    finally:
        p.end()

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    if not out.save(buf, "PNG"):
        return None
    url = "data:image/png;base64," + base64.standard_b64encode(ba.data()).decode("ascii")
    if len(_ICON_FADE_CACHE) >= _ICON_FADE_CACHE_MAX:
        _ICON_FADE_CACHE.clear()
    _ICON_FADE_CACHE[key] = url
    return url


def _lerp_hex(ca: str, cb: str, t: float) -> str:
    t = max(0.0, min(1.0, float(t)))

    def _parse(h: str) -> tuple[int, int, int]:
        h = h.strip().lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    ra, ga, ba = _parse(ca)
    rb, gb, bb = _parse(cb)
    r = int(ra + (rb - ra) * t + 0.5)
    g = int(ga + (gb - ga) * t + 0.5)
    b = int(ba + (bb - ba) * t + 0.5)
    return f"#{r:02x}{g:02x}{b:02x}"


def terminal_time_color_for_age(age_sec: float) -> str:
    """로그 줄이 찍힌 뒤 경과(초) → 시간 접두 `#RRGGBB`. 최신=밝은 민트, 오래될수록 황록→모래→회녹."""
    a = max(0.0, float(age_sec))
    if a <= 30.0:
        return _lerp_hex("#8ef5c4", "#cfe89a", a / 30.0)
    if a <= 120.0:
        return _lerp_hex("#cfe89a", "#e8c86e", (a - 30.0) / 90.0)
    if a <= 600.0:
        return _lerp_hex("#e8c86e", "#d4a574", (a - 120.0) / 480.0)
    u = min(1.0, (a - 600.0) / 3000.0)
    return _lerp_hex("#d4a574", "#6f8a7e", u)

# 괄호 안 문자열은 `main.py` 의 `_LOG_*` (`_LOG_RELOAD` 등) 와 동기화할 것.
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
    # main.py 워커 루프 `_LOG_*` 한글 접두
    "리로드": UI_ICON_RELOAD_PATH,
    "용병호출": UI_ICON_MERC_PATH,
    "탄약보급": UI_ICON_AMMO_PATH,
    "게임시작": START_GAME_IMAGE_PATH,
    "HP회복": UI_ICON_HP_REFILL_PATH,
    "플레임트리거": UI_ICON_FLAME_PATH,
    "좌클릭자동": MOVE_ICON_PATH,
    "우클릭홀드": FIRE_ICON_PATH,
}


def _path_if_file(p: str) -> str | None:
    if p and os.path.isfile(p):
        return p
    return None


def bracket_tag_to_icon_path(tag: str) -> str | None:
    """Map ``[...]`` tag text → bundled PNG path under ``assets/``."""
    t = tag.strip()
    tl = t.lower()
    if t in _EXACT_TAG_ICON:
        return _path_if_file(_EXACT_TAG_ICON[t])
    if "kill" in tl and "counter" in tl:
        return _path_if_file(UI_ICON_KILL_COUNTER_PATH)
    if tl.startswith("reload") or "nobullet" in tl or "vault" in tl or "리로드" in t:
        return _path_if_file(UI_ICON_RELOAD_PATH)
    if "hp" in tl and ("refill" in tl or "회복" in t):
        return _path_if_file(UI_ICON_HP_REFILL_PATH)
    if "ammo" in tl or "탄약" in t or "구매" in t or "인벤" in t or "은행" in t:
        return _path_if_file(UI_ICON_AMMO_PATH)
    if "merc" in tl or "용병" in t or "호출" in t or "계약" in t or "닫기" in t:
        return _path_if_file(UI_ICON_MERC_PATH)
    if "ride" in tl:
        return _path_if_file(CURSOR_RIDE_ICON_PATH)
    if "flame" in tl or "플레임" in t:
        return _path_if_file(UI_ICON_FLAME_PATH)
    if ("right" in tl and "hold" in tl) or "우클릭" in t:
        return _path_if_file(FIRE_ICON_PATH)
    if ("left" in tl and "click" in tl) or "좌클릭" in t:
        return _path_if_file(MOVE_ICON_PATH)
    if "start" in tl or "intro" in tl or "accept" in tl or "런처" in t or "게임시작" in t:
        return _path_if_file(START_GAME_IMAGE_PATH)
    if "ocr" in tl:
        return _path_if_file(UI_ICON_SETTINGS_PATH)
    if "템플릿" in t or "감지" in t:
        return _path_if_file(UI_ICON_RELOAD_PATH)
    if "캡처" in t:
        return _path_if_file(UI_ICON_SETTINGS_PATH)
    return None


def _fade_toward_terminal_bg(hex_fg: str, visibility: float) -> str:
    """`QTextDocument` HTML 은 `opacity` 를 자주 무시함 — 배경으로 색 보간으로 페이드."""
    v = max(0.0, min(1.0, float(visibility)))
    return _lerp_hex(T.TERMINAL_BG, hex_fg, v)


def format_terminal_log_line_html(
    time_prefix: str,
    raw_line: str,
    *,
    icon_px: int,
    time_age_sec: float | None = None,
    line_opacity: float | None = None,
) -> str:
    """시간 접두(절대 시각 또는 `line_mono` 기준 경과) + 본문 한 줄 → HTML (줄 끝 `<br/>` 없음).

    ``time_age_sec`` 가 있으면 접두 색만 줄 나이에 따라 그라데이션; 본문은 ``TERMINAL_FG`` 유지.
    """
    fg = T.TERMINAL_FG
    tp = time_prefix or ""
    op = (
        max(0.0, min(1.0, float(line_opacity)))
        if line_opacity is not None
        else None
    )
    if time_age_sec is not None:
        tcol = terminal_time_color_for_age(time_age_sec)
        if op is not None:
            tcol = _fade_toward_terminal_bg(tcol, op)
        time_html = f'<span style="color:{tcol};">{html.escape(tp)}</span>'
    else:
        if op is not None:
            tcol = _fade_toward_terminal_bg(fg, op * 0.88)
            time_html = f'<span style="color:{tcol};">{html.escape(tp)}</span>'
        else:
            time_html = (
                f'<span style="color:{fg}; opacity:0.88;">{html.escape(tp)}</span>'
            )
    body_fg = _fade_toward_terminal_bg(fg, op) if op is not None else fg
    mr = max(4, icon_px // 4)
    if not raw_line:
        out = time_html
    else:
        m = _BRACKET_HEAD.match(raw_line)
        if not m:
            out = time_html + f'<span style="color:{body_fg};">{html.escape(raw_line)}</span>'
        else:
            tag, rest = m.group(1), m.group(2)
            ipath = bracket_tag_to_icon_path(tag)
            if ipath:
                use_fade = op is not None and op < 0.999
                if use_fade:
                    durl = _terminal_icon_faded_data_url(ipath, icon_px, float(op) if op is not None else 1.0)
                    if durl:
                        img = (
                            f'<img src="{html.escape(durl)}" width="{int(icon_px)}" height="{int(icon_px)}" '
                            f'style="vertical-align:middle; margin-right:{mr}px;" />'
                        )
                    else:
                        img = (
                            f'<span style="color:{body_fg}; display:inline-block; width:{int(icon_px)}px; '
                            f"height:{int(icon_px)}px;\"></span>"
                        )
                else:
                    url = QUrl.fromLocalFile(
                        os.path.normpath(os.path.abspath(ipath)),
                    ).toString()
                    img = (
                        f'<img src="{html.escape(url)}" width="{int(icon_px)}" height="{int(icon_px)}" '
                        f'style="vertical-align:middle; margin-right:{mr}px;" />'
                    )
            else:
                img = f'<span style="color:{body_fg};">[{html.escape(tag)}]</span>'
            rest_html = f'<span style="color:{body_fg};">{html.escape(rest)}</span>'
            out = time_html + img + " " + rest_html
    return out
