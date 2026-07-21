"""레거시 독립 허브 창은 제거됨 — 프레임리스 제어창(`control_main.PipelaQtMainWindow`) 설정 탭과 공통 크롬.

토큰은 `pipela_qt.theme`, 스케일·pt는 `pipela_qt.ui_adaptive` — 이 모듈은 QSS 문자열만 조립한다."""

from __future__ import annotations

from pipela_qt import control_tab_chrome as _ctc
from pipela_qt import theme as T
from pipela_qt.kill_counter_viewport_metrics import KC_WINDOW_FONT_SCALE
from pipela_qt.ui_adaptive import letter_spacing_qss, qss_pad_all, qss_pad_vh, scale_px_h, scale_px_v, spt
def shell_root_outer_margins_lr_tb() -> tuple[int, int, int, int]:
    """허브·제어 본문 외곽 — 메인 창과 동일 (12·12·12·12, 스케일)."""
    ph = scale_px_h(12)
    pv = scale_px_v(12)
    return (ph, pv, ph, pv)


def shell_hub_inner_gutter_px() -> int:
    """설정 허브 그리드·스크롤 내부 세로 간격."""
    return scale_px_v(8)


def shell_hub_scroll_right_chrome_px() -> int:
    """허브 콘텐츠 `QVBoxLayout` 오른쪽 여백 — 메인과 동일."""
    return scale_px_h(8)


def shell_muted_subtitle_label_qss() -> str:
    """섹션 안내 한 줄 — 메인 `_head` 와 동일 (제어창 설정 타이틀에도 사용)."""
    return (
        f"QLabel {{ color: {T.FG_MUTED}; font-size: {T.spt(9.5)}; font-weight: 500; "
        f"font-family: {T.FONT_CSS_UI}; letter-spacing: {letter_spacing_qss()}; "
        f"padding: 0px; }}"
    )


def settings_breadcrumb_chrome_qss() -> str:
    """Settings path — parent link ``pipelaBreadcrumbSeg``, current chip ``pipelaBreadcrumbCurrent``."""
    r = scale_px_v(8)
    py, px = scale_px_v(4), scale_px_h(12)
    seg_py, seg_px = scale_px_v(2), scale_px_h(4)
    return (
        f"QPushButton#pipelaBreadcrumbSeg {{"
        f"  color: {T.FG_MUTED};"
        f"  background: transparent;"
        f"  border: none;"
        f"  font-size: {T.spt(9.5)};"
        f"  font-weight: 500;"
        f"  font-family: {T.FONT_CSS_UI};"
        f"  letter-spacing: {letter_spacing_qss()};"
        f"  padding: {seg_py}px {seg_px}px;"
        f"  text-align: center;"
        f"}}"
        f"QPushButton#pipelaBreadcrumbSeg:hover {{ color: {T.ACCENT}; }}"
        f"QPushButton#pipelaBreadcrumbSeg:pressed {{ color: {T.ACCENT}; }}"
        f"QLabel#pipelaBreadcrumbSep {{"
        f"  color: {T.FG_DIM};"
        f"  font-size: {T.spt(9.5)};"
        f"  font-weight: 600;"
        f"  padding: 0px {scale_px_h(2)}px;"
        f"}}"
        f"QLabel#pipelaBreadcrumbCurrent {{"
        f"  color: {T.ACCENT};"
        f"  background-color: rgba(61, 212, 201, 0.16);"
        f"  border: 1px solid rgba(61, 212, 201, 0.45);"
        f"  border-left: 3px solid {T.ACCENT};"
        f"  border-radius: {r}px;"
        f"  font-size: {T.spt(10)};"
        f"  font-weight: 700;"
        f"  font-family: {T.FONT_CSS_UI};"
        f"  letter-spacing: {letter_spacing_qss()};"
        f"  padding: {py}px {px}px;"
        f"}}"
    )


def hub_card_row_title_label_qss() -> str:
    """`HubCard` 제목 `QLabel` — 설정 탭 허브 `QPushButton` 타이포와 동일 계열(12/600)."""
    return (
        f"color: {T.FG}; font-weight: 600; font-size: {T.spt(12)}; font-family: {T.FONT_CSS_UI}; "
        f"letter-spacing: {letter_spacing_qss()};"
    )


def hub_card_qss_block() -> str:
    """`QFrame#hubCard` — 허브 카드 (메인 허브 그리드와 제어창 공통 시트에 포함)."""
    return f"""
QFrame#hubCard {{
  background-color: {T.CARD_BG};
  border: 1px solid {T.BORDER};
  border-radius: {T.RADIUS_SM};
}}
QFrame#hubCard:hover {{
  background-color: {T.CARD_HOVER};
  border: 1px solid {T.ACCENT};
}}
"""


def shell_scroll_area_plain_qss() -> str:
    """배경만 — 테두리 없음."""
    return f"QScrollArea {{ background: {T.WINDOW_BG}; border: none; }}"


def frameless_outer_window_qss(*, object_name: str) -> str:
    """프레임리스 `QMainWindow` 바깥 1px — 제어창(`echFramelessMain`)·킬 플로터(`pipelaKcFrameless`) 동일 토큰."""
    return (
        f"QMainWindow#{object_name} {{\n"
        f"  background: {T.WINDOW_BG};\n"
        f"  border: 1px solid {T.STRIP_BORDER};\n"
        f"  border-radius: {scale_px_v(2)}px;\n"
        f"}}\n"
    )


def kill_counter_floater_window_qss() -> str:
    """`kill_counter_window.PipelaQtKillCounterWindow` — 제어창(`control_frameless_window_qss`)과 동일 베이스: 루트 배경·허브 카드·PlainTextEdit·스크롤."""
    _pte_pad = qss_pad_all(8)
    return (
        frameless_outer_window_qss(object_name="pipelaKcFrameless")
        + f"""
#pipelaKcRoot {{
  background: {T.WINDOW_BG};
  color: {T.FG};
}}
QWidget#pipelaKcPanel {{
  background: transparent;
  color: {T.FG};
}}
QMainWindow#pipelaKcFrameless QPlainTextEdit {{
  background: {T.PANEL_BG};
  color: {T.FG};
  border: 1px solid {T.BORDER_HAIR};
  border-radius: {T.RADIUS_SM};
  padding: {_pte_pad};
  selection-background-color: {T.ACCENT};
  font-family: {T.FONT_CSS_UI};
  font-size: {T.spt(9.5 * KC_WINDOW_FONT_SCALE)};
  letter-spacing: {letter_spacing_qss()};
}}
"""
        + hub_card_qss_block()
        + f"""
/* 킬 카운터 패널 섹션 카드 — 허브와 달리 호버 하이라이트 없음 */
QMainWindow#pipelaKcFrameless QWidget#pipelaKcPanel QFrame#hubCard:hover {{
  background-color: {T.CARD_BG};
  border: 1px solid {T.BORDER};
}}
"""
        + shell_scroll_area_plain_qss()
        + "\n"
        + T.narrow_scrollbars_qss(scope_selector="QMainWindow#pipelaKcFrameless")
    )


def intro_skip_settings_popup_qss() -> str:
    """런처 스트립 Intro Skip 설정 — OS 타이틀 없음, 상단 스트립 톤 헤더 + 얇은 외곽선."""
    r = scale_px_v(2)
    _pad_close = qss_pad_vh(2, 6)
    return (
        f"QDialog#pipelaIntroSkipPopup {{\n"
        f"  background: {T.WINDOW_BG};\n"
        f"  border: 1px solid {T.STRIP_BORDER};\n"
        f"  border-radius: {r}px;\n"
        f"}}\n"
        f"QFrame#pipelaIntroSkipPopupHead {{\n"
        f"  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
        f"    stop:0 {T.STRIP_BG_TOP}, stop:1 {T.STRIP_BG});\n"
        f"  border: none;\n"
        f"  border-top-left-radius: {r}px;\n"
        f"  border-top-right-radius: {r}px;\n"
        f"  border-bottom: 1px solid {T.STRIP_BORDER};\n"
        f"}}\n"
        f"QLabel#pipelaIntroSkipPopupTitle {{\n"
        f"  color: {T.STRIP_ACCENT};\n"
        f"  font-family: {T.FONT_CSS_UI};\n"
        f"  font-size: {T.spt(11)};\n"
        f"  font-weight: 700;\n"
        f"  letter-spacing: {letter_spacing_qss()};\n"
        f"  background: transparent;\n"
        f"}}\n"
        f"QPushButton#pipelaIntroSkipPopupClose {{\n"
        f"  background: transparent;\n"
        f"  border: none;\n"
        f"  border-radius: {T.STRIP_RADIUS_BTN};\n"
        f"  padding: {_pad_close};\n"
        f"  min-width: {scale_px_h(22)}px;\n"
        f"  min-height: {scale_px_v(18)}px;\n"
        f"}}\n"
        f"QPushButton#pipelaIntroSkipPopupClose:hover {{ background: {T.STRIP_BTN_HOVER_CLOSE}; }}\n"
    ) + shell_scroll_area_plain_qss() + T.narrow_scrollbars_qss(
        scope_selector="QDialog#pipelaIntroSkipPopup",
    )


def main_hub_window_qss() -> str:
    """독립 `MainWindow` 허브 — 제어창과 동일 카드·스크롤 규칙."""
    return (
        f"QMainWindow, QWidget {{ background-color: {T.WINDOW_BG}; }}\n"
        f"{shell_scroll_area_plain_qss()}\n"
        f"{hub_card_qss_block()}"
    )


def settings_hub_entry_button_qss() -> str:
    """설정 탭 허브 그리드 `QPushButton` — `HubCard`와 동일 타이포, 메인 액션과 맞는 유리 면.

    (액센트 세로막대 없음; off/hover/pressed 는 `MAIN_GLASS_*` 토큰.)"""
    _hub_fpt = T.spt(12)
    _hub_rs = T.MAIN_GLASS_BTN_RADIUS
    _ls = letter_spacing_qss()
    _pad = qss_pad_vh(10, 12)
    return (
        f"QPushButton {{"
        f" background: {T.MAIN_GLASS_OFF_BG}; color: {T.FG}; font-weight: 600; "
        f"font-size: {_hub_fpt}; font-family: {T.FONT_CSS_UI};"
        f" border: 1px solid {T.MAIN_GLASS_OFF_BORDER}; padding: {_pad}; letter-spacing: {_ls};"
        f" border-radius: {_hub_rs}; text-align: center; }}"
        f"QPushButton:hover {{"
        f" background: {T.MAIN_GLASS_OFF_HOVER_BG}; border: 1px solid {T.ACCENT}; color: {T.FG};"
        f"}}"
        f"QPushButton:pressed {{"
        f" background: {T.MAIN_GLASS_PRESSED_BG}; border: 1px solid {T.MAIN_GLASS_PRESSED_BORDER};"
        f"}}"
    )


def control_frameless_window_qss() -> str:
    """`QMainWindow#pipelaFramelessMain` + 터미널·탭·내부와 허브 카드 규칙."""
    _pte_pad = qss_pad_all(8)
    _log_pad = qss_pad_vh(10, 8)
    _sb_narrow = max(4, scale_px_h(5))
    _sb_cap_r = max(2, scale_px_h(3))
    _sb_edge = scale_px_h(3)
    _sb_handle_pad = scale_px_v(2)
    _sb_min = scale_px_v(22)
    _pane_pad = scale_px_h(4)
    _tab_pad = _ctc.main_tabs_tab_padding_qss()
    _tab_seg_r = _ctc.main_tabs_segment_radius_px()
    _tab_vm = _ctc.main_tabs_bar_vertical_inset_px()
    _tab_rail = _ctc.main_tabs_rail_hpad_px()
    _tab_mh = _ctc.main_tabs_min_height_px()
    _tab_fpt = _ctc.main_tabs_label_font_spt()
    _tab_sel_tint = "rgba(61, 212, 201, 0.08)"
    _tab_hover_mist = "rgba(255, 255, 255, 0.05)"
    _ag_tray_r = max(10, int(scale_px_v(12)))
    return (
        frameless_outer_window_qss(object_name="echFramelessMain")
        + f"""
#pipelaRoot, #pipelaBody {{
  background: {T.WINDOW_BG};
  color: {T.FG};
}}
#pipelaBody QLabel {{
  color: {T.FG_MUTED};
}}
{settings_breadcrumb_chrome_qss()}
QPlainTextEdit {{
  background: {T.PANEL_BG};
  color: {T.FG};
  border: 1px solid {T.BORDER_HAIR};
  border-radius: {T.RADIUS_SM};
  padding: {_pte_pad};
  selection-background-color: {T.ACCENT};
  font-family: {T.FONT_CSS_UI};
  font-size: {T.spt(9.5)};
  letter-spacing: {letter_spacing_qss()};
}}
QTextEdit#pipelaTerminalLog {{
  background: {T.TERMINAL_BG};
  color: {T.TERMINAL_FG};
  border: 1px solid {T.TERMINAL_BORDER};
  border-radius: {T.RADIUS_SM};
  padding: {_log_pad};
  selection-background-color: {T.TERMINAL_SELECTION_BG};
  selection-color: {T.TERMINAL_SELECTION_FG};
  font-family: {T.FONT_CSS_UI};
  font-size: {T.spt(9.25)};
  letter-spacing: {letter_spacing_qss()};
}}
QTextEdit#pipelaTerminalLog QScrollBar:vertical {{
  background: rgba(10, 18, 15, 0.92);
  width: {_sb_narrow}px;
  margin: {_sb_edge}px {_sb_edge}px {_sb_edge}px 0px;
  border: none;
  border-radius: {_sb_cap_r}px;
}}
QTextEdit#pipelaTerminalLog QScrollBar::handle:vertical {{
  background: {T.TERMINAL_SCROLLGRIP};
  min-height: {_sb_min}px;
  border-radius: {_sb_cap_r}px;
  margin: {_sb_handle_pad}px 1px;
}}
QTextEdit#pipelaTerminalLog QScrollBar::handle:vertical:hover {{
  background: {T.TERMINAL_SCROLLGRIP_HOVER};
}}
QTextEdit#pipelaTerminalLog QScrollBar::add-line:vertical,
QTextEdit#pipelaTerminalLog QScrollBar::sub-line:vertical {{
  height: 0px;
  width: 0px;
  border: none;
}}
QTextEdit#pipelaTerminalLog QScrollBar::add-page:vertical,
QTextEdit#pipelaTerminalLog QScrollBar::sub-page:vertical {{
  background: transparent;
}}
QTextEdit#pipelaTerminalLog QScrollBar:horizontal {{
  background: rgba(10, 18, 15, 0.92);
  height: {_sb_narrow}px;
  margin: 0px {_sb_edge}px {_sb_edge}px {_sb_edge}px;
  border: none;
  border-radius: {_sb_cap_r}px;
}}
QTextEdit#pipelaTerminalLog QScrollBar::handle:horizontal {{
  background: {T.TERMINAL_SCROLLGRIP};
  min-width: {_sb_min}px;
  border-radius: {_sb_cap_r}px;
  margin: 1px {_sb_handle_pad}px;
}}
QTextEdit#pipelaTerminalLog QScrollBar::handle:horizontal:hover {{
  background: {T.TERMINAL_SCROLLGRIP_HOVER};
}}
QTextEdit#pipelaTerminalLog QScrollBar::add-line:horizontal,
QTextEdit#pipelaTerminalLog QScrollBar::sub-line:horizontal {{
  height: 0px;
  width: 0px;
  border: none;
}}
QTextEdit#pipelaTerminalLog QScrollBar::add-page:horizontal,
QTextEdit#pipelaTerminalLog QScrollBar::sub-page:horizontal {{
  background: transparent;
}}
{T.narrow_scrollbars_qss(scope_selector="QMainWindow#pipelaFramelessMain")}
#pipelaTabArea {{
  background: {T.SURFACE};
  border: none;
}}
QSplitter#pipelaMainSplit::handle {{
  background: {T.SURFACE};
  border: none;
  margin: 0px;
}}
#pipelaActionBtnPanel {{
  background: {T.MAIN_GLASS_TRAY_BG};
  border: 1px solid {T.MAIN_GLASS_TRAY_BORDER};
  border-radius: {_ag_tray_r}px;
}}
QTabWidget#pipelaMainTabs {{
  background: {T.SURFACE};
  border: none;
}}
QTabWidget#pipelaMainTabs::pane {{
  border: 1px solid {T.BORDER_HAIR};
  border-top: none;
  border-bottom-left-radius: {T.RADIUS_SM};
  border-bottom-right-radius: {T.RADIUS_SM};
  top: 0px;
  margin-top: 0px;
  background: {T.SURFACE};
  padding: {_pane_pad}px;
}}
QTabWidget#pipelaMainTabs::tab-bar {{
  left: 0px;
  background: {T.SURFACE};
  border: none;
  border-bottom: 1px solid {T.BORDER_HAIR};
  padding: {_tab_vm}px {_tab_rail}px 0px {_tab_rail}px;
}}
QTabWidget#pipelaMainTabs QTabBar::tab {{
  background: transparent;
  color: {T.FG_MUTED};
  border: none;
  border-bottom: 2px solid transparent;
  min-width: 0px;
  min-height: {_tab_mh}px;
  padding: {_tab_pad};
  margin: 0px;
  border-top-left-radius: {_tab_seg_r}px;
  border-top-right-radius: {_tab_seg_r}px;
  font-family: {T.FONT_CSS_UI};
  font-size: {_tab_fpt};
  font-weight: 500;
  letter-spacing: {letter_spacing_qss()};
}}
QTabWidget#pipelaMainTabs QTabBar::tab:selected {{
  background: {_tab_sel_tint};
  color: {T.ACCENT};
  border: none;
  border-bottom: 2px solid {T.ACCENT};
  font-weight: 600;
}}
QTabWidget#pipelaMainTabs QTabBar::tab:hover:!selected {{
  background: {_tab_hover_mist};
  color: {T.FG};
  border: none;
  border-bottom: 2px solid transparent;
  font-weight: 500;
}}
QTabWidget#pipelaMainTabs QTabBar::tab:selected:hover {{
  background: {_tab_sel_tint};
  color: {T.ACCENT};
  border: none;
  border-bottom: 2px solid {T.ACCENT};
  font-weight: 600;
}}
{hub_card_qss_block()}
{shell_scroll_area_plain_qss()}
"""
    )
