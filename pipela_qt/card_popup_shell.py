"""프레임리스 카드 팝업 공통 껍데기 — 섀도·헤더·닫기(×)·Esc."""

from __future__ import annotations

from html import escape

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pipela_qt import theme as T
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v

# 경고 본문 2번째 줄 — 제목 대비 살짝 낮은 골드톤(가독 유지)
_WARN_BODY_MUTED = "#c4b24a"


def dialog_body_html(
    text: str,
    *,
    color: str,
    font_px: int | None = None,
    line_height: float = 1.58,
) -> str:
    """카드 다이얼로그 본문용 RichText — 한글 줄바꿈·여러 줄(\\n→br) 자연스럽게."""
    fp = scale_px_v(11) if font_px is None else max(8, int(font_px))
    # ``FONT_CSS_UI`` 는 따옴표가 많아 QLabel RichText 속성을 깨므로 본문만 단순 스택.
    ff = "Malgun Gothic, Gulim, sans-serif"
    body = escape((text or "").strip()).replace("\n", "<br/>")
    lh = line_height
    return (
        "<html><body style='margin:0'>"
        f"<p style='margin:0;color:{color};font-size:{fp}px;font-family:{ff};"
        f"line-height:{lh};word-break:keep-all;'>"
        f"{body}</p>"
        "</body></html>"
    )


def _confirm_dialog_warn_message_html(message: str) -> str:
    """경고 톤 확인창 본문 — 첫 줄 강조·둘째 줄 보조(HTML)."""
    text = (message or "").strip()
    if not text:
        return ""
    fs = scale_px_v(11)
    fs2 = max(scale_px_v(10), fs - 1)
    ff = "Malgun Gothic, Gulim, sans-serif"
    _wb = "word-break:keep-all;"
    if "\n" in text:
        first, rest = text.split("\n", 1)
        return (
            f"<p style='margin:0 0 {scale_px_v(8)}px 0; color:{T.STATUS_WARN}; font-size:{fs}px; "
            f"font-weight:700; line-height:1.52; {_wb} font-family:{ff};'>{escape(first)}</p>"
            f"<p style='margin:0; color:{_WARN_BODY_MUTED}; font-size:{fs2}px; "
            f"font-weight:600; line-height:1.52; letter-spacing:0.01em; {_wb} font-family:{ff};'>"
            f"{escape(rest.strip())}</p>"
        )
    return (
        f"<p style='margin:0; color:{T.STATUS_WARN}; font-size:{fs}px; "
        f"font-weight:700; line-height:1.52; {_wb} font-family:{ff};'>{escape(text)}</p>"
    )


def center_card_popup(dlg: QDialog, parent: QWidget | None) -> None:
    dlg.adjustSize()
    if parent is not None:
        g = parent.window().frameGeometry()
        cp = g.center()
    else:
        from PyQt6.QtGui import QGuiApplication

        scr = QGuiApplication.primaryScreen()
        cp = scr.availableGeometry().center() if scr is not None else None
    if cp is None:
        return
    # 프레임리스·섀도 카드는 ``geometry()`` 기준이 체감 위치와 더 잘 맞음.
    geo = dlg.geometry()
    geo.moveCenter(cp)
    dlg.move(geo.topLeft())


def confirm_card_dialog(
    parent: QWidget | None,
    *,
    title: str,
    message: str,
    confirm_text: str = "예",
    cancel_text: str = "아니오",
    message_tone: str = "muted",
    default_confirm: bool = False,
) -> bool:
    """프레임리스 카드 + 예/아니오. ``True`` = 확인(``accept``)."""
    from pipela_qt.panels.settings_chrome import (
        panel_primary_button_qss,
        panel_secondary_button_qss,
    )

    parent_win = parent.window() if parent is not None else None
    chrome_t: str | None = None
    if message_tone == "warn":
        chrome_t = "warn"
    elif message_tone == "danger":
        chrome_t = "danger"
    dlg = CardFramelessDialog(
        parent_win,
        title=title,
        modal=True,
        chrome_tone=chrome_t,
    )
    dlg.setMinimumWidth(scale_px_h(320))
    lay = dlg.content_layout()
    body = QLabel()
    body.setWordWrap(True)
    body.setTextFormat(Qt.TextFormat.RichText)
    if message_tone == "warn":
        body.setText(_confirm_dialog_warn_message_html(message))
    else:
        if message_tone == "danger":
            col = T.STATUS_ERR
        else:
            col = T.FG_MUTED
        body.setText(dialog_body_html(message, color=col))
    lay.addWidget(body)

    row = QHBoxLayout()
    row.addStretch(1)
    no_b = QPushButton(cancel_text)
    no_b.setCursor(Qt.CursorShape.PointingHandCursor)
    no_b.setStyleSheet(panel_secondary_button_qss())
    no_b.clicked.connect(dlg.reject)
    yes_b = QPushButton(confirm_text)
    yes_b.setCursor(Qt.CursorShape.PointingHandCursor)
    yes_b.setStyleSheet(panel_primary_button_qss())
    yes_b.clicked.connect(dlg.accept)
    row.addWidget(no_b)
    row.addWidget(yes_b)
    lay.addLayout(row)

    if default_confirm:
        yes_b.setDefault(True)
    else:
        no_b.setDefault(True)

    center_card_popup(dlg, parent)
    return dlg.exec() == QDialog.DialogCode.Accepted


class CardFramelessDialog(QDialog):
    """타이틀바 없는 둥근 카드 + 그림자. 본문은 ``content_layout()`` 에 위젯 추가."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        title: str,
        modal: bool = True,
        chrome_tone: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._chrome_tone: str | None = chrome_tone
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(modal)

        self._root_layout = QVBoxLayout(self)
        self._root_layout.setSpacing(0)

        self._card = QFrame()
        self._card.setObjectName("PipelaCardPopupShell")

        shadow = QGraphicsDropShadowEffect(self._card)
        shadow.setColor(QColor(0, 0, 0, 100))
        self._shadow = shadow
        self._card.setGraphicsEffect(shadow)

        self._card_inner_layout = QVBoxLayout(self._card)

        self._hdr_layout = QHBoxLayout()
        self._title_lbl = QLabel(title)
        self._title_lbl.setWordWrap(True)

        self._hdr_layout.addWidget(self._title_lbl, 1)
        self._close_btn = QPushButton("×")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.reject)
        self._hdr_layout.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignTop)
        self._card_inner_layout.addLayout(self._hdr_layout)

        self._content = QVBoxLayout()
        self._card_inner_layout.addLayout(self._content)

        self._root_layout.addWidget(self._card)

        self.apply_scaled_chrome()

        from pipela_qt.dialog_dismiss_on_outside import register_dialog_dismiss_on_outside_click

        register_dialog_dismiss_on_outside_click(self)

    def apply_scaled_chrome(self) -> None:
        """외곽 카드·섀도·헤더·닫기 — ``refresh_pipela_typography`` 에서 현재 DPI/pt 기준 재적용."""
        ct = self._chrome_tone
        m = scale_px_v(18)
        self._root_layout.setContentsMargins(m, m, m, m)
        r_br = scale_px_v(14)
        if ct == "warn":
            self._card.setStyleSheet(
                f"#PipelaCardPopupShell {{"
                f"background: {T.CARD_BG};"
                f"border: 1px solid {T.BORDER};"
                f"border-left: 3px solid {T.STATUS_WARN};"
                f"border-radius: {r_br}px;"
                f"}}",
            )
        elif ct == "danger":
            self._card.setStyleSheet(
                f"#PipelaCardPopupShell {{"
                f"background: {T.CARD_BG};"
                f"border: 1px solid {T.BORDER};"
                f"border-left: 3px solid {T.STATUS_ERR};"
                f"border-radius: {r_br}px;"
                f"}}",
            )
        else:
            self._card.setStyleSheet(
                f"#PipelaCardPopupShell {{"
                f"background: {T.CARD_BG};"
                f"border: 1px solid {T.BORDER};"
                f"border-radius: {r_br}px;"
                f"}}",
            )
        self._shadow.setBlurRadius(scale_px_v(28))
        self._shadow.setOffset(0, scale_px_v(6))
        _ip_h = scale_px_h(14)
        _ip_v = scale_px_v(14)
        self._card_inner_layout.setContentsMargins(_ip_h, _ip_v, _ip_h, _ip_v)
        self._card_inner_layout.setSpacing(scale_px_v(12))
        self._hdr_layout.setSpacing(scale_px_h(8))

        fs_t = scale_px_v(13)
        if ct == "warn":
            self._title_lbl.setStyleSheet(
                f"color: {T.STATUS_WARN}; font-weight: 800; font-size: {fs_t}px; "
                f"font-family: {T.FONT_CSS_UI}; letter-spacing: 0.03em;",
            )
        elif ct == "danger":
            self._title_lbl.setStyleSheet(
                f"color: {T.STATUS_ERR}; font-weight: 800; font-size: {fs_t}px; "
                f"font-family: {T.FONT_CSS_UI}; letter-spacing: 0.03em;",
            )
        else:
            self._title_lbl.setStyleSheet(
                f"color: {T.FG}; font-weight: 600; font-size: {fs_t}px;",
            )

        csz = scale_px_v(30)
        self._close_btn.setFixedSize(csz, csz)
        self._close_btn.setStyleSheet(
            f"QPushButton {{"
            f"background: {T.SURFACE}; color: {T.FG_MUTED};"
            f"border: 1px solid {T.BORDER_HAIR}; border-radius: {scale_px_v(8)}px;"
            f"font-size: {scale_px_v(18)}px;"
            f"}}"
            f"QPushButton:hover {{ background: {T.CARD_HOVER}; color: {T.FG}; }}",
        )

        self._content.setSpacing(scale_px_v(8))

    def set_header_title(self, text: str) -> None:
        self._title_lbl.setText(text)

    def content_layout(self) -> QVBoxLayout:
        return self._content

    def keyPressEvent(self, e) -> None:  # noqa: N802
        if e.key() == Qt.Key.Key_Escape:
            self.reject()
            e.accept()
            return
        super().keyPressEvent(e)


def refresh_open_card_frameless_dialogs_scaled() -> None:
    """표시 중인 ``CardFramelessDialog`` 카드 크롬 — ``refresh_pipela_typography`` 연동용."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        if isinstance(w, CardFramelessDialog) and w.isVisible():
            try:
                w.apply_scaled_chrome()
            except Exception:
                pass


def message_card_dialog(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    tone: str = "info",
) -> None:
    """단일 «확인» — ``CardFramelessDialog``·섀도·바깥 클릭 닫기. ``tone``: ``info`` | ``warn`` | ``danger``."""
    from pipela_qt.panels.settings_chrome import panel_primary_button_qss

    parent_win = parent.window() if parent is not None else None
    chrome: str | None = None
    if tone == "warn":
        chrome = "warn"
    elif tone == "danger":
        chrome = "danger"
    dlg = CardFramelessDialog(parent_win, title=title, modal=True, chrome_tone=chrome)
    dlg.setMinimumWidth(scale_px_h(300))
    lay = dlg.content_layout()
    body = QLabel()
    body.setWordWrap(True)
    body.setTextFormat(Qt.TextFormat.RichText)
    if tone == "danger":
        body_col = T.FG
    elif tone == "warn":
        body_col = T.STATUS_WARN
    else:
        body_col = T.FG_MUTED
    body.setText(dialog_body_html((text or "").strip(), color=body_col))
    lay.addWidget(body)
    row = QHBoxLayout()
    row.addStretch(1)
    ok_b = QPushButton("확인")
    ok_b.setCursor(Qt.CursorShape.PointingHandCursor)
    ok_b.setStyleSheet(panel_primary_button_qss())
    ok_b.clicked.connect(dlg.accept)
    row.addWidget(ok_b)
    lay.addLayout(row)
    ok_b.setDefault(True)
    center_card_popup(dlg, parent)
    dlg.exec()


def tri_choice_card_dialog(
    parent: QWidget | None,
    *,
    title: str,
    message: str,
    yes_text: str = "예",
    no_text: str = "아니오",
    cancel_text: str = "취소",
    message_tone: str = "muted",
    default_which: str = "yes",
) -> bool | None:
    """예 / 아니오 / 취소 카드. ``True``·``False``·``None`` (취소·Esc·×)."""
    from pipela_qt.panels.settings_chrome import (
        panel_primary_button_qss,
        panel_secondary_button_qss,
    )

    parent_win = parent.window() if parent is not None else None
    chrome: str | None = None
    if message_tone == "warn":
        chrome = "warn"
    elif message_tone == "danger":
        chrome = "danger"

    dlg = CardFramelessDialog(parent_win, title=title, modal=True, chrome_tone=chrome)
    dlg.setMinimumWidth(scale_px_h(340))
    lay = dlg.content_layout()
    body = QLabel()
    body.setWordWrap(True)
    body.setTextFormat(Qt.TextFormat.RichText)
    if message_tone == "danger":
        col = T.STATUS_ERR
    elif message_tone == "warn":
        col = T.STATUS_WARN
    else:
        col = T.FG_MUTED
    body.setText(dialog_body_html((message or "").strip(), color=col))
    lay.addWidget(body)

    outcome: bool | None = None

    def _yes() -> None:
        nonlocal outcome
        outcome = True
        dlg.accept()

    def _no() -> None:
        nonlocal outcome
        outcome = False
        dlg.accept()

    def _cancel() -> None:
        nonlocal outcome
        outcome = None
        dlg.reject()

    row = QHBoxLayout()
    row.addStretch(1)
    cancel_b = QPushButton(cancel_text)
    cancel_b.setCursor(Qt.CursorShape.PointingHandCursor)
    cancel_b.setStyleSheet(panel_secondary_button_qss())
    cancel_b.clicked.connect(_cancel)
    no_b = QPushButton(no_text)
    no_b.setCursor(Qt.CursorShape.PointingHandCursor)
    no_b.setStyleSheet(panel_secondary_button_qss())
    no_b.clicked.connect(_no)
    yes_b = QPushButton(yes_text)
    yes_b.setCursor(Qt.CursorShape.PointingHandCursor)
    yes_b.setStyleSheet(panel_primary_button_qss())
    yes_b.clicked.connect(_yes)
    row.addWidget(cancel_b)
    row.addWidget(no_b)
    row.addWidget(yes_b)
    lay.addLayout(row)

    if default_which == "no":
        no_b.setDefault(True)
    elif default_which == "cancel":
        cancel_b.setDefault(True)
    else:
        yes_b.setDefault(True)

    center_card_popup(dlg, parent)
    dlg.exec()
    if dlg.result() != QDialog.DialogCode.Accepted:
        return None
    return outcome
