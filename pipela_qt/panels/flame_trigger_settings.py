"""Flame Trigger 설정 — Merc Fire 키·입력 간격(초 단위)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtGui import QFontMetrics, QKeyEvent
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_bool, snapshot_float, snapshot_int
from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import (
    add_settings_control_row_centered,
    add_settings_field_row,
    make_settings_hline,
    settings_caption_style,
    settings_footnote_style,
    settings_label_align_center_h,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.resizable_text_widgets import ResizableLineEdit
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox
from pipela_qt.settings_binary_toggle import SettingsBinaryToggleSwitch
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v
from pipela_qt.typography_refresh_support import TypographyStyleBundle

_MS_MIN = 1.0
_MS_MAX = 1_000_000.0
_SEC_MIN = 0.001
_SEC_MAX = 1000.0
_SEC_DECIMALS = 3


def _h_advance(fm: QFontMetrics, s: str) -> int:
    return int(fm.horizontalAdvance(s))


class FlameTriggerSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._capturing = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._typo = TypographyStyleBundle()

        lay = QVBoxLayout(self)
        self._root_lay = lay
        lay.setSpacing(settings_root_vertical_spacing())
        lay.setContentsMargins(0, 0, 0, 0)

        st1 = QLabel("Merc Fire · 연사 키")
        st1.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st1: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st1)
        lay.addWidget(st1)

        self._cb_lbl = QLabel("Merc Fire 활성화")
        self._cb_lbl.setStyleSheet(f"color: {T.FG}; font-family: {T.FONT_CSS_UI};")
        self._typo.add(
            lambda w=self._cb_lbl: w.setStyleSheet(
                f"color: {T.FG}; font-family: {T.FONT_CSS_UI};",
            ),
        )
        self._cb = SettingsBinaryToggleSwitch()
        self._cb.toggled.connect(self._on_enabled_changed)
        add_settings_control_row_centered(lay, self._cb_lbl, self._cb)

        self._merc_opts = QWidget()
        opts_lay = QVBoxLayout(self._merc_opts)
        opts_lay.setSpacing(settings_root_vertical_spacing())
        opts_lay.setContentsMargins(0, 0, 0, 0)

        opts_lay.addWidget(make_settings_hline())

        st2 = QLabel("지정할 키")
        st2.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st2: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st2)
        opts_lay.addWidget(st2)

        self._key_disp = ResizableLineEdit()
        self._key_disp.setReadOnly(True)
        self._key_disp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cap_btn = QPushButton("키 입력")
        self._cap_btn.clicked.connect(self._toggle_key_capture)
        add_settings_field_row(opts_lay, "키", self._key_disp, self._cap_btn)

        self._key_hint = QLabel(
            "「키 입력」 후 원하는 키를 한 번 누르면 바인딩됩니다. 키 입력 중 Esc는 취소.",
        )
        self._key_hint.setWordWrap(True)
        self._key_hint.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=self._key_hint: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(self._key_hint)
        opts_lay.addWidget(self._key_hint)

        opts_lay.addWidget(make_settings_hline())

        st3 = QLabel("입력 간격")
        st3.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st3: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st3)
        opts_lay.addWidget(st3)

        self._min_spin = DragDoubleSpinBox()
        self._max_spin = DragDoubleSpinBox()
        self._configure_interval_spins()

        self._ival_lo_lbl = QLabel("최소")
        self._ival_hi_lbl = QLabel("최대")
        self._ival_tilde = QLabel("~")
        self._ival_sec_lo = QLabel("초")
        self._ival_sec_hi = QLabel("초")
        for _w in (
            self._ival_lo_lbl,
            self._ival_hi_lbl,
            self._ival_tilde,
            self._ival_sec_lo,
            self._ival_sec_hi,
        ):
            _w.setStyleSheet(settings_caption_style())
            self._typo.add(lambda w=_w: w.setStyleSheet(settings_caption_style()))
            settings_label_align_center_h(_w)

        add_settings_field_row(
            opts_lay,
            "",
            self._ival_lo_lbl,
            self._min_spin,
            self._ival_sec_lo,
            self._ival_tilde,
            self._ival_hi_lbl,
            self._max_spin,
            self._ival_sec_hi,
        )

        self._interval_hint = QLabel("")
        self._interval_hint.setWordWrap(True)
        self._interval_hint.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=self._interval_hint: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(self._interval_hint)
        opts_lay.addWidget(self._interval_hint)

        self._min_spin.valueChanged.connect(self._commit)
        self._max_spin.valueChanged.connect(self._commit)

        lay.addWidget(self._merc_opts)
        lay.addStretch(1)

        self._reload_from_globals()

    def showEvent(self, e: QShowEvent) -> None:
        super().showEvent(e)
        self._reload_from_globals()

    def _fit_key_disp_width(self) -> None:
        """표시 중인 키 이름 길이에만 맞춤(긴 이름은 캡처 후 자동 확장)."""
        fm = self._key_disp.fontMetrics()
        t = self._key_disp.text() or "—"
        ref = _h_advance(fm, t)
        pad = scale_px_v(14)
        lo = scale_px_v(30)
        hi = scale_px_v(220)
        self._key_disp.setFixedWidth(max(lo, min(hi, ref + pad)))

    def _configure_interval_spins(self) -> None:
        self._min_spin.setDecimals(_SEC_DECIMALS)
        self._max_spin.setDecimals(_SEC_DECIMALS)
        self._min_spin.setRange(_SEC_MIN, _SEC_MAX)
        self._max_spin.setRange(_SEC_MIN, _SEC_MAX)
        step = 0.001
        self._min_spin.setSingleStep(step)
        self._max_spin.setSingleStep(step)

    def _spin_pair_as_ms(self) -> tuple[float, float]:
        lo = float(self._min_spin.value()) * 1000.0
        hi = float(self._max_spin.value()) * 1000.0
        return lo, hi

    def _fit_interval_spins_width(self) -> None:
        fm = self._min_spin.fontMetrics()
        lo_s = f"{float(self._min_spin.value()):.{_SEC_DECIMALS}f}"
        hi_s = f"{float(self._max_spin.value()):.{_SEC_DECIMALS}f}"
        sample = max(lo_s, hi_s, "888.888", key=len)
        ref = _h_advance(fm, sample)
        pad = scale_px_v(26)
        lo = scale_px_v(48)
        hi = scale_px_v(112)
        w = max(lo, min(hi, ref + pad))
        self._min_spin.setFixedWidth(w)
        self._max_spin.setFixedWidth(w)

    def _refresh_compact_control_widths(self) -> None:
        self._fit_key_disp_width()
        self._fit_interval_spins_width()

    def apply_scaled_typography(self) -> None:
        self._root_lay.setSpacing(settings_root_vertical_spacing())
        self._cb.refresh_for_scale()
        self._typo.apply()
        self._refresh_enables()
        self._refresh_interval_hint()
        self._refresh_compact_control_widths()

    def _reload_from_globals(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        self._cb.blockSignals(True)
        self._min_spin.blockSignals(True)
        self._max_spin.blockSignals(True)
        self._cb.setChecked(snapshot_bool(snap, "merc_fire_enabled", bool(m.merc_fire_enabled)))
        lo_ms = float(
            max(
                _MS_MIN,
                min(
                    _MS_MAX,
                    snapshot_float(snap, "merc_fire_random_min_ms", float(m.merc_fire_random_min_ms)),
                ),
            )
        )
        hi_ms = float(
            max(
                _MS_MIN,
                min(
                    _MS_MAX,
                    snapshot_float(snap, "merc_fire_random_max_ms", float(m.merc_fire_random_max_ms)),
                ),
            )
        )
        if hi_ms < lo_ms:
            hi_ms = min(_MS_MAX, lo_ms + 1.0)
        self._min_spin.setValue(lo_ms / 1000.0)
        self._max_spin.setValue(hi_ms / 1000.0)
        kc = snapshot_int(snap, "merc_fire_key_code", int(m.merc_fire_key_code))
        self._key_disp.setText(m.vk_to_display_name(int(kc) & 0xFF))
        self._cb.blockSignals(False)
        self._min_spin.blockSignals(False)
        self._max_spin.blockSignals(False)
        self._refresh_enables()
        self._refresh_interval_hint()
        self._refresh_compact_control_widths()

    def _on_enabled_changed(self) -> None:
        if not self._cb.isChecked() and self._capturing:
            self._end_capture(cancel=True)
        self._commit()

    def _refresh_enables(self) -> None:
        on = self._cb.isChecked()
        self._merc_opts.setVisible(on)

    def _refresh_interval_hint(self) -> None:
        hint = getattr(self, "_interval_hint", None)
        if hint is None:
            return
        lo_ms, hi_ms = self._spin_pair_as_ms()
        hint.setText(f"≈ {int(round(lo_ms))} ms ~ {int(round(hi_ms))} ms")

    def _commit(self) -> None:
        m = self._m
        m.merc_fire_enabled = self._cb.isChecked()
        m.merc_fire_interval_use_seconds = True
        lo_ms, hi_ms = self._spin_pair_as_ms()
        lo_ms = max(_MS_MIN, min(_MS_MAX, lo_ms))
        hi_ms = max(_MS_MIN, min(_MS_MAX, hi_ms))
        if hi_ms < lo_ms:
            hi_ms = min(_MS_MAX, lo_ms + 1.0)
            self._max_spin.blockSignals(True)
            self._max_spin.setValue(hi_ms / 1000.0)
            self._max_spin.blockSignals(False)
        m.merc_fire_random_min_ms = float(lo_ms)
        m.merc_fire_random_max_ms = float(hi_ms)
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
        self._refresh_enables()
        self._refresh_interval_hint()
        self._refresh_compact_control_widths()

    def _toggle_key_capture(self) -> None:
        if not self._cb.isChecked():
            return
        if self._capturing:
            self._end_capture(cancel=True)
            return
        self._capturing = True
        self._cap_btn.setText("키를 누르세요…")
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.grabKeyboard()

    def _end_capture(self, *, cancel: bool = False) -> None:
        if not self._capturing:
            return
        self._capturing = False
        self.releaseKeyboard()
        self._cap_btn.setText("키 입력")
        if not cancel:
            self._commit()

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
            self._m.merc_fire_key_code = vk
            sync_registry_snapshot_from_module(self._m)
            self._key_disp.setText(self._m.vk_to_display_name(vk))
            self._fit_key_disp_width()
            self._end_capture(cancel=False)
            event.accept()
            return
        super().keyPressEvent(event)
