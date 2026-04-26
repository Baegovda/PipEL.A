"""템플릿/감지 ROI 오버레이 — 색·불투명도·채우기(미리보기·드래그 선택·퀵 펄스) 공통.

Qt 전용. 테마 `pipela_qt.theme`의 ACCENT·PANEL_BG와 맞춤.
"""

from __future__ import annotations

import math
from typing import Any

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPen

from pipela_qt import theme as T

# 전체 창을 덮는 dim (템플릿 PNG 캡처, 클라이언트 영역 드래그)
OVERLAY_FULL_WINDOW_OPACITY: float = 0.44


def overlay_full_dim_color() -> QColor:
    return QColor(T.PANEL_BG)


def _border_w(pipela_mod: Any | None) -> int:
    if pipela_mod is not None and hasattr(pipela_mod, "ui_px"):
        return max(2, int(pipela_mod.ui_px(2)))
    return 2


def selection_drag_rect_fill() -> QColor:
    c = QColor(T.ACCENT)
    c.setAlpha(75)
    return c


def selection_drag_rect_outline() -> QColor:
    return QColor(T.ACCENT)


def paint_selection_drag_rect(p: QPainter, r: QRect, *, pipela_mod: Any | None = None) -> None:
    """캡처/영역선택: 드래그 중 사각형."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(r, selection_drag_rect_fill())
    pen = QPen(selection_drag_rect_outline())
    pen.setWidth(_border_w(pipela_mod))
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(r)
    p.restore()


# 저장 ROI 미리보기(작은 툴윈) — `WA_TranslucentBackground` + 픽셀 알파
_REGION_PREVIEW_FILL_ALPHA_BASE = 48
_REGION_PREVIEW_FILL_ALPHA_PULSE = 12
_REGION_PREVIEW_STROKE_ALPHA = 220


def paint_region_preview_box(
    p: QPainter,
    w: int,
    h: int,
    *,
    pipela_mod: Any | None = None,
    t_sec: float | None = None,
) -> None:
    """감지 영역「미리보기」: 반투명 액센트 + 테두리 (모든 region_type 공통)."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    wi = max(1, w)
    hi = max(1, h)
    a = float(_REGION_PREVIEW_FILL_ALPHA_BASE)
    if t_sec is not None:
        a = _REGION_PREVIEW_FILL_ALPHA_BASE + _REGION_PREVIEW_FILL_ALPHA_PULSE * (
            0.5 + 0.5 * math.sin(float(t_sec) * 1.15)
        )
    a = max(20.0, min(100.0, a))
    fill = QColor(T.ACCENT)
    fill.setAlpha(int(a))
    p.fillRect(0, 0, wi, hi, fill)
    edge = QColor(T.ACCENT)
    edge.setAlpha(_REGION_PREVIEW_STROKE_ALPHA)
    pen = QPen(edge)
    pen.setWidth(_border_w(pipela_mod))
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRect(0, 0, max(1, wi - 1), max(1, hi - 1)))


def _template_hit_accent_hex(pipela_mod: Any, kind: str | None) -> str:
    d = getattr(pipela_mod, "_SETTINGS_TEMPLATE_HIT_ACCENT_BY_KIND", None)
    default = getattr(pipela_mod, "_SETTINGS_TEMPLATE_HIT_ACCENT_DEFAULT", T.ACCENT)
    if isinstance(d, dict) and kind:
        return str(d.get(kind, default))
    return str(default)


def paint_debug_template_match(
    p: QPainter,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    pipela_mod: Any,
    kind: str | None,
    t_sec: float,
) -> None:
    """템플릿 감지 1회 펄스 박스(내부 채움 + 종류별 액센트 테두리)."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    fill = QColor(T.ACCENT)
    a = 55 + int(25 * (0.5 + 0.5 * math.sin(float(t_sec) * 2.0)))
    fill.setAlpha(max(45, min(95, a)))
    p.fillRect(QRect(x, y, w, h), fill)
    acc = _template_hit_accent_hex(pipela_mod, kind)
    pen = QPen(QColor(acc))
    pen.setWidth(2)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRect(x, y, max(1, w - 1), max(1, h - 1)))
    p.restore()


def paint_debug_kill_counter_boxes(
    p: QPainter,
    label_rect: tuple[int, int, int, int] | None,
    num_rect: tuple[int, int, int, int] | None,
    *,
    kc_edge_hex: str,
    phase: int,
) -> None:
    """킬카운터 OCR 펄스 — 라벨/숫자 박스(액센트 반투명 윤곽 + 숫자 구역 강조)."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    hf = (float(phase % 6) / 6.0)
    v = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(hf * 6.283185307))
    col = QColor(kc_edge_hex)
    col.setAlpha(int(90 + 110 * v))
    pen = QPen(col)
    pen.setWidth(3)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if label_rect:
        x, y, rw, rh = label_rect
        p.drawRect(QRect(x, y, max(1, rw - 1), max(1, rh - 1)))
    kc2 = QColor(kc_edge_hex)
    kc2.setAlpha(230)
    pen2 = QPen(kc2)
    pen2.setWidth(2)
    p.setPen(pen2)
    if num_rect:
        x, y, rw, rh = num_rect
        p.drawRect(QRect(x, y, max(1, rw - 1), max(1, rh - 1)))
    p.restore()
