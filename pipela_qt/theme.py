# Pipela Qt UI — 차콜 베이스 + 청록·틸 액센트 (스트립·제어창 동일 계열)

from pipela_core.ui_fonts import qt_stylesheet_font_family
from pipela_qt.ui_adaptive import letter_spacing_qss, qss_pad_all, qss_pad_vh, scale_px_h, scale_px_v, spt

# Qt stylesheet `font-family:` 값 — 영문 모노 + 한글 맑은 고딕 (AGENTS.md §19 / ui_fonts)
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

# --- 제어창 메인 액션 그리드 — 반투명 유리 (QSS qlineargradient + 얇은 하이라이트 테두리) ---
MAIN_GLASS_BTN_RADIUS = RADIUS
# Off: 상단 하이라이트 → 아래로 어두워지는 프로스트
MAIN_GLASS_OFF_BG = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 rgba(255, 255, 255, 0.10), stop:0.42 rgba(40, 46, 56, 0.52), "
    "stop:1 rgba(16, 20, 26, 0.86))"
)
MAIN_GLASS_OFF_BORDER = "rgba(255, 255, 255, 0.13)"
MAIN_GLASS_OFF_HOVER_BG = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 rgba(255, 255, 255, 0.16), stop:0.5 rgba(52, 60, 72, 0.65), "
    "stop:1 rgba(24, 30, 38, 0.90))"
)
# On: 액센트 틴트 + 깊은 베이스
MAIN_GLASS_ON_BG = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 rgba(61, 212, 201, 0.28), stop:0.38 rgba(16, 58, 60, 0.60), "
    "stop:1 rgba(4, 26, 28, 0.92))"
)
MAIN_GLASS_ON_BORDER = "rgba(32, 210, 195, 0.52)"
MAIN_GLASS_ON_HOVER_BG = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 rgba(110, 235, 220, 0.32), stop:0.5 rgba(20, 72, 74, 0.72), "
    "stop:1 rgba(6, 40, 42, 0.95))"
)
# Emit(동작 중) 강조
MAIN_GLASS_EMIT_BG = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 rgba(120, 245, 230, 0.38), stop:0.4 rgba(22, 96, 88, 0.78), "
    "stop:1 rgba(6, 48, 44, 0.94))"
)
MAIN_GLASS_EMIT_BORDER = "rgba(150, 250, 238, 0.58)"
MAIN_GLASS_EMIT_HOVER_BG = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 rgba(180, 255, 245, 0.35), stop:0.5 rgba(32, 110, 102, 0.82), "
    "stop:1 rgba(8, 58, 54, 0.97))"
)
# 눌림: 유리 뒤로 눌리는 느낌 — 실질적 불투명
MAIN_GLASS_PRESSED_BG = "rgba(4, 6, 10, 0.94)"
MAIN_GLASS_PRESSED_BORDER = "rgba(255, 255, 255, 0.09)"
# 액션 그리드를 감싸는 트레이 (패널 위젯)
MAIN_GLASS_TRAY_BG = (
    "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
    "stop:0 rgba(255, 255, 255, 0.05), stop:1 rgba(0, 0, 0, 0.16))"
)
MAIN_GLASS_TRAY_BORDER = "rgba(255, 255, 255, 0.08)"


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
    w_v = max(4, int(scale_px_h(5)))
    h_h = max(4, int(scale_px_v(5)))
    r = max(2, int(scale_px_v(3)))
    edge_v = int(scale_px_v(3))
    edge_h = int(scale_px_h(3))
    hp_v = int(scale_px_v(2))
    hp_h = int(scale_px_h(2))
    mn_v = int(scale_px_v(20))
    mn_h = int(scale_px_h(20))
    sc = str(scope_selector).strip()
    return f"""
{sc} QScrollArea QScrollBar:vertical {{
  background: {SURFACE};
  width: {w_v}px;
  margin: {edge_v}px {edge_h}px {edge_v}px 0px;
  border: none;
  border-radius: {r}px;
}}
{sc} QScrollArea QScrollBar::handle:vertical {{
  background: {BORDER_HAIR};
  min-height: {mn_v}px;
  border-radius: {r}px;
  margin: {hp_v}px 1px;
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
  height: {h_h}px;
  margin: 0px {edge_h}px {edge_h}px {edge_h}px;
  border: none;
  border-radius: {r}px;
}}
{sc} QScrollArea QScrollBar::handle:horizontal {{
  background: {BORDER_HAIR};
  min-width: {mn_h}px;
  border-radius: {r}px;
  margin: 1px {hp_h}px;
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
