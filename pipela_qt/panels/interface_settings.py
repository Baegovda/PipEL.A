"""인터페이스 — 전역 UI 글꼴 크기(pt)."""

from __future__ import annotations

from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    settings_caption_style,
    settings_label_align_center_h,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.qt_typography_refresh import refresh_pipela_typography
from pipela_qt.scrub_spinboxes import DragSpinBox
from pipela_qt.typography_refresh_support import TypographyStyleBundle


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

    def _on_font_pt_changed(self, v: int) -> None:
        self._m.pipela_ui_font_pt = max(8, min(24, int(v)))
        refresh_pipela_typography(self._m)
        self._m.schedule_save_config()

    def apply_scaled_typography(self) -> None:
        self._root_lay.setSpacing(settings_root_vertical_spacing())
        self._typo.apply()
