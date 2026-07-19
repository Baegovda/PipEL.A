"""Ride 설정 — ride_threshold·image_score·타겟 템플릿."""

from __future__ import annotations

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
from pipela_qt.panels.template_last_match_thumb import (
    append_side_by_side_target_and_match_previews,
    fit_template_thumb_label_to_pixmap,
    thumb_preview_max_wh,
    thumb_preview_slot_min_wh,
    update_last_match_thumbnail,
)
from pipela_qt.panels.thumbnail_preview_dialog import attach_template_thumbnail_click_preview
from pipela_qt.panels.settings_chrome import (
    add_template_similarity_row,
    configure_settings_scroll_area,
    settings_label_align_center_h,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v
from pipela_qt.qt_capture import attach_template_toolbar
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox
from pipela_qt.template_section_probe_frame import (
    TemplateLiveScoreReadout,
    TemplateProbeSectionFrame,
)
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

        scroll = QScrollArea()
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        self._inner_lay = lay
        lay.setSpacing(settings_root_vertical_spacing())
        ride_fr = TemplateProbeSectionFrame(self._m, "ride_target", inner)
        self._ride_probe_frame = ride_fr
        ride_blk = ride_fr.content_layout()
        st = QLabel("Ride 타겟 · 테스트")
        st.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st)
        ride_blk.addWidget(st)
        _tmw, _tmh = thumb_preview_slot_min_wh()
        self._thumb = QLabel()
        self._thumb.setMinimumSize(_tmw, _tmh)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px_v(4)}px;")
        attach_template_thumbnail_click_preview(
            self._thumb,
            lambda: str(getattr(self._m, "RIDE_TARGET_IMAGE_PATH", "") or ""),
        )
        self._last_hit_cap, self._last_hit_thumb = append_side_by_side_target_and_match_previews(
            ride_blk,
            self._typo,
            self._thumb,
            pipela_mod=self._m,
            hit_kind="ride_target",
        )
        self._cur = TemplateLiveScoreReadout(self._m, "ride_target")
        self._typo.add(self._cur.refresh_metric_font)
        self._thr = DragDoubleSpinBox()
        self._thr.setRange(_THR_MIN, _THR_MAX)
        self._thr.setDecimals(2)
        self._thr.setSingleStep(0.01)
        self._thr.setMaximumWidth(scale_px_h(88))
        self._thr.valueChanged.connect(self._commit_thr)
        add_template_similarity_row(
            ride_blk,
            self._cur,
            self._thr,
            pipela_mod=self._m,
            probe_capture_kind="ride_target",
            typography_bundle=self._typo,
        )
        attach_template_toolbar(
            ride_blk,
            self._m,
            "ride_target",
            self._tick,
            typography_bundle=self._typo,
        )
        lay.addWidget(ride_fr)
        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

    def apply_scaled_typography(self) -> None:
        self._outer.setSpacing(settings_root_vertical_spacing())
        self._inner_lay.setSpacing(settings_root_vertical_spacing())
        self._ride_probe_frame.apply_scale_margins()
        self._thr.setMaximumWidth(scale_px_h(88))
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
        bgr = m.load_image_data(path, "ride_target_image_data")
        _tw, _thm = thumb_preview_max_wh()
        pm = pixmap_from_bgr(bgr, _tw, _thm)
        fit_template_thumb_label_to_pixmap(self._thumb, pm, empty_text="없음")
        update_last_match_thumbnail(
            self._last_hit_thumb,
            m,
            "ride_target",
            match_caption_lbl=self._last_hit_cap,
            orig_thumb=self._thumb,
        )
