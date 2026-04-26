"""설정 패널 공통 — 타이포·구분선·가로 유동(라벨↔컨트롤) 배치."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from pipela_qt import theme as T
from pipela_qt.scroll_utils import tie_scroll_content_min_width
from pipela_qt.ui_adaptive import letter_spacing_qss, qss_pad_all, scale_px


def settings_root_vertical_spacing() -> int:
    return scale_px(12)


def _settings_label_font_qss() -> str:
    return f"font-family: {T.FONT_CSS_UI}; text-align: center;"


def settings_label_align_center_h(lbl: QLabel) -> None:
    """설정용 ``QLabel`` — 한 줄은 세로 가운데, ``wordWrap`` 켜진 다줄은 위쪽 기준."""
    a = (
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
        if lbl.wordWrap()
        else Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
    )
    lbl.setAlignment(a)


def settings_page_title_style() -> str:
    return (
        f"{_settings_label_font_qss()} font-weight: 700; font-size: {T.spt(12.5)}; "
        f"color: {T.ACCENT}; letter-spacing: {letter_spacing_qss()};"
    )


def settings_section_heading_style(*, top_margin_px: int = 0) -> str:
    mt = f" margin-top: {top_margin_px}px;" if top_margin_px else ""
    return (
        f"{_settings_label_font_qss()} font-weight: 600; font-size: {T.spt(10.5)}; "
        f"color: {T.FG};{mt}"
    )


def settings_caption_style() -> str:
    return (
        f"{_settings_label_font_qss()} color: {T.FG_MUTED}; font-size: {T.spt(9.25)}; "
        f"font-weight: 400; letter-spacing: {letter_spacing_qss()};"
    )


def settings_footnote_style() -> str:
    return (
        f"{_settings_label_font_qss()} color: {T.FG_DIM}; font-size: {T.spt(8.5)}; "
        f"font-weight: 400; letter-spacing: {letter_spacing_qss()};"
    )


def settings_footnote_style_color(foreground: str) -> str:
    """접힘/비활성 등에 따라 색만 바꾸는 설명문 (크기·정렬·글꼴은 동일)."""
    return (
        f"{_settings_label_font_qss()} color: {foreground}; font-size: {T.spt(8.5)}; "
        f"font-weight: 400; letter-spacing: {letter_spacing_qss()};"
    )


def settings_field_label_style() -> str:
    return (
        f"{_settings_label_font_qss()} color: {T.FG}; font-size: {T.spt(9.75)}; "
        f"font-weight: 500; letter-spacing: {letter_spacing_qss()};"
    )


def settings_emphasis_line_style() -> str:
    return (
        f"{_settings_label_font_qss()} color: {T.ACCENT}; font-size: {T.spt(10)}; "
        f"font-weight: 600; letter-spacing: {letter_spacing_qss()};"
    )


def settings_path_connector_style() -> str:
    """섹션 사이 ‘↓’ 등 시각 구분 — 액센트·조금 큰 글자."""
    return (
        f"{_settings_label_font_qss()} color: {T.ACCENT}; font-size: {T.spt(15)}; "
        f"font-weight: 500; letter-spacing: {letter_spacing_qss()};"
    )


def settings_template_metric_muted_label_style() -> str:
    """‘실시간’ / ‘/’ / ‘기준’ 등 메트릭 보조 라벨."""
    return (
        f"{_settings_label_font_qss()} color: {T.FG_MUTED}; font-size: {T.spt(8.9)}; "
        f"font-weight: 500; letter-spacing: {letter_spacing_qss()};"
    )


def panel_toolbar_button_qss() -> str:
    """패널 상단 한 줄 툴바(미리보기·영역·해제 등) — `T.spt`·`scale_px` 패딩."""
    pv, ph = scale_px(5), scale_px(10)
    return (
        f"QPushButton {{ background: {T.BTN_BG}; color: {T.FG}; text-align: center; "
        f"border: 1px solid {T.BORDER_HAIR}; border-radius: {T.RADIUS_SM}; "
        f"padding: {pv}px {ph}px; font-weight: 600; font-size: {T.spt(9)}; "
        f"font-family: {T.FONT_CSS_UI}; letter-spacing: {letter_spacing_qss()}; }}"
        f"QPushButton:hover {{ background: {T.BTN_HOVER}; }}"
        f"QPushButton:pressed {{ background: {T.BTN_PRESSED}; }}"
        f"QPushButton:disabled {{ color: {T.FG_DIM}; background: {T.PANEL_BG}; }}"
    )


def panel_secondary_button_qss() -> str:
    """보조 액션(랩 초기화·종료·세션 리셋 등)."""
    pv, ph = scale_px(6), scale_px(12)
    return (
        f"QPushButton {{ background: {T.BTN_BG}; color: {T.FG}; text-align: center; "
        f"border: 1px solid {T.BORDER_HAIR}; border-radius: {T.RADIUS_SM}; "
        f"padding: {pv}px {ph}px; font-weight: 600; font-size: {T.spt(9.25)}; "
        f"font-family: {T.FONT_CSS_UI}; letter-spacing: {letter_spacing_qss()}; }}"
        f"QPushButton:hover {{ background: {T.BTN_HOVER}; }}"
        f"QPushButton:pressed {{ background: {T.BTN_PRESSED}; }}"
        f"QPushButton:disabled {{ color: {T.FG_DIM}; background: {T.PANEL_BG}; }}"
    )


def panel_primary_button_qss() -> str:
    """강조 1차 액션(예: 랩 시작/일시중지/재개)."""
    pv, ph = scale_px(6), scale_px(14)
    return (
        f"QPushButton {{ background: {T.BTN_ON}; color: {T.FG}; text-align: center; "
        f"border: 1px solid {T.BTN_ON_BORDER}; border-radius: {T.RADIUS_SM}; "
        f"padding: {pv}px {ph}px; font-weight: 600; font-size: {T.spt(9.5)}; "
        f"font-family: {T.FONT_CSS_UI}; letter-spacing: {letter_spacing_qss()}; }}"
        f"QPushButton:hover {{ background: {T.BTN_ON_HOVER}; }}"
        f"QPushButton:pressed {{ background: {T.BTN_PRESSED}; }}"
        f"QPushButton:disabled {{ color: {T.FG_DIM}; background: {T.PANEL_BG}; "
        f"border: 1px solid {T.BORDER_HAIR}; }}"
    )


def make_settings_hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(max(1, scale_px(1)))
    line.setStyleSheet(
        f"background: {T.DIVIDER}; color: {T.DIVIDER}; border: none; "
        f"min-height: 1px; max-height: 1px;",
    )
    return line


def settings_card_qss(*, pad_px: float = 10.0) -> str:
    pad = qss_pad_all(pad_px)
    return (
        f"QFrame#settingsCard {{ background: {T.CARD_BG}; "
        f"border: 1px solid {T.BORDER_HAIR}; border-radius: {T.RADIUS_SM}; "
        f"{pad} }}"
    )


def make_settings_card_frame() -> QFrame:
    fr = QFrame()
    fr.setObjectName("settingsCard")
    fr.setStyleSheet(settings_card_qss())
    return fr


def configure_settings_scroll_area(scroll: QScrollArea) -> None:
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    tie_scroll_content_min_width(scroll)


def add_settings_field_row(
    parent_lay: QVBoxLayout,
    label_text: str,
    *controls: QWidget,
) -> None:
    """가운데 정렬 라벨(유동·줄바꿈) + 오른쪽: 컨트롤 묶음(최소 폭)."""
    row = QHBoxLayout()
    row.setSpacing(scale_px(10))
    lab = QLabel(label_text)
    lab.setWordWrap(True)
    lab.setStyleSheet(settings_field_label_style())
    settings_label_align_center_h(lab)
    lab.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    row.addWidget(lab, 1)
    if controls:
        box = QHBoxLayout()
        box.setSpacing(scale_px(8))
        for w in controls:
            w.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            box.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addLayout(box, 0)
    parent_lay.addLayout(row)


def add_template_similarity_row(parent_lay: QVBoxLayout, cur: QLabel, thr_spin: QWidget) -> None:
    """이미지 템플릿 유사도: `실시간 n.nn / 기준 n.nn` (임계는 스핀) — 가운데 뭉쳐 배치."""
    st_m = settings_template_metric_muted_label_style()
    row = QHBoxLayout()
    row.setSpacing(scale_px(8))
    live = QLabel("실시간")
    live.setStyleSheet(st_m)
    settings_label_align_center_h(live)
    live.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    mid = QLabel("/")
    mid.setStyleSheet(st_m)
    settings_label_align_center_h(mid)
    mid.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    thr_lbl = QLabel("기준")
    thr_lbl.setStyleSheet(st_m)
    settings_label_align_center_h(thr_lbl)
    cur.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    thr_spin.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    row.addStretch(1)
    row.addWidget(live, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(cur, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(mid, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(thr_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addWidget(thr_spin, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addStretch(1)
    parent_lay.addLayout(row)


def add_settings_control_row_centered(
    parent_lay: QVBoxLayout,
    *widgets: QWidget,
    spacing_px: int | None = None,
) -> None:
    """라디오·토글 등 가운데 정렬 한 줄."""
    row = QHBoxLayout()
    row.setSpacing(scale_px(spacing_px if spacing_px is not None else 10))
    row.addStretch(1)
    for w in widgets:
        row.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addStretch(1)
    parent_lay.addLayout(row)
