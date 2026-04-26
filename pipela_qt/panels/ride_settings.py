"""Ride 설정 — ride_threshold·image_score·타겟 템플릿."""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from pipela_core.display_timing import display_tick_ms
from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_float
from pipela_qt import theme as T
from pipela_qt.panels.image_preview import pixmap_from_bgr
from pipela_qt.panels.settings_chrome import (
    add_template_similarity_row,
    configure_settings_scroll_area,
    make_settings_hline,
    settings_footnote_style,
    settings_label_align_center_h,
    settings_page_title_style,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.ui_adaptive import scale_px
from pipela_qt.qt_capture import attach_template_toolbar
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox
from pipela_qt.template_section_probe_frame import TemplateLiveScoreReadout
from pipela_qt.typography_refresh_support import TypographyStyleBundle

_THR_MIN = 0.1
_THR_MAX = 1.0


class RideSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._typo = TypographyStyleBundle()

        outer = QVBoxLayout(self)
        self._outer = outer
        outer.setSpacing(settings_root_vertical_spacing())
        outer.setContentsMargins(0, 0, 0, 0)
        t1 = QLabel("Ride 설정")
        t1.setStyleSheet(settings_page_title_style())
        self._typo.add(lambda w=t1: w.setStyleSheet(settings_page_title_style()))
        settings_label_align_center_h(t1)
        outer.addWidget(t1)
        outer.addWidget(make_settings_hline())

        scroll = QScrollArea()
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        self._inner_lay = lay
        lay.setSpacing(settings_root_vertical_spacing())
        st = QLabel("Ride 타겟 · 테스트")
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
        attach_template_toolbar(lay, self._m, "ride_target", self._tick)
        self._cur = TemplateLiveScoreReadout(self._m, "ride_target")
        self._typo.add(lambda w=self._cur: w.setStyleSheet(f"font-family: {T.FONT_CSS_UI};"))
        self._thr = DragDoubleSpinBox()
        self._thr.setRange(_THR_MIN, _THR_MAX)
        self._thr.setDecimals(2)
        self._thr.setSingleStep(0.01)
        self._thr.setMaximumWidth(scale_px(88))
        self._thr.valueChanged.connect(self._commit_thr)
        add_template_similarity_row(lay, self._cur, self._thr)
        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

    def apply_scaled_typography(self) -> None:
        self._outer.setSpacing(settings_root_vertical_spacing())
        self._inner_lay.setSpacing(settings_root_vertical_spacing())
        self._thumb.setMinimumSize(scale_px(120), scale_px(72))
        self._thr.setMaximumWidth(scale_px(88))
        self._typo.apply()
        self._tick()

    def _commit_thr(self) -> None:
        self._m.ride_threshold = float(self._thr.value())
        sync_registry_snapshot_from_module(self._m)
        self._m.schedule_save_config()

    def _reload(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        self._thr.blockSignals(True)
        self._thr.setValue(
            max(
                _THR_MIN,
                min(_THR_MAX, snapshot_float(snap, "ride_threshold", float(m.ride_threshold))),
            )
        )
        self._thr.blockSignals(False)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._reload()
        self._timer.start(max(16, int(display_tick_ms())))

    def hideEvent(self, e) -> None:
        self._timer.stop()
        super().hideEvent(e)

    def _tick(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        self._cur.setText(f"{float(m.image_score):.2f}")
        if not self._thr.hasFocus():
            self._thr.blockSignals(True)
            self._thr.setValue(
                max(
                    _THR_MIN,
                    min(
                        _THR_MAX,
                        snapshot_float(snap, "ride_threshold", float(m.ride_threshold)),
                    ),
                )
            )
            self._thr.blockSignals(False)
        path = m.RIDE_TARGET_IMAGE_PATH
        self._path_lbl.setText(f"템플릿: {os.path.basename(path) if path else '—'}")
        bgr = m.load_image_data(path, "ride_target_image_data")
        pm = pixmap_from_bgr(bgr, scale_px(200), scale_px(120))
        if pm:
            self._thumb.setText("")
            self._thumb.setPixmap(pm)
            self._thumb.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;")
        else:
            self._thumb.clear()
            self._thumb.setText("없음")
            self._thumb.setStyleSheet(
                f"background: {T.PANEL_BG}; color: {T.FG_DIM}; border-radius: {scale_px(4)}px;",
            )
