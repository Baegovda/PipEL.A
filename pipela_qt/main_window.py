from __future__ import annotations

from PyQt6.QtGui import QColor

from pipela_qt import theme as T
from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.ui_adaptive import set_root_font_pt

# 설정 허브 탭 순서·id — `control_main.PipelaQtMainWindow` 설정 스택과 동기.
# 본문은 2열 그리드, «업데이트」「테서렉트 설치법」은 스크롤 영역 맨 아래 가로 1:1.
HUB_MAIN_ENTRIES: tuple[tuple[str, str], ...] = (
    ("lc", "LeftClick 설정"),
    ("ft", "Flame Trigger 설정"),
    ("rl", "Reload 설정"),
    ("ride", "Ride 설정"),
    ("hp", "HP Refill 설정"),
    ("ammo", "Ammo Restock 설정"),
    ("merc", "Call Merc 설정"),
    ("sg", "Intro Skip 설정"),
    ("iface", "인터페이스"),
    ("console", "터미널"),
)
HUB_FOOTER_ENTRIES: tuple[tuple[str, str], ...] = (
    ("update", "업데이트"),
    ("tesseract", "테서렉트 설치법"),
)
HUB_ENTRIES: tuple[tuple[str, str], ...] = HUB_MAIN_ENTRIES + HUB_FOOTER_ENTRIES


def apply_dark_palette(app) -> None:
    app.setStyle("Fusion")
    pal = app.palette()
    pal.setColor(pal.ColorRole.Window, QColor(T.WINDOW_BG))
    pal.setColor(pal.ColorRole.WindowText, QColor(T.FG))
    pal.setColor(pal.ColorRole.Base, QColor(T.PANEL_BG))
    pal.setColor(pal.ColorRole.AlternateBase, QColor(T.CARD_BG))
    pal.setColor(pal.ColorRole.Text, QColor(T.FG))
    pal.setColor(pal.ColorRole.Button, QColor(T.BTN_BG))
    pal.setColor(pal.ColorRole.ButtonText, QColor(T.FG))
    pal.setColor(pal.ColorRole.Highlight, QColor(T.ACCENT))
    pal.setColor(pal.ColorRole.HighlightedText, QColor(T.FG))
    pal.setColor(pal.ColorRole.Link, QColor(T.ACCENT))
    app.setPalette(pal)


def configure_app(app, *, ui_font_pt: int | None = None) -> None:
    pt = 11 if ui_font_pt is None else max(8, min(24, int(ui_font_pt)))
    set_root_font_pt(float(pt))
    apply_dark_palette(app)
    app.setFont(app_default_qfont(pt))
    _prev = (app.styleSheet() or "").strip()
    _g = T.global_interaction_stylesheet().strip()
    app.setStyleSheet(f"{_prev}\n{_g}" if _prev else _g)
