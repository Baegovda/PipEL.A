"""콘솔(터미널) 설정 — 레지/전역과 동기 — 로그 보존·절대/상대 시간."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from pipela_core.console_log_constants import (
    CONSOLE_LOG_RETENTION_MAX_SECONDS,
    CONSOLE_LOG_RETENTION_UI_MAX_CLOCK_MINUTE,
    CONSOLE_LOG_RETENTION_UI_MAX_HOURS,
    console_log_retention_split_total,
    console_log_retention_split_total_to_hms,
    console_log_retention_total_sec,
    console_log_retention_total_sec_from_hms,
)
from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_int
from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    settings_caption_style,
    settings_label_align_center_h,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.scrub_spinboxes import DragSpinBox
from pipela_qt.settings_binary_toggle import SettingsBinaryToggleSwitch
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_adaptive import letter_spacing_qss, scale_px_h, scale_px_v


class ConsoleSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._typo = TypographyStyleBundle()
        m = pipela_mod
        lay = QVBoxLayout(self)
        self._root_lay = lay
        lay.setSpacing(settings_root_vertical_spacing())
        lay.setContentsMargins(0, 0, 0, 0)

        t2 = QLabel("시간 표시 방식")
        t2.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=t2: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(t2)
        lay.addWidget(t2)
        row_time = QHBoxLayout()
        row_time.setSpacing(scale_px_h(10))
        self._lbl_abs = QLabel("절대")
        self._lbl_rel = QLabel("상대")
        self._time_sw = SettingsBinaryToggleSwitch()
        self._time_sw.toggled.connect(self._on_time_sw_toggled)
        row_time.addStretch(1)
        row_time.addWidget(self._lbl_abs, 0, Qt.AlignmentFlag.AlignVCenter)
        row_time.addWidget(self._time_sw, 0, Qt.AlignmentFlag.AlignVCenter)
        row_time.addWidget(self._lbl_rel, 0, Qt.AlignmentFlag.AlignVCenter)
        row_time.addStretch(1)
        lay.addLayout(row_time)

        t3 = QLabel("로그 자동 숨김")
        t3.setStyleSheet(settings_section_heading_style(top_margin_px=scale_px_v(4)))
        self._typo.add(
            lambda w=t3: w.setStyleSheet(
                settings_section_heading_style(top_margin_px=scale_px_v(4)),
            ),
        )
        settings_label_align_center_h(t3)
        lay.addWidget(t3)
        self._spin_hour = DragSpinBox()
        self._spin_hour.setRange(0, int(CONSOLE_LOG_RETENTION_UI_MAX_HOURS))
        self._spin_hour.valueChanged.connect(self._commit_retention)
        self._lbl_hour_unit = QLabel("시간")
        self._lbl_hour_unit.setStyleSheet(settings_caption_style())
        self._typo.add(lambda w=self._lbl_hour_unit: w.setStyleSheet(settings_caption_style()))
        self._spin_min = DragSpinBox()
        self._spin_min.setRange(0, int(CONSOLE_LOG_RETENTION_UI_MAX_CLOCK_MINUTE))
        self._spin_min.valueChanged.connect(self._commit_retention)
        self._lbl_min_unit = QLabel("분")
        self._lbl_min_unit.setStyleSheet(settings_caption_style())
        self._typo.add(lambda w=self._lbl_min_unit: w.setStyleSheet(settings_caption_style()))
        self._spin_sec = DragSpinBox()
        self._spin_sec.setRange(0, int(CONSOLE_LOG_RETENTION_MAX_SECONDS))
        self._spin_sec.valueChanged.connect(self._commit_retention)
        self._lbl_sec_unit = QLabel("초")
        self._lbl_sec_unit.setStyleSheet(settings_caption_style())
        self._typo.add(lambda w=self._lbl_sec_unit: w.setStyleSheet(settings_caption_style()))
        add_settings_field_row(
            lay,
            "",
            self._spin_hour,
            self._lbl_hour_unit,
            self._spin_min,
            self._lbl_min_unit,
            self._spin_sec,
            self._lbl_sec_unit,
        )

        lay.addStretch(1)

        self._reload_from_globals()

    def apply_scaled_typography(self) -> None:
        self._root_lay.setSpacing(settings_root_vertical_spacing())
        self._time_sw.refresh_for_scale()
        self._typo.apply()
        self._sync_time_switch_labels(self._time_sw.isChecked())

    def _reload_from_globals(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        self._spin_hour.blockSignals(True)
        self._spin_min.blockSignals(True)
        self._spin_sec.blockSignals(True)
        try:
            vm = max(
                int(m.CONSOLE_LOG_RETENTION_MIN_MIN),
                min(
                    int(m.CONSOLE_LOG_RETENTION_MAX_MIN),
                    snapshot_int(
                        snap,
                        "console_log_retention_minutes",
                        int(m.console_log_retention_minutes),
                    ),
                ),
            )
            vs = max(
                0,
                min(
                    int(CONSOLE_LOG_RETENTION_MAX_SECONDS),
                    snapshot_int(
                        snap,
                        "console_log_retention_seconds",
                        int(getattr(m, "console_log_retention_seconds", 0)),
                    ),
                ),
            )
            total = console_log_retention_total_sec(vm, vs)
            h_u, mi_u, s_u = console_log_retention_split_total_to_hms(total)
            self._spin_hour.setValue(int(h_u))
            self._spin_min.setValue(int(mi_u))
            self._spin_sec.setValue(int(s_u))
        finally:
            self._spin_hour.blockSignals(False)
            self._spin_min.blockSignals(False)
            self._spin_sec.blockSignals(False)
        tm = snap.get("console_log_time_display_mode", m.console_log_time_display_mode)
        if tm not in (m.CONSOLE_LOG_TIME_MODE_ABSOLUTE, m.CONSOLE_LOG_TIME_MODE_RELATIVE):
            tm = m.CONSOLE_LOG_TIME_MODE_ABSOLUTE
        self._time_sw.blockSignals(True)
        try:
            self._time_sw.setChecked(tm == m.CONSOLE_LOG_TIME_MODE_RELATIVE)
        finally:
            self._time_sw.blockSignals(False)
        self._sync_time_switch_labels(tm == m.CONSOLE_LOG_TIME_MODE_RELATIVE)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._reload_from_globals()

    def _sync_time_switch_labels(self, relative_on: bool) -> None:
        on = T.FG
        off = T.FG_MUTED
        ls = letter_spacing_qss()
        _base = f"font-family: {T.FONT_CSS_UI}; text-align: center; font-size: {T.spt(9.5)}; letter-spacing: {ls};"
        self._lbl_abs.setStyleSheet(
            f"{_base} color: {on if not relative_on else off}; "
            f"font-weight: {'600' if not relative_on else '400'};",
        )
        self._lbl_rel.setStyleSheet(
            f"{_base} color: {on if relative_on else off}; "
            f"font-weight: {'600' if relative_on else '400'};",
        )
        self._lbl_abs.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_rel.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

    def _on_time_sw_toggled(self, checked: bool) -> None:
        m = self._m
        if checked:
            m.console_log_time_display_mode = m.CONSOLE_LOG_TIME_MODE_RELATIVE
        else:
            m.console_log_time_display_mode = m.CONSOLE_LOG_TIME_MODE_ABSOLUTE
        self._sync_time_switch_labels(checked)
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
        try:
            w = getattr(m, "_qt_control_main", None)
            if w is not None and hasattr(w, "sync_console_time_display_chrome"):
                w.sync_console_time_display_chrome()
        except Exception:
            pass

    def _commit_retention(self) -> None:
        m = self._m
        hh = int(self._spin_hour.value())
        mm = int(self._spin_min.value())
        ss = int(self._spin_sec.value())
        total = console_log_retention_total_sec_from_hms(hh, mm, ss)
        mm2, ss2 = console_log_retention_split_total(total)
        m.console_log_retention_minutes = mm2
        m.console_log_retention_seconds = ss2
        h_u, mi_u, s_u = console_log_retention_split_total_to_hms(total)
        self._spin_hour.blockSignals(True)
        self._spin_min.blockSignals(True)
        self._spin_sec.blockSignals(True)
        try:
            self._spin_hour.setValue(int(h_u))
            self._spin_min.setValue(int(mi_u))
            self._spin_sec.setValue(int(s_u))
        finally:
            self._spin_hour.blockSignals(False)
            self._spin_min.blockSignals(False)
            self._spin_sec.blockSignals(False)
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
        try:
            w = getattr(m, "_qt_control_main", None)
            if w is not None and hasattr(w, "apply_console_log_retention_now"):
                w.apply_console_log_retention_now()
        except Exception:
            pass
