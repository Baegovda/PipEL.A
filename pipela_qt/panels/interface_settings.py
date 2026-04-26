"""인터페이스 — 전역 UI 글꼴 크기(pt)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from pipela_qt import theme as T
from pipela_qt.cursor_hud import apply_pipela_cursor_hud_enabled
from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    settings_caption_style,
    settings_footnote_style,
    settings_label_align_center_h,
    settings_page_title_style,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.qt_typography_refresh import refresh_pipela_typography
from pipela_qt.scrub_spinboxes import DragSpinBox
from pipela_qt.settings_binary_toggle import SettingsBinaryToggleSwitch
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.ui_adaptive import letter_spacing_qss, scale_px


# UI pt: 드래그 스크럽은 기본보다 덜 민감, 휠은 2노치(≈240)당 1pt
class _FontPtDragSpinBox(DragSpinBox):
    def __init__(self, parent=None) -> None:
        super().__init__(
            parent,
            scrub_pixels_scale=2.5,
            pre_step_highlight_start=0.70,
        )
        self._wheel_acc = 0

    def wheelEvent(self, e: QWheelEvent) -> None:
        self._wheel_acc += e.angleDelta().y()
        th = 120 * 2
        if abs(self._wheel_acc) < th:
            e.accept()
            return
        d = 1 if self._wheel_acc > 0 else -1
        self._wheel_acc = 0
        e.accept()
        v = int(self.value()) + d
        self.setValue(max(self.minimum(), min(self.maximum(), v)))


class InterfaceSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._typo = TypographyStyleBundle()
        lay = QVBoxLayout(self)
        self._root_lay = lay
        lay.setSpacing(settings_root_vertical_spacing())
        lay.setContentsMargins(0, 0, 0, 0)

        t1 = QLabel("인터페이스")
        t1.setStyleSheet(settings_page_title_style())
        self._typo.add(lambda w=t1: w.setStyleSheet(settings_page_title_style()))
        settings_label_align_center_h(t1)
        lay.addWidget(t1)

        t2 = QLabel("글꼴")
        t2.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=t2: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(t2)
        lay.addWidget(t2)

        self._font_spin = _FontPtDragSpinBox()
        self._font_spin.setRange(8, 24)
        self._font_spin.setValue(int(getattr(pipela_mod, "pipela_ui_font_pt", 11)))
        self._font_spin.valueChanged.connect(self._on_font_pt_changed)
        add_settings_field_row(lay, "UI 글꼴 크기 (pt)", self._font_spin)

        t_hud = QLabel("커서·플레임 HUD")
        t_hud.setStyleSheet(settings_section_heading_style(top_margin_px=scale_px(4)))
        self._typo.add(
            lambda w=t_hud: w.setStyleSheet(
                settings_section_heading_style(top_margin_px=scale_px(4)),
            ),
        )
        settings_label_align_center_h(t_hud)
        lay.addWidget(t_hud)
        row_hud = QHBoxLayout()
        row_hud.setSpacing(scale_px(10))
        self._lbl_hud_off = QLabel("끔")
        self._lbl_hud_on = QLabel("켜짐")
        self._hud_sw = SettingsBinaryToggleSwitch()
        self._hud_sw.toggled.connect(self._on_hud_sw_toggled)
        row_hud.addWidget(self._lbl_hud_off, 0, Qt.AlignmentFlag.AlignRight)
        row_hud.addWidget(self._hud_sw, 0, Qt.AlignmentFlag.AlignCenter)
        row_hud.addWidget(self._lbl_hud_on, 0, Qt.AlignmentFlag.AlignLeft)
        row_hud.addStretch(1)
        lay.addLayout(row_hud)
        hud_note = QLabel(
            "이동·사격·탑승 아이콘과 플레임 정보 창입니다. 끄고도 증상이 남으면 원인이 HUD만은 아닐 수 있습니다 "
            "(게임 오버레이·타이틀 스트립, 전체화면 독점 시 커서 API 유령값, Flame Trigger 중앙 스냅 등). "
            "한 번만 HUD 없이 켤 때는 환경 변수 PIPELA_CURSOR_HUD=0 을 쓸 수 있습니다.",
        )
        hud_note.setWordWrap(True)
        hud_note.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=hud_note: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(hud_note)
        lay.addWidget(hud_note)

        body = QLabel(
            "8~24pt 범위에서 조절합니다. 숫자 칸을 드래그할 때는 한 단계 전에 필드가 살짝 강조되며, "
            "휠은 두 톱니에 한 번씩만 변합니다. 적용 즉시 제어창·타이틀 스트립·킬 패널 등에 반영되며 설정에 저장됩니다.",
        )
        body.setWordWrap(True)
        body.setStyleSheet(settings_caption_style())
        self._typo.add(lambda w=body: w.setStyleSheet(settings_caption_style()))
        settings_label_align_center_h(body)
        lay.addWidget(body)
        lay.addStretch(1)

        self._reload_hud_toggle_from_globals()

    def _reload_hud_toggle_from_globals(self) -> None:
        m = self._m
        on = bool(getattr(m, "pipela_cursor_hud_enabled", True))
        self._hud_sw.blockSignals(True)
        try:
            self._hud_sw.setChecked(on)
        finally:
            self._hud_sw.blockSignals(False)
        self._sync_hud_switch_labels(on)

    def _sync_hud_switch_labels(self, hud_on: bool) -> None:
        on_c = T.FG
        off_c = T.FG_MUTED
        ls = letter_spacing_qss()
        _base = (
            f"font-family: {T.FONT_CSS_UI}; text-align: center; font-size: {T.spt(9.5)}; "
            f"letter-spacing: {ls};"
        )
        self._lbl_hud_off.setStyleSheet(
            f"{_base} color: {on_c if not hud_on else off_c}; "
            f"font-weight: {'600' if not hud_on else '400'};",
        )
        self._lbl_hud_on.setStyleSheet(
            f"{_base} color: {on_c if hud_on else off_c}; "
            f"font-weight: {'600' if hud_on else '400'};",
        )
        self._lbl_hud_off.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_hud_on.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._reload_hud_toggle_from_globals()

    def _on_hud_sw_toggled(self, checked: bool) -> None:
        self._m.pipela_cursor_hud_enabled = bool(checked)
        self._sync_hud_switch_labels(checked)
        apply_pipela_cursor_hud_enabled(self._m)
        self._m.schedule_save_config()

    def _on_font_pt_changed(self, v: int) -> None:
        self._m.pipela_ui_font_pt = max(8, min(24, int(v)))
        refresh_pipela_typography(self._m)
        self._m.schedule_save_config()

    def apply_scaled_typography(self) -> None:
        self._root_lay.setSpacing(settings_root_vertical_spacing())
        self._hud_sw.refresh_for_scale()
        self._typo.apply()
