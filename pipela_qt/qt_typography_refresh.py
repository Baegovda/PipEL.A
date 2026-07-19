"""전역 UI pt 변경 후 Qt 스타일·창에 반영."""

from __future__ import annotations

from typing import Any

from PyQt6.QtWidgets import QApplication

from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.ui_adaptive import (
    set_root_font_pt,
    set_typography_layout_height_px,
    set_typography_layout_width_px,
)
from pipela_qt.qt_dock_anchor import resolve_dock_anchor_hwnd
from pipela_qt.qt_side_dock import anchor_client_inner_height_logical_qt


def _clamp_ui_font_pt(v: Any) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        n = 11
    return max(8, min(24, n))


def refresh_pipela_typography(pipela_mod) -> None:
    pt = _clamp_ui_font_pt(getattr(pipela_mod, "pipela_ui_font_pt", 11))
    pipela_mod.pipela_ui_font_pt = pt
    set_root_font_pt(float(pt))
    app = QApplication.instance()
    if app is not None:
        app.setFont(app_default_qfont(pt))

    win = getattr(pipela_mod, "_qt_control_main", None)
    if win is not None:
        try:
            set_typography_layout_width_px(int(win.width()))
        except Exception:
            pass
        h_ref = None
        try:
            ah = resolve_dock_anchor_hwnd(pipela_mod)
            if ah:
                h_ref = anchor_client_inner_height_logical_qt(pipela_mod, int(ah))
        except Exception:
            h_ref = None
        if h_ref is None:
            try:
                h_ref = max(8, int(win.height()))
            except Exception:
                h_ref = None
        if h_ref is not None:
            try:
                set_typography_layout_height_px(int(h_ref))
            except Exception:
                pass
        if hasattr(win, "apply_scaled_typography"):
            # 글꼴(pt) 변경은 같은 이벤트에서 즉시 반영(immediate) — coalesce 는 한 프레임 지연
            try:
                win.apply_scaled_typography(immediate=True)
            except TypeError:
                win.apply_scaled_typography()

    strip = getattr(pipela_mod, "_qt_title_bar_strip", None)
    if strip is not None and hasattr(strip, "apply_scaled_typography"):
        strip.apply_scaled_typography()

    if win is not None:
        kcw = getattr(win, "_kc_float", None)
        if kcw is not None and hasattr(kcw, "apply_scaled_typography"):
            kcw.apply_scaled_typography()

    try:
        from pipela_qt.panels.kill_counter_tier_table_dialog import (
            refresh_kill_counter_tier_table_typography_if_open,
        )

        refresh_kill_counter_tier_table_typography_if_open()
    except Exception:
        pass

    try:
        from pipela_qt.card_popup_shell import refresh_open_card_frameless_dialogs_scaled

        refresh_open_card_frameless_dialogs_scaled()
    except Exception:
        pass

    try:
        from pipela_qt.panels.thumbnail_preview_dialog import (
            refresh_open_image_inspect_cards_content_if_any,
        )

        refresh_open_image_inspect_cards_content_if_any()
    except Exception:
        pass
