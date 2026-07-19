"""테서렉트(Tesseract) 설치 안내 — 설정 허브 푸터에서 열 수 있음."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import (
    settings_footnote_style,
    settings_label_align_center_h,
)
from pipela_qt.resizable_text_widgets import ResizableTextEdit
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_adaptive import letter_spacing_qss, qss_pad_all, scale_px_h, scale_px_v


def _help_root_spacing() -> int:
    return scale_px_v(14)


def _help_callout_qss(*, pad_px: float = 14.0) -> str:
    pad = qss_pad_all(pad_px)
    br = max(1, scale_px_v(3))
    return (
        f"QFrame#helpCallout {{ background: {T.SURFACE}; "
        f"border: 1px solid {T.BORDER_HAIR}; border-left: {br}px solid {T.ACCENT}; "
        f"border-radius: {T.RADIUS_SM}; {pad} }}"
    )


def _help_body_qss(*, pad_px: float = 8.0) -> str:
    pad = qss_pad_all(pad_px)
    return (
        f"QFrame#helpBody {{ background: {T.PANEL_BG}; "
        f"border: 1px solid {T.BORDER_HAIR}; border-radius: {max(4, scale_px_v(6))}px; "
        f"{pad} }}"
    )


def _help_badge_style() -> str:
    return (
        f"font-family: {T.FONT_CSS_UI}; text-align: center; "
        f"color: {T.ACCENT}; font-weight: 700; font-size: {T.spt(8.25)}; "
        f"letter-spacing: {letter_spacing_qss()}; "
        f"background: {T.ACCENT_SOFT}; border-radius: {T.RADIUS_PILL}; "
        f"padding: {scale_px_v(4)}px {scale_px_v(10)}px;"
    )


def _help_copy_button_qss() -> str:
    r = T.RADIUS_SM
    p_v, p_h = scale_px_v(8), scale_px_v(14)
    return (
        f"QPushButton {{ color: {T.ACCENT}; background: transparent; "
        f"border: 1px solid {T.ACCENT}; border-radius: {r}; "
        f"padding: {p_v}px {p_h}px; font-weight: 600; font-size: {T.spt(9.25)}; }}"
        f"QPushButton:hover {{ background: {T.ACCENT_SOFT}; }}"
        f"QPushButton:pressed {{ background: rgba(61, 212, 201, 0.22); }}"
    )


class TesseractSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._typo = TypographyStyleBundle()
        root = QVBoxLayout(self)
        self._root_lay = root
        root.setSpacing(_help_root_spacing())
        root.setContentsMargins(0, 0, 0, 0)

        callout = QFrame()
        callout.setObjectName("helpCallout")
        callout.setStyleSheet(_help_callout_qss())
        self._callout = callout
        card = QVBoxLayout(callout)
        _cm = scale_px_v(14)
        card.setContentsMargins(_cm, _cm, _cm, _cm)
        card.setSpacing(scale_px_v(10))

        badge = QLabel("도움말")
        badge.setStyleSheet(_help_badge_style())
        settings_label_align_center_h(badge)
        self._badge = badge
        self._typo.add(lambda w=badge: w.setStyleSheet(_help_badge_style()))
        card.addWidget(badge, 0, Qt.AlignmentFlag.AlignHCenter)

        body = QFrame()
        body.setObjectName("helpBody")
        body.setStyleSheet(_help_body_qss())
        body_l = QVBoxLayout(body)
        _bm = scale_px_v(8)
        body_l.setContentsMargins(_bm, _bm, _bm, _bm)
        self._txt = ResizableTextEdit()
        self._txt.setReadOnly(True)
        self._txt.setPlainText(pipela_mod._kill_counter_install_help_text())
        self._txt.setMinimumHeight(scale_px_v(220))
        self._txt.setStyleSheet(
            f"font-family: {T.FONT_CSS_UI}; font-size: {T.spt(9.25)}; color: {T.FG_MUTED}; "
            f"background: transparent; border: none;",
        )
        self._typo.add(
            lambda w=self._txt: w.setStyleSheet(
                f"font-family: {T.FONT_CSS_UI}; font-size: {T.spt(9.25)}; color: {T.FG_MUTED}; "
                f"background: transparent; border: none;",
            ),
        )
        body_l.addWidget(self._txt, 1)
        card.addWidget(body, 1)

        foot = QVBoxLayout()
        foot.setSpacing(scale_px_v(10))
        hint = QLabel("설치 후에도 인식이 안 되면 이 블록을 그대로 공유해 주세요.")
        hint.setWordWrap(True)
        hint.setStyleSheet(settings_footnote_style())
        self._foot_hint = hint
        self._typo.add(lambda w=hint: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(hint)
        foot.addWidget(hint)
        foot_btns = QHBoxLayout()
        foot_btns.setSpacing(scale_px_h(10))
        foot_btns.addStretch(1)
        b = QPushButton("안내 전체 복사")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(_help_copy_button_qss())
        self._copy_btn = b
        self._typo.add(lambda w=b: w.setStyleSheet(_help_copy_button_qss()))
        b.clicked.connect(lambda: QGuiApplication.clipboard().setText(self._txt.toPlainText()))
        foot_btns.addWidget(b, 0, Qt.AlignmentFlag.AlignHCenter)
        foot_btns.addStretch(1)
        foot.addLayout(foot_btns)
        card.addLayout(foot)

        root.addWidget(callout, 1)

    def apply_scaled_typography(self) -> None:
        self._root_lay.setSpacing(_help_root_spacing())
        self._callout.setStyleSheet(_help_callout_qss())
        self._txt.setMinimumHeight(scale_px_v(220))
        self._typo.apply()
