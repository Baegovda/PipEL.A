"""LeftClick 설정 — 홀드 시간·고정/랜덤 간격(ms 저장)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_bool, snapshot_float
from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    settings_caption_style,
    settings_label_align_center_h,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt import theme as T
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox
from pipela_qt.settings_binary_toggle import SettingsBinaryToggleSwitch
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_adaptive import letter_spacing_qss, scale_px_h, scale_px_v

_MIN_SEC = 0.01
_MAX_SEC = 5.0
_MIN_HOLD_SEC = 0.02
_MAX_HOLD_SEC = 2.0


def _cps_from_wait_ms(ms: float) -> float:
    return 1000.0 / (10.0 + max(0.0, float(ms)))


class LeftClickSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._typo = TypographyStyleBundle()
        lay = QVBoxLayout(self)
        self._root_lay = lay
        lay.setSpacing(settings_root_vertical_spacing())
        lay.setContentsMargins(0, 0, 0, 0)

        st1 = QLabel("발동 조건")
        st1.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st1: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st1)
        lay.addWidget(st1)
        self._hold = DragDoubleSpinBox()
        self._hold.setRange(_MIN_HOLD_SEC, _MAX_HOLD_SEC)
        self._hold.setDecimals(4)
        self._hold.setSingleStep(0.01)
        self._hold.valueChanged.connect(self._commit)
        add_settings_field_row(lay, "홀드 시간", self._hold, QLabel("초"))

        self._st_click_gap = QLabel("클릭 간격")
        self._st_click_gap.setStyleSheet(
            settings_section_heading_style(top_margin_px=scale_px_v(6)),
        )
        self._typo.add(
            lambda w=self._st_click_gap: w.setStyleSheet(
                settings_section_heading_style(top_margin_px=scale_px_v(6)),
            ),
        )
        settings_label_align_center_h(self._st_click_gap)
        lay.addWidget(self._st_click_gap)
        row_mode = QHBoxLayout()
        row_mode.setSpacing(scale_px_h(10))
        self._lbl_fixed = QLabel("고정 간격")
        self._lbl_random = QLabel("랜덤 간격")
        self._mode_sw = SettingsBinaryToggleSwitch()
        self._mode_sw.toggled.connect(self._on_mode_toggled)
        row_mode.addStretch(1)
        row_mode.addWidget(self._lbl_fixed, 0, Qt.AlignmentFlag.AlignVCenter)
        row_mode.addWidget(self._mode_sw, 0, Qt.AlignmentFlag.AlignVCenter)
        row_mode.addWidget(self._lbl_random, 0, Qt.AlignmentFlag.AlignVCenter)
        row_mode.addStretch(1)
        lay.addLayout(row_mode)
        self._sync_mode_switch_labels(False)

        self._stack = QStackedWidget()
        fixed_w = QWidget()
        fr = QVBoxLayout(fixed_w)
        fr.setContentsMargins(0, 0, 0, 0)
        self._fixed = DragDoubleSpinBox()
        self._fixed.setRange(_MIN_SEC, _MAX_SEC)
        self._fixed.setDecimals(4)
        self._fixed.setSingleStep(0.01)
        self._fixed.valueChanged.connect(self._commit)
        add_settings_field_row(fr, "간격", self._fixed, QLabel("초"))

        rand_w = QWidget()
        rr = QVBoxLayout(rand_w)
        rr.setContentsMargins(0, 0, 0, 0)
        self._min_iv = DragDoubleSpinBox()
        self._min_iv.setRange(_MIN_SEC, _MAX_SEC)
        self._min_iv.setDecimals(4)
        self._min_iv.setSingleStep(0.01)
        self._min_iv.valueChanged.connect(self._commit)
        self._max_iv = DragDoubleSpinBox()
        self._max_iv.setRange(_MIN_SEC, _MAX_SEC)
        self._max_iv.setDecimals(4)
        self._max_iv.setSingleStep(0.01)
        self._max_iv.valueChanged.connect(self._commit)
        self._rand_lo_lbl = QLabel("최소")
        self._rand_hi_lbl = QLabel("최대")
        self._rand_tilde = QLabel("~")
        self._rand_sec_lo = QLabel("초")
        self._rand_sec_hi = QLabel("초")
        for _w in (
            self._rand_lo_lbl,
            self._rand_hi_lbl,
            self._rand_tilde,
            self._rand_sec_lo,
            self._rand_sec_hi,
        ):
            _w.setStyleSheet(settings_caption_style())
            self._typo.add(lambda w=_w: w.setStyleSheet(settings_caption_style()))
            settings_label_align_center_h(_w)
        add_settings_field_row(
            rr,
            "",
            self._rand_lo_lbl,
            self._min_iv,
            self._rand_sec_lo,
            self._rand_tilde,
            self._rand_hi_lbl,
            self._max_iv,
            self._rand_sec_hi,
        )

        self._stack.addWidget(fixed_w)
        self._stack.addWidget(rand_w)
        lay.addWidget(self._stack)

        self._cps = QLabel("")
        self._cps.setWordWrap(True)
        self._cps.setStyleSheet(settings_caption_style())
        self._typo.add(lambda w=self._cps: w.setStyleSheet(settings_caption_style()))
        settings_label_align_center_h(self._cps)
        lay.addWidget(self._cps)
        lay.addStretch(1)

        self._reload_from_globals()

    def apply_scaled_typography(self) -> None:
        self._root_lay.setSpacing(settings_root_vertical_spacing())
        self._st_click_gap.setStyleSheet(
            settings_section_heading_style(top_margin_px=scale_px_v(6)),
        )
        self._mode_sw.refresh_for_scale()
        self._typo.apply()
        self._sync_mode_switch_labels(self._mode_sw.isChecked())
        self._refresh_cps_preview()

    def _on_mode_toggled(self, random_on: bool) -> None:
        self._stack.setCurrentIndex(1 if random_on else 0)
        self._sync_mode_switch_labels(random_on)
        self._commit()

    def _sync_mode_switch_labels(self, random_on: bool) -> None:
        on = T.FG
        off = T.FG_MUTED
        ls = letter_spacing_qss()
        _base = (
            f"font-family: {T.FONT_CSS_UI}; text-align: center; "
            f"font-size: {T.spt(9.5)}; letter-spacing: {ls};"
        )
        self._lbl_fixed.setStyleSheet(
            f"{_base} color: {on if not random_on else off}; "
            f"font-weight: {'600' if not random_on else '400'};",
        )
        self._lbl_random.setStyleSheet(
            f"{_base} color: {on if random_on else off}; "
            f"font-weight: {'600' if random_on else '400'};",
        )
        self._lbl_fixed.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        )
        self._lbl_random.setAlignment(
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        )

    def _reload_from_globals(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        for w in (
            self._hold,
            self._fixed,
            self._min_iv,
            self._max_iv,
        ):
            w.blockSignals(True)
        hold = max(
            _MIN_HOLD_SEC,
            min(
                _MAX_HOLD_SEC,
                snapshot_float(snap, "left_click_hold_sec", float(m.left_click_hold_sec)),
            ),
        )
        self._hold.setValue(hold)
        fixed_sec = max(
            _MIN_SEC,
            min(
                _MAX_SEC,
                snapshot_float(snap, "left_click_interval_ms", float(m.left_click_interval_ms)) / 1000.0,
            ),
        )
        self._fixed.setValue(fixed_sec)
        lo = max(
            _MIN_SEC,
            min(
                _MAX_SEC,
                snapshot_float(snap, "left_click_random_min_ms", float(m.left_click_random_min_ms)) / 1000.0,
            ),
        )
        hi = max(
            _MIN_SEC,
            min(
                _MAX_SEC,
                snapshot_float(snap, "left_click_random_max_ms", float(m.left_click_random_max_ms)) / 1000.0,
            ),
        )
        if lo > hi:
            lo, hi = hi, lo
        self._min_iv.setValue(lo)
        self._max_iv.setValue(hi)
        rand_on = snapshot_bool(snap, "left_click_random_enabled", bool(m.left_click_random_enabled))
        self._mode_sw.blockSignals(True)
        try:
            self._mode_sw.setChecked(rand_on)
        finally:
            self._mode_sw.blockSignals(False)
        self._stack.setCurrentIndex(1 if rand_on else 0)
        self._sync_mode_switch_labels(rand_on)
        for w in (
            self._hold,
            self._fixed,
            self._min_iv,
            self._max_iv,
        ):
            w.blockSignals(False)
        self._refresh_cps_preview()

    def _commit(self) -> None:
        m = self._m
        hold = max(_MIN_HOLD_SEC, min(_MAX_HOLD_SEC, float(self._hold.value())))
        fixed_sec = max(_MIN_SEC, min(_MAX_SEC, float(self._fixed.value())))
        min_sec = max(_MIN_SEC, min(_MAX_SEC, float(self._min_iv.value())))
        max_sec = max(_MIN_SEC, min(_MAX_SEC, float(self._max_iv.value())))
        if min_sec > max_sec:
            min_sec, max_sec = max_sec, min_sec
            self._min_iv.blockSignals(True)
            self._max_iv.blockSignals(True)
            self._min_iv.setValue(min_sec)
            self._max_iv.setValue(max_sec)
            self._min_iv.blockSignals(False)
            self._max_iv.blockSignals(False)

        m.left_click_hold_sec = hold
        m.left_click_interval_ms = fixed_sec * 1000.0
        m.left_click_random_min_ms = min_sec * 1000.0
        m.left_click_random_max_ms = max_sec * 1000.0
        m.left_click_random_enabled = self._mode_sw.isChecked()
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
        self._refresh_cps_preview()

    def _refresh_cps_preview(self) -> None:
        fixed_sec = max(_MIN_SEC, min(_MAX_SEC, float(self._fixed.value())))
        min_sec = max(_MIN_SEC, min(_MAX_SEC, float(self._min_iv.value())))
        max_sec = max(_MIN_SEC, min(_MAX_SEC, float(self._max_iv.value())))
        if min_sec > max_sec:
            min_sec, max_sec = max_sec, min_sec
        lo_ms = min_sec * 1000.0
        hi_ms = max_sec * 1000.0

        if self._mode_sw.isChecked():
            c_small = _cps_from_wait_ms(hi_ms)
            c_big = _cps_from_wait_ms(lo_ms)
            c_lo, c_hi = min(c_small, c_big), max(c_small, c_big)
            if c_hi - c_lo < 1e-6:
                self._cps.setText(f"초당 클릭 횟수 : 약 {c_lo:.2f}회")
            else:
                self._cps.setText(
                    f"초당 클릭 횟수 : 약 {c_lo:.2f}회 ~ {c_hi:.2f}회",
                )
        else:
            c = _cps_from_wait_ms(fixed_sec * 1000.0)
            self._cps.setText(f"초당 클릭 횟수 : 약 {c:.2f}회")
