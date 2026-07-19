"""설정 패널 공통 — 타이포·구분선·가로 유동(라벨↔컨트롤) 배치."""

from __future__ import annotations

from typing import Any, Literal

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
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_adaptive import letter_spacing_qss, qss_pad_all, scale_px_h, scale_px_v

# 「실시간」「기준」 강조 라벨과 동일 — 실시간 수치·임계 스핀 글자 크기에도 사용.
TEMPLATE_SIMILARITY_EMPHASIS_DESIGN_PT = 8.9 * 1.5


def settings_root_vertical_spacing() -> int:
    return scale_px_v(12)


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


def settings_template_thumb_target_caption_style() -> str:
    """원본 PNG(목표) 캡션 — 액센트 틸, 본문보다 한 단계 작되 선명."""
    return (
        f"{_settings_label_font_qss()} color: {T.ACCENT}; font-size: {T.spt(9.85)}; "
        f"font-weight: 600; letter-spacing: {letter_spacing_qss()};"
    )


def settings_template_thumb_match_caption_style() -> str:
    """인게임 매칭 패치 캡션 — 터미널 포스포 그린(실측/히트)."""
    return (
        f"{_settings_label_font_qss()} color: {T.TERMINAL_FG}; font-size: {T.spt(9.85)}; "
        f"font-weight: 600; letter-spacing: {letter_spacing_qss()};"
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


def settings_path_connector_qss(*, color: str) -> str:
    """섹션 사이 ‘↓’ — 글자색만 바꿔 재사용(기본·흐림·펄스 보간)."""
    return (
        f"{_settings_label_font_qss()} color: {color}; font-size: {T.spt(15)}; "
        f"font-weight: 500; letter-spacing: {letter_spacing_qss()};"
    )


def settings_path_connector_style() -> str:
    """섹션 사이 ‘↓’ 등 시각 구분 — 액센트·조금 큰 글자."""
    return settings_path_connector_qss(color=T.ACCENT)


def settings_path_connector_style_muted() -> str:
    """‘↓’ 비활성·대기 색(잠깐 통과 펄스 전)."""
    return settings_path_connector_qss(color=T.FG_DIM)


def settings_template_metric_muted_label_style(*, emphasis: bool = False) -> str:
    """‘실시간’ / ‘/’ / ‘기준’ 등 메트릭 보조 라벨. emphasis=True → 실시간·기준용 1.5×."""
    pt = TEMPLATE_SIMILARITY_EMPHASIS_DESIGN_PT if emphasis else 8.9
    return (
        f"{_settings_label_font_qss()} color: {T.FG_MUTED}; font-size: {T.spt(pt)}; "
        f"font-weight: 500; letter-spacing: {letter_spacing_qss()};"
    )


def settings_template_similarity_value_spin_qss() -> str:
    """템플릿 행 기준(임계) `DragDoubleSpinBox` — 실시간·기준 한글 라벨과 동일 pt."""
    pt = TEMPLATE_SIMILARITY_EMPHASIS_DESIGN_PT
    pv, ph = scale_px_v(2), scale_px_h(6)
    mh = scale_px_v(26)
    fe = T.FONT_CSS_UI
    fs = T.spt(pt)
    tls = letter_spacing_qss()
    return (
        f"QDoubleSpinBox {{ font-family: {fe}; font-size: {fs}; font-weight: 600; color: {T.FG}; "
        f"letter-spacing: {tls}; }}"
        f"QDoubleSpinBox QLineEdit {{ font-family: {fe}; font-size: {fs}; font-weight: 600; color: {T.FG}; "
        f"letter-spacing: {tls}; padding: {pv}px {ph}px; min-height: {mh}px; }}"
    )


def panel_toolbar_button_qss() -> str:
    """패널 상단 한 줄 툴바(미리보기·영역·해제 등) — `T.spt`·`scale_px` 패딩."""
    pv, ph = scale_px_v(5), scale_px_h(10)
    return (
        f"QPushButton {{ background: {T.BTN_BG}; color: {T.FG}; text-align: center; "
        f"border: 1px solid {T.BORDER_HAIR}; border-radius: {T.RADIUS_SM}; "
        f"padding: {pv}px {ph}px; font-weight: 600; font-size: {T.spt(9)}; "
        f"font-family: {T.FONT_CSS_UI}; letter-spacing: {letter_spacing_qss()}; }}"
        f"QPushButton:hover {{ background: {T.BTN_HOVER}; }}"
        f"QPushButton:pressed {{ background: {T.BTN_PRESSED}; }}"
        f"QPushButton:disabled {{ color: {T.FG_DIM}; background: {T.PANEL_BG}; }}"
    )


TemplateToolbarRole = Literal["capture", "test", "preview", "region", "clear"]


def panel_template_toolbar_button_qss(
    role: TemplateToolbarRole,
    *,
    omit_inline_font: bool = False,
    font_size: str | None = None,
    letter_spacing: str | None = None,
    vertical_padding_px: int | None = None,
    horizontal_padding_px: int | None = None,
) -> str:
    """템플릿 섹션 툴바 — `TemplateProbeSectionFrame` 과 같이 패널 베이스 위에 역할색이 은은히 비치는 대각 그라데이션.

    `omit_inline_font` 가 True 면 글자 크기는 QSS 로 두지 않고 위젯 ``setFont`` 에 맡긴다.
    그렇지 않으면 ``font_size`` / ``letter_spacing`` 에 ``fit_qpushbutton_text_width_qss`` 출력을 넣을 수 있다."""
    pv = (
        vertical_padding_px
        if vertical_padding_px is not None
        else scale_px_v(5)
    )
    ph = (
        horizontal_padding_px
        if horizontal_padding_px is not None
        else scale_px_h(10)
    )
    if omit_inline_font:
        base = (
            f"color: {T.FG}; text-align: center; border-radius: {T.RADIUS_SM}; "
            f"padding: {pv}px {ph}px;"
        )
    else:
        fs = font_size if font_size is not None else T.spt(9)
        ls = letter_spacing if letter_spacing is not None else letter_spacing_qss()
        base = (
            f"color: {T.FG}; text-align: center; border-radius: {T.RADIUS_SM}; "
            f"padding: {pv}px {ph}px; font-weight: 600; font-size: {fs}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: {ls};"
        )
    pb, sf, cb = T.PANEL_BG, T.SURFACE, T.CARD_BG
    # 대부분 `pb`/`sf` — 좁은 구간만 틴트(내부 광). 호버는 광만 살짝 밝게, 눌림은 살짝 누름.
    g: dict[TemplateToolbarRole, tuple[str, str, str, str]] = {
        "capture": (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.2 {pb}, "
            f"stop:0.42 {pb}, stop:0.52 #243a36, stop:0.64 {pb}, stop:0.85 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.18 {pb}, "
            f"stop:0.38 {pb}, stop:0.5 #2c4a44, stop:0.6 {pb}, stop:0.82 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.22 {pb}, "
            f"stop:0.5 #1e302c, stop:0.72 {pb}, stop:1 {sf})",
            "#2a3d38",
        ),
        "test": (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.2 {pb}, "
            f"stop:0.38 {pb}, stop:0.46 #223834, stop:0.52 #242e38, stop:0.58 #262630, "
            f"stop:0.66 {pb}, stop:0.86 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.16 {pb}, "
            f"stop:0.34 {pb}, stop:0.44 #2a403c, stop:0.5 #2c3642, stop:0.56 #2e2e3a, "
            f"stop:0.64 {pb}, stop:0.82 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.24 {pb}, "
            f"stop:0.5 #1e302c, stop:0.68 #22242c, stop:0.78 {pb}, stop:1 {sf})",
            "#2d3a38",
        ),
        "preview": (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.2 {pb}, "
            f"stop:0.4 {pb}, stop:0.52 #262e3a, stop:0.64 {pb}, stop:0.84 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.18 {pb}, "
            f"stop:0.36 {pb}, stop:0.5 #2e3846, stop:0.62 {pb}, stop:0.82 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.22 {pb}, "
            f"stop:0.5 #222830, stop:0.72 {pb}, stop:1 {sf})",
            "#2c333e",
        ),
        "region": (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.2 {pb}, "
            f"stop:0.42 {pb}, stop:0.52 #2e2820, stop:0.64 {pb}, stop:0.85 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.18 {pb}, "
            f"stop:0.38 {pb}, stop:0.5 #3a3228, stop:0.6 {pb}, stop:0.82 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.22 {pb}, "
            f"stop:0.5 #262220, stop:0.72 {pb}, stop:1 {sf})",
            "#3a342c",
        ),
        "clear": (
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.2 {pb}, "
            f"stop:0.42 {pb}, stop:0.52 #30262a, stop:0.64 {pb}, stop:0.85 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.18 {pb}, "
            f"stop:0.38 {pb}, stop:0.5 #3a3034, stop:0.6 {pb}, stop:0.82 {cb}, stop:1 {sf})",
            f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {sf}, stop:0.22 {pb}, "
            f"stop:0.5 #261f22, stop:0.72 {pb}, stop:1 {sf})",
            "#352c30",
        ),
    }
    gn, gh, gp, bd = g[role]
    return (
        f"QPushButton {{ background: {gn}; {base} border: 1px solid {bd}; }}"
        f"QPushButton:hover {{ background: {gh}; }}"
        f"QPushButton:pressed {{ background: {gp}; }}"
        f"QPushButton:disabled {{ color: {T.FG_DIM}; background: {T.PANEL_BG}; "
        f"border: 1px solid {T.BORDER_HAIR}; }}"
    )


def panel_secondary_button_qss(
    *,
    omit_inline_font: bool = False,
    font_size: str | None = None,
    letter_spacing: str | None = None,
    vertical_padding_px: int | None = None,
    horizontal_padding_px: int | None = None,
) -> str:
    """보조 액션(랩 초기화·종료·세션 리셋 등).

    ``omit_inline_font`` 가 True 면 폰트는 QSS 가 아니라 위젯 ``setFont`` 기준."""

    pv = (
        vertical_padding_px
        if vertical_padding_px is not None
        else scale_px_v(6)
    )
    ph = (
        horizontal_padding_px
        if horizontal_padding_px is not None
        else scale_px_h(12)
    )
    if omit_inline_font:
        inner = (
            f"padding: {pv}px {ph}px; text-align: center;"
        )
    else:
        fs = font_size if font_size is not None else T.spt(9.25)
        ls = letter_spacing if letter_spacing is not None else letter_spacing_qss()
        inner = (
            f"padding: {pv}px {ph}px; font-weight: 600; font-size: {fs}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: {ls}; "
            f"text-align: center;"
        )
    return (
        f"QPushButton {{ background: {T.BTN_BG}; color: {T.FG}; "
        f"border: 1px solid {T.BORDER_HAIR}; border-radius: {T.RADIUS_SM}; "
        f"{inner} }}"
        f"QPushButton:hover {{ background: {T.BTN_HOVER}; }}"
        f"QPushButton:pressed {{ background: {T.BTN_PRESSED}; }}"
        f"QPushButton:disabled {{ color: {T.FG_DIM}; background: {T.PANEL_BG}; }}"
    )


def kill_counter_session_reset_button_qss(
    *,
    omit_inline_font: bool = False,
    font_size: str | None = None,
    letter_spacing: str | None = None,
    vertical_padding_px: int | None = None,
    horizontal_padding_px: int | None = None,
) -> str:
    """세션만 지움 — 주의(되돌리기 쉬움), 앰버/틸 하이라이트의 유리 톤.

    ``omit_inline_font`` 가 True 면 ``font_size``/``letter_spacing`` 은 무시하고 QSS 에 글자 크기를 넣지 않음."""
    pv = (
        vertical_padding_px
        if vertical_padding_px is not None
        else scale_px_v(6)
    )
    ph = (
        horizontal_padding_px
        if horizontal_padding_px is not None
        else scale_px_h(9)
    )
    ss = T.SURFACE
    pb = T.PANEL_BG
    g0 = (
        f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 rgba(90, 72, 46, 0.96), stop:0.45 rgba(44, 38, 28, 0.95), "
        f"stop:1 rgba(20, 18, 14, 0.98))"
    )
    gh = (
        f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 rgba(120, 96, 58, 0.98), stop:0.5 rgba(52, 44, 32, 0.97), "
        f"stop:1 rgba(28, 24, 18, 0.99))"
    )
    gp = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {ss}, stop:1 {pb})"
    bd = "rgba(255, 190, 110, 0.42)"
    bdh = "rgba(255, 210, 140, 0.55)"
    if omit_inline_font:
        typo_in = f" padding: {pv}px {ph}px; text-align: center;"
    else:
        fs = font_size if font_size is not None else T.spt(9)
        ls = letter_spacing if letter_spacing is not None else letter_spacing_qss()
        typo_in = (
            f" padding: {pv}px {ph}px; font-weight: 600; font-size: {fs}; "
            f" font-family: {T.FONT_CSS_UI}; letter-spacing: {ls}; "
            f" text-align: center;"
        )
    return (
        f"QPushButton {{"
        f" background: {g0}; color: {T.FG};"
        f" border: 1px solid {bd}; border-radius: {T.RADIUS_SM};"
        f"{typo_in}"
        f"}}"
        f"QPushButton:hover {{ background: {gh}; border: 1px solid {bdh}; }}"
        f"QPushButton:pressed {{ background: {gp}; border: 1px solid {bd}; }}"
        f"QPushButton:disabled {{ color: {T.FG_DIM}; background: {T.PANEL_BG}; "
        f" border: 1px solid {T.BORDER_HAIR}; }}"
    )


def kill_counter_permanent_wipe_button_qss(
    *,
    omit_inline_font: bool = False,
    font_size: str | None = None,
    letter_spacing: str | None = None,
    vertical_padding_px: int | None = None,
    horizontal_padding_px: int | None = None,
) -> str:
    """영구 삭제 — 되돌릴 수 없음, 와인/크림슨 유리 톤.

    ``omit_inline_font`` 가 True 면 QSS 에 글자 크기 없음."""

    pv = (
        vertical_padding_px
        if vertical_padding_px is not None
        else scale_px_v(6)
    )
    ph = (
        horizontal_padding_px
        if horizontal_padding_px is not None
        else scale_px_h(9)
    )
    ss = T.SURFACE
    pb = T.PANEL_BG
    g0 = (
        f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 rgba(92, 28, 34, 0.97), stop:0.48 rgba(36, 18, 22, 0.96), "
        f"stop:1 rgba(14, 8, 10, 0.99))"
    )
    gh = (
        f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 rgba(120, 38, 46, 0.98), stop:0.5 rgba(48, 20, 26, 0.97), "
        f"stop:1 rgba(22, 10, 14, 0.99))"
    )
    gp = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {ss}, stop:1 {pb})"
    bd = "rgba(255, 95, 105, 0.58)"
    bdh = "rgba(255, 130, 142, 0.68)"
    if omit_inline_font:
        typo_in = f" padding: {pv}px {ph}px; text-align: center;"
    else:
        fs = font_size if font_size is not None else T.spt(9)
        ls = letter_spacing if letter_spacing is not None else letter_spacing_qss()
        typo_in = (
            f" padding: {pv}px {ph}px; font-weight: 600; font-size: {fs}; "
            f" font-family: {T.FONT_CSS_UI}; letter-spacing: {ls}; "
            f" text-align: center;"
        )
    return (
        f"QPushButton {{"
        f" background: {g0}; color: {T.FG};"
        f" border: 1px solid {bd}; border-radius: {T.RADIUS_SM};"
        f"{typo_in}"
        f"}}"
        f"QPushButton:hover {{ background: {gh}; border: 1px solid {bdh}; }}"
        f"QPushButton:pressed {{ background: {gp}; border: 1px solid {bd}; }}"
        f"QPushButton:disabled {{ color: {T.FG_DIM}; background: {T.PANEL_BG}; "
        f" border: 1px solid {T.BORDER_HAIR}; }}"
    )


def panel_primary_button_qss(
    *,
    font_size: str | None = None,
    letter_spacing: str | None = None,
    vertical_padding_px: int | None = None,
    horizontal_padding_px: int | None = None,
) -> str:
    """강조 1차 액션(예: 랩 시작/일시중지/재개).

    ``letter_spacing`` — omit for theme default; use ``fit_qpushbutton_text_width_qss`` output when fitting."""
    pv = (
        vertical_padding_px
        if vertical_padding_px is not None
        else scale_px_v(6)
    )
    ph = (
        horizontal_padding_px
        if horizontal_padding_px is not None
        else scale_px_h(14)
    )
    fs = font_size if font_size is not None else T.spt(9.5)
    ls = letter_spacing if letter_spacing is not None else letter_spacing_qss()
    return (
        f"QPushButton {{ background: {T.BTN_ON}; color: {T.FG}; text-align: center; "
        f"border: 1px solid {T.BTN_ON_BORDER}; border-radius: {T.RADIUS_SM}; "
        f"padding: {pv}px {ph}px; font-weight: 600; font-size: {fs}; "
        f"font-family: {T.FONT_CSS_UI}; letter-spacing: {ls}; }}"
        f"QPushButton:hover {{ background: {T.BTN_ON_HOVER}; }}"
        f"QPushButton:pressed {{ background: {T.BTN_PRESSED}; }}"
        f"QPushButton:disabled {{ color: {T.FG_DIM}; background: {T.PANEL_BG}; "
        f"border: 1px solid {T.BORDER_HAIR}; }}"
    )


def make_settings_hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(max(1, scale_px_v(1)))
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
    """라벨+컨트롤 묶음을 가로 가운데 정렬(설정 허브 패널 공통)."""
    row = QHBoxLayout()
    row.setSpacing(scale_px_h(10))
    row.addStretch(1)
    if (label_text or "").strip():
        lab = QLabel(label_text)
        lab.setWordWrap(True)
        lab.setMaximumWidth(scale_px_h(360))
        lab.setStyleSheet(settings_field_label_style())
        settings_label_align_center_h(lab)
        lab.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        row.addWidget(lab, 0, Qt.AlignmentFlag.AlignVCenter)
    if controls:
        box = QHBoxLayout()
        box.setSpacing(scale_px_h(8))
        for w in controls:
            w.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
            box.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
        row.addLayout(box, 0)
    row.addStretch(1)
    parent_lay.addLayout(row)


def add_template_similarity_row(
    parent_lay: QVBoxLayout,
    cur: QLabel,
    thr_spin: QWidget,
    *,
    pipela_mod: Any | None = None,
    probe_capture_kind: str | None = None,
    typography_bundle: TypographyStyleBundle | None = None,
) -> None:
    """이미지 템플릿 유사도: `실시간 n.nn / 기준 n.nn` (임계는 스핀) — 가운데 뭉쳐 배치."""
    st_em = settings_template_metric_muted_label_style(emphasis=True)
    st_m = settings_template_metric_muted_label_style()
    row = QHBoxLayout()
    row.setSpacing(scale_px_h(8))
    if pipela_mod is not None and probe_capture_kind is not None:
        from pipela_qt.template_section_probe_frame import TemplateProbeLiveCaptionLabel

        live = TemplateProbeLiveCaptionLabel(pipela_mod, probe_capture_kind)
        if typography_bundle is not None:
            typography_bundle.add(live.refresh_font)
    else:
        live = QLabel("실시간")
        live.setStyleSheet(st_em)
        settings_label_align_center_h(live)
    live.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    mid = QLabel("/")
    mid.setStyleSheet(st_m)
    settings_label_align_center_h(mid)
    mid.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    thr_lbl = QLabel("기준")
    thr_lbl.setStyleSheet(st_em)
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
    _spin_qss = settings_template_similarity_value_spin_qss()
    thr_spin.setStyleSheet(_spin_qss)
    if typography_bundle is not None:
        typography_bundle.add(lambda w=thr_spin: w.setStyleSheet(settings_template_similarity_value_spin_qss()))
    from pipela_qt.template_section_probe_frame import TemplateLiveScoreReadout as _TLSim

    if isinstance(cur, _TLSim):
        cur.refresh_metric_font()
        if typography_bundle is not None:
            typography_bundle.add(cur.refresh_metric_font)
    parent_lay.addLayout(row)


def add_settings_control_row_centered(
    parent_lay: QVBoxLayout,
    *widgets: QWidget,
    spacing_px: int | None = None,
) -> None:
    """라디오·토글 등 가운데 정렬 한 줄."""
    row = QHBoxLayout()
    row.setSpacing(scale_px_h(spacing_px if spacing_px is not None else 10))
    row.addStretch(1)
    for w in widgets:
        row.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)
    row.addStretch(1)
    parent_lay.addLayout(row)
