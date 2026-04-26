# Pipela Qt UI — 차콜 베이스 + 청록·틸 액센트 (스트립·제어창 동일 계열)

from pipela_core.ui_fonts import qt_stylesheet_font_family
from pipela_qt.ui_adaptive import letter_spacing_qss, qss_pad_all, qss_pad_vh, scale_px, spt

# Qt stylesheet `font-family:` 값 — 영문 모노 + 한글 맑은 고딕 (AGENTS.md)
FONT_CSS_UI = qt_stylesheet_font_family()
# 전역 기본 QFont pt는 ``main_window.configure_app`` / ``qt_fonts.app_default_qfont`` 기본값(11pt).
# 패널·스트립의 ``font-size`` 는 본문 가독을 위해 기본 대비 한 단계 큰 pt 스케일을 쓴다.

# --- 상단 스트립(게임 타이틀 띠) 전용 ---
STRIP_BG = "#121417"
STRIP_BG_TOP = "#16191c"
STRIP_ACCENT = "#3DD4C9"
STRIP_FG = "#FFFFFF"
STRIP_FG_MUTED = "#8E9297"
STRIP_BORDER = "#2a2d32"
STRIP_BTN_HOVER = "rgba(61, 212, 201, 0.24)"
STRIP_BTN_HOVER_CLOSE = "rgba(248, 113, 113, 0.22)"
STRIP_RADIUS_BTN = "6px"

# --- 앱 전역(제어창·패널·허브) — 위와 정렬 ---
WINDOW_BG = STRIP_BG
PANEL_BG = "#1a1d22"
SURFACE = "#16191c"
CARD_BG = "#1e2228"
CARD_ACCENT = "#252a32"
CARD_HOVER = "#2a3038"

FG = STRIP_FG
FG_MUTED = STRIP_FG_MUTED
FG_DIM = "#6b7380"
HINT = FG_MUTED
DIVIDER = "#2f343c"

BTN_BG = "#2a3038"
BTN_HOVER = "#383f4d"
BTN_PRESSED = "#1f2329"
# 토글 ON — 진한 청록·틸 틴트
BTN_ON = "#132a2c"
BTN_ON_BORDER = "#0f9b8e"
# RightHold 등 «동작 중» 강조
BTN_EMIT_BG = "#1a3f3c"
BTN_EMIT_BORDER = STRIP_ACCENT
# 토글 ON / emit 상태에서 마우스 오버
BTN_ON_HOVER = "#1a3d42"
BTN_EMIT_HOVER = "#2a5f58"

BORDER = STRIP_BORDER
BORDER_HAIR = "#23262c"
ACCENT = STRIP_ACCENT
ACCENT_SOFT = "rgba(61, 212, 201, 0.15)"

# 킬 패널·상태 문구
STATUS_OK = "#e8eaed"
STATUS_WARN = "#d4c04a"
STATUS_ERR = "#ef6a5a"
METER_LABEL = "#8E9297"

# 터미널 탭(로그 뷰) — 어두운 배경 + 포스포 그린 계열
TERMINAL_BG = "#060908"
TERMINAL_FG = "#6bdc9b"
TERMINAL_BORDER = "#153028"
TERMINAL_SELECTION_BG = "rgba(61, 212, 201, 0.42)"
TERMINAL_SELECTION_FG = "#03120c"
TERMINAL_SCROLLTRACK = "#0a1210"
TERMINAL_SCROLLGRIP = "#2a5c48"
TERMINAL_SCROLLGRIP_HOVER = "#3a7f62"

RADIUS = "10px"
RADIUS_SM = "8px"
RADIUS_PILL = "999px"
TITLE_GRAD0 = STRIP_BG_TOP
TITLE_GRAD1 = STRIP_BG
TITLE_H = 42
TITLE_DRAG_BAR_H = 32

SHADOW = "0 0 0 1px rgba(0,0,0,0.35)"
DOCK_SIDE_PANEL_WIDTH = 400


def global_interaction_stylesheet() -> str:
    """QApplication·제어창 QSS 끝에 붙임 — QPushButton·QToolButton 공통 호버/눌림."""
    return f"""
QPushButton {{
  background-color: {BTN_BG};
  color: {FG};
  border: 1px solid {BORDER_HAIR};
  padding: {qss_pad_vh(9, 10)};
  border-radius: {RADIUS_SM};
  font-size: {spt(10)};
  letter-spacing: {letter_spacing_qss()};
  font-weight: 500;
}}
QPushButton:hover {{
  background-color: {BTN_HOVER};
  border: 1px solid {ACCENT};
  color: {FG};
}}
QPushButton:pressed {{
  background-color: {BTN_PRESSED};
  border-color: {BORDER_HAIR};
  color: {FG};
}}
QPushButton:disabled {{
  background-color: {PANEL_BG};
  color: {FG_DIM};
  border: 1px solid {BORDER_HAIR};
}}
QToolButton {{
  background: transparent;
  border: none;
  padding: {qss_pad_all(4)};
  border-radius: {RADIUS_SM};
}}
QToolButton:hover {{
  background-color: {ACCENT_SOFT};
}}
QToolButton:pressed {{
  background-color: {BTN_PRESSED};
}}
"""


def narrow_scrollbars_qss(*, scope_selector: str) -> str:
    """QScrollArea 내 얇은 스크롤바 — ``scope_selector`` 로 제한 (예: ``QMainWindow#pipelaFramelessMain``)."""
    w = max(4, int(scale_px(5)))
    r = max(2, int(scale_px(3)))
    edge = int(scale_px(3))
    hp = int(scale_px(2))
    mn = int(scale_px(20))
    sc = str(scope_selector).strip()
    return f"""
{sc} QScrollArea QScrollBar:vertical {{
  background: {SURFACE};
  width: {w}px;
  margin: {edge}px {edge}px {edge}px 0px;
  border: none;
  border-radius: {r}px;
}}
{sc} QScrollArea QScrollBar::handle:vertical {{
  background: {BORDER_HAIR};
  min-height: {mn}px;
  border-radius: {r}px;
  margin: {hp}px 1px;
}}
{sc} QScrollArea QScrollBar::handle:vertical:hover {{
  background: {BTN_HOVER};
}}
{sc} QScrollArea QScrollBar::add-line:vertical,
{sc} QScrollArea QScrollBar::sub-line:vertical {{
  height: 0px;
  width: 0px;
  border: none;
}}
{sc} QScrollArea QScrollBar::add-page:vertical,
{sc} QScrollArea QScrollBar::sub-page:vertical {{
  background: transparent;
}}
{sc} QScrollArea QScrollBar:horizontal {{
  background: {SURFACE};
  height: {w}px;
  margin: 0px {edge}px {edge}px {edge}px;
  border: none;
  border-radius: {r}px;
}}
{sc} QScrollArea QScrollBar::handle:horizontal {{
  background: {BORDER_HAIR};
  min-width: {mn}px;
  border-radius: {r}px;
  margin: 1px {hp}px;
}}
{sc} QScrollArea QScrollBar::handle:horizontal:hover {{
  background: {BTN_HOVER};
}}
{sc} QScrollArea QScrollBar::add-line:horizontal,
{sc} QScrollArea QScrollBar::sub-line:horizontal {{
  height: 0px;
  width: 0px;
  border: none;
}}
{sc} QScrollArea QScrollBar::add-page:horizontal,
{sc} QScrollArea QScrollBar::sub-page:horizontal {{
  background: transparent;
}}
"""
