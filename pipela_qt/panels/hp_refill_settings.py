"""HP Refill 설정 — 임계값·키·실시간 점수·썸네일 (`hp_refill_threshold` 레지)."""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QKeyEvent, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pipela_core.display_timing import display_tick_ms
from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_float, snapshot_int
from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    add_template_similarity_row,
    configure_settings_scroll_area,
    make_settings_hline,
    settings_footnote_style,
    settings_label_align_center_h,
    settings_page_title_style,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.qt_capture import attach_template_toolbar
from pipela_qt.resizable_text_widgets import ResizableLineEdit
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox
from pipela_qt.template_section_probe_frame import TemplateLiveScoreReadout
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_adaptive import scale_px

_THR_MIN = 0.1
_THR_MAX = 1.0


def _scaled_pixmap(path: str, max_w: int, max_h: int) -> QPixmap | None:
    if not path or not os.path.isfile(path):
        return None
    img = QImage(path)
    if img.isNull():
        return None
    pm = QPixmap.fromImage(img)
    return pm.scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class HpRefillSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._capturing = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._typo = TypographyStyleBundle()

        outer = QVBoxLayout(self)
        self._outer = outer
        outer.setSpacing(settings_root_vertical_spacing())
        outer.setContentsMargins(0, 0, 0, 0)

        title = QLabel("HP Refill 설정")
        title.setStyleSheet(settings_page_title_style())
        self._typo.add(lambda w=title: w.setStyleSheet(settings_page_title_style()))
        settings_label_align_center_h(title)
        outer.addWidget(title)

        outer.addWidget(make_settings_hline())

        scroll = QScrollArea()
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        self._inner_lay = lay
        lay.setSpacing(settings_root_vertical_spacing())

        st = QLabel("HP 바 · 체력 막대")
        st.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st)
        lay.addWidget(st)
        self._path_lbl = QLabel("")
        self._path_lbl.setWordWrap(True)
        self._path_lbl.setStyleSheet(settings_footnote_style())
        self._typo.add(
            lambda w=self._path_lbl: w.setStyleSheet(settings_footnote_style()),
        )
        settings_label_align_center_h(self._path_lbl)
        lay.addWidget(self._path_lbl)
        self._thumb = QLabel()
        self._thumb.setMinimumSize(scale_px(120), scale_px(72))
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;")
        lay.addWidget(self._thumb)
        attach_template_toolbar(lay, self._m, "hp_zkey", self._tick)

        self._cur_lbl = TemplateLiveScoreReadout(self._m, "hp_zkey")
        self._typo.add(
            lambda w=self._cur_lbl: w.setStyleSheet(f"font-family: {T.FONT_CSS_UI};"),
        )
        self._thr = DragDoubleSpinBox()
        self._thr.setRange(_THR_MIN, _THR_MAX)
        self._thr.setDecimals(2)
        self._thr.setSingleStep(0.01)
        self._thr.setMaximumWidth(scale_px(88))
        self._thr.valueChanged.connect(self._commit_thr)
        add_template_similarity_row(lay, self._cur_lbl, self._thr)

        lay.addWidget(make_settings_hline())

        key_t = QLabel("감지 시 누를 키")
        key_t.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=key_t: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(key_t)
        lay.addWidget(key_t)
        self._key_disp = ResizableLineEdit()
        self._key_disp.setReadOnly(True)
        self._key_disp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._key_disp.setMaximumWidth(scale_px(140))
        self._cap_btn = QPushButton("키 입력")
        self._cap_btn.clicked.connect(self._toggle_key_capture)
        add_settings_field_row(lay, "키", self._key_disp, self._cap_btn)
        self._key_hint = QLabel(
            "「키 입력」 후 원하는 키를 한 번 누릅니다. 키 입력 중 Esc는 취소.",
        )
        self._key_hint.setWordWrap(True)
        self._key_hint.setStyleSheet(settings_footnote_style())
        self._typo.add(
            lambda w=self._key_hint: w.setStyleSheet(settings_footnote_style()),
        )
        settings_label_align_center_h(self._key_hint)
        lay.addWidget(self._key_hint)

        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        self._reload_fields()

    def apply_scaled_typography(self) -> None:
        self._outer.setSpacing(settings_root_vertical_spacing())
        self._inner_lay.setSpacing(settings_root_vertical_spacing())
        self._thumb.setMinimumSize(scale_px(120), scale_px(72))
        self._thr.setMaximumWidth(scale_px(88))
        self._key_disp.setMaximumWidth(scale_px(140))
        self._typo.apply()
        self._tick()

    def _commit_thr(self) -> None:
        self._m.hp_refill_threshold = float(self._thr.value())
        sync_registry_snapshot_from_module(self._m)
        self._m.schedule_save_config()

    def _reload_fields(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        self._thr.blockSignals(True)
        self._thr.setValue(
            max(
                _THR_MIN,
                min(
                    _THR_MAX,
                    snapshot_float(snap, "hp_refill_threshold", float(m.hp_refill_threshold)),
                ),
            )
        )
        self._thr.blockSignals(False)
        kc = snapshot_int(snap, "hp_refill_key_code", int(m.hp_refill_key_code))
        self._key_disp.setText(m.vk_to_display_name(int(kc) & 0xFF))

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._reload_fields()
        self._timer.start(max(16, int(display_tick_ms())))

    def hideEvent(self, e) -> None:
        self._timer.stop()
        if self._capturing:
            self._end_capture(cancel=True)
        super().hideEvent(e)

    def _tick(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        self._cur_lbl.setText(f"{float(m.hp_refill_detection_score):.2f}")
        if not self._thr.hasFocus():
            self._thr.blockSignals(True)
            self._thr.setValue(
                max(
                    _THR_MIN,
                    min(
                        _THR_MAX,
                        snapshot_float(snap, "hp_refill_threshold", float(m.hp_refill_threshold)),
                    ),
                )
            )
            self._thr.blockSignals(False)
        if not self._capturing:
            kc = snapshot_int(snap, "hp_refill_key_code", int(m.hp_refill_key_code))
            self._key_disp.setText(m.vk_to_display_name(int(kc) & 0xFF))
        path = m.HP_REFILL_ZKEY_IMAGE_PATH
        self._path_lbl.setText(f"템플릿: {os.path.basename(path) if path else '—'}")
        pm = _scaled_pixmap(path, scale_px(200), scale_px(120))
        if pm:
            self._thumb.setPixmap(pm)
            self._thumb.setText("")
            self._thumb.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;")
        else:
            self._thumb.clear()
            self._thumb.setText("없음")
            self._thumb.setStyleSheet(
                f"background: {T.PANEL_BG}; color: {T.FG_DIM}; border-radius: {scale_px(4)}px;",
            )

    def _toggle_key_capture(self) -> None:
        if self._capturing:
            self._end_capture(cancel=True)
            return
        self._capturing = True
        self._cap_btn.setText("키를 누르세요…")
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.grabKeyboard()

    def _end_capture(self, *, cancel: bool) -> None:
        if not self._capturing:
            return
        self._capturing = False
        self.releaseKeyboard()
        self._cap_btn.setText("키 입력")
        if not cancel:
            self._m.schedule_save_config()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._capturing:
            if event.key() == Qt.Key.Key_Escape:
                self._end_capture(cancel=True)
                event.accept()
                return
            vk = int(event.nativeVirtualKey()) & 0xFF
            if vk == 0:
                event.ignore()
                return
            self._m.hp_refill_key_code = vk
            sync_registry_snapshot_from_module(self._m)
            self._key_disp.setText(self._m.vk_to_display_name(vk))
            self._end_capture(cancel=False)
            event.accept()
            return
        super().keyPressEvent(event)
