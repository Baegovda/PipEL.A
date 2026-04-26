"""콘솔(터미널) 설정 — 레지/전역과 동기 — 로그 보존·절대/상대 시간."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_int
from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    settings_footnote_style,
    settings_label_align_center_h,
    settings_page_title_style,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.scrub_spinboxes import DragSpinBox
from pipela_qt.settings_binary_toggle import SettingsBinaryToggleSwitch
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_adaptive import letter_spacing_qss, scale_px


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

        t1 = QLabel("터미널 설정")
        t1.setStyleSheet(settings_page_title_style())
        self._typo.add(lambda w=t1: w.setStyleSheet(settings_page_title_style()))
        settings_label_align_center_h(t1)
        lay.addWidget(t1)

        t2 = QLabel("시간 표시 방식")
        t2.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=t2: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(t2)
        lay.addWidget(t2)
        row_time = QHBoxLayout()
        row_time.setSpacing(scale_px(10))
        self._lbl_abs = QLabel("절대")
        self._lbl_rel = QLabel("상대")
        self._time_sw = SettingsBinaryToggleSwitch()
        self._time_sw.toggled.connect(self._on_time_sw_toggled)
        row_time.addWidget(self._lbl_abs, 0, Qt.AlignmentFlag.AlignRight)
        row_time.addWidget(self._time_sw, 0, Qt.AlignmentFlag.AlignCenter)
        row_time.addWidget(self._lbl_rel, 0, Qt.AlignmentFlag.AlignLeft)
        row_time.addStretch(1)
        lay.addLayout(row_time)
        self._time_hint = QLabel(
            "절대: 월·일 시:분:초. 상대: 각 로그 **줄이 찍힌 뒤** 흐른 시간(초→분→…, "
            "터미널·상대 모드에서 1초마다 갱신). 이후 출력되는 줄부터 적용됩니다.",
        )
        self._time_hint.setWordWrap(True)
        self._time_hint.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=self._time_hint: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(self._time_hint)
        lay.addWidget(self._time_hint)

        t3 = QLabel("로그 자동 숨김")
        t3.setStyleSheet(settings_section_heading_style(top_margin_px=scale_px(4)))
        self._typo.add(
            lambda w=t3: w.setStyleSheet(
                settings_section_heading_style(top_margin_px=scale_px(4)),
            ),
        )
        settings_label_align_center_h(t3)
        lay.addWidget(t3)
        self._spin = DragSpinBox()
        self._spin.setRange(int(m.CONSOLE_LOG_RETENTION_MIN_MIN), int(m.CONSOLE_LOG_RETENTION_MAX_MIN))
        self._spin.setSuffix(" 분 이상 경과 시 숨김")
        self._spin.valueChanged.connect(self._on_retention_change)
        add_settings_field_row(lay, "보존·숨김", self._spin)
        rng = QLabel(
            f"(허용 {m.CONSOLE_LOG_RETENTION_MIN_MIN}~{m.CONSOLE_LOG_RETENTION_MAX_MIN}분)",
        )
        rng.setWordWrap(True)
        rng.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=rng: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(rng)
        lay.addWidget(rng)

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
        self._spin.blockSignals(True)
        try:
            v = max(
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
            self._spin.setValue(v)
        finally:
            self._spin.blockSignals(False)
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

    def _on_retention_change(self, v: int) -> None:
        m = self._m
        m.console_log_retention_minutes = max(
            int(m.CONSOLE_LOG_RETENTION_MIN_MIN),
            min(int(m.CONSOLE_LOG_RETENTION_MAX_MIN), int(v)),
        )
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
