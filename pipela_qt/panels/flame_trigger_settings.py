"""Flame Trigger 설정 — Merc Fire 키·간격(ms)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

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
    settings_footnote_style,
    settings_footnote_style_color,
    settings_label_align_center_h,
    settings_page_title_style,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.resizable_text_widgets import ResizableLineEdit
from pipela_qt.scrub_spinboxes import DragSpinBox
from pipela_qt.settings_binary_toggle import SettingsBinaryToggleSwitch
from pipela_qt.ui_adaptive import scale_px
from pipela_qt.typography_refresh_support import TypographyStyleBundle

_MS_MIN = 1
_MS_MAX = 1_000_000


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

        t1 = QLabel("Flame Trigger 설정")
        t1.setStyleSheet(settings_page_title_style())
        self._typo.add(lambda w=t1: w.setStyleSheet(settings_page_title_style()))
        settings_label_align_center_h(t1)
        lay.addWidget(t1)

        lay.addWidget(make_settings_hline())

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

        lay.addWidget(make_settings_hline())

        st2 = QLabel("지정할 키")
        st2.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st2: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st2)
        lay.addWidget(st2)

        self._key_disp = ResizableLineEdit()
        self._key_disp.setReadOnly(True)
        self._key_disp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._key_disp.setMaximumWidth(scale_px(140))
        self._cap_btn = QPushButton("키 입력")
        self._cap_btn.clicked.connect(self._toggle_key_capture)
        add_settings_field_row(lay, "키", self._key_disp, self._cap_btn)

        self._key_hint = QLabel(
            "「키 입력」 후 원하는 키를 한 번 누르면 바인딩됩니다. 키 입력 중 Esc는 취소.",
        )
        self._key_hint.setWordWrap(True)
        self._key_hint.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=self._key_hint: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(self._key_hint)
        lay.addWidget(self._key_hint)

        lay.addWidget(make_settings_hline())

        st3 = QLabel("입력 간격 (밀리초)")
        st3.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st3: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st3)
        lay.addWidget(st3)

        self._min_spin = DragSpinBox()
        self._min_spin.setRange(_MS_MIN, _MS_MAX)
        self._min_spin.valueChanged.connect(self._commit)
        self._max_spin = DragSpinBox()
        self._max_spin.setRange(_MS_MIN, _MS_MAX)
        self._max_spin.valueChanged.connect(self._commit)
        add_settings_field_row(
            lay,
            "최소 ~ 최대",
            self._min_spin,
            QLabel("ms"),
            QLabel("~"),
            self._max_spin,
            QLabel("ms"),
        )

        self._sec_hint = QLabel("")
        self._sec_hint.setWordWrap(True)
        self._sec_hint.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=self._sec_hint: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(self._sec_hint)
        lay.addWidget(self._sec_hint)
        lay.addStretch(1)

        self._reload_from_globals()

    def apply_scaled_typography(self) -> None:
        self._root_lay.setSpacing(settings_root_vertical_spacing())
        self._key_disp.setMaximumWidth(scale_px(140))
        self._cb.refresh_for_scale()
        self._typo.apply()
        self._refresh_enables()
        self._refresh_sec_hint()

    def _reload_from_globals(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        self._cb.blockSignals(True)
        self._min_spin.blockSignals(True)
        self._max_spin.blockSignals(True)
        self._cb.setChecked(snapshot_bool(snap, "merc_fire_enabled", bool(m.merc_fire_enabled)))
        lo = int(
            max(
                _MS_MIN,
                min(
                    _MS_MAX,
                    round(snapshot_float(snap, "merc_fire_random_min_ms", float(m.merc_fire_random_min_ms))),
                ),
            )
        )
        hi = int(
            max(
                _MS_MIN,
                min(
                    _MS_MAX,
                    round(snapshot_float(snap, "merc_fire_random_max_ms", float(m.merc_fire_random_max_ms))),
                ),
            )
        )
        if hi < lo:
            hi = min(_MS_MAX, lo + 1)
        self._min_spin.setValue(lo)
        self._max_spin.setValue(hi)
        kc = snapshot_int(snap, "merc_fire_key_code", int(m.merc_fire_key_code))
        self._key_disp.setText(m.vk_to_display_name(int(kc) & 0xFF))
        self._cb.blockSignals(False)
        self._min_spin.blockSignals(False)
        self._max_spin.blockSignals(False)
        self._refresh_enables()
        self._refresh_sec_hint()

    def _on_enabled_changed(self) -> None:
        if not self._cb.isChecked() and self._capturing:
            self._end_capture(cancel=True)
        self._commit()

    def _refresh_enables(self) -> None:
        on = self._cb.isChecked()
        self._key_disp.setEnabled(on)
        self._cap_btn.setEnabled(on)
        self._min_spin.setEnabled(on)
        self._max_spin.setEnabled(on)
        muted = T.FG_DIM if on else T.FG_MUTED
        self._key_hint.setStyleSheet(settings_footnote_style_color(muted))
        settings_label_align_center_h(self._key_hint)

    def _refresh_sec_hint(self) -> None:
        lo = self._min_spin.value()
        hi = self._max_spin.value()
        sm = lo / 1000.0
        sx = hi / 1000.0
        self._sec_hint.setText(f"≈ {sm:.4g}초 ~ {sx:.4g}초")

    def _commit(self) -> None:
        m = self._m
        m.merc_fire_enabled = self._cb.isChecked()
        lo = self._min_spin.value()
        hi = self._max_spin.value()
        if hi < lo:
            hi = min(_MS_MAX, lo + 1)
            self._max_spin.blockSignals(True)
            self._max_spin.setValue(hi)
            self._max_spin.blockSignals(False)
        m.merc_fire_random_min_ms = float(lo)
        m.merc_fire_random_max_ms = float(hi)
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
        self._refresh_enables()
        self._refresh_sec_hint()

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
            self._end_capture(cancel=False)
            event.accept()
            return
        super().keyPressEvent(event)
