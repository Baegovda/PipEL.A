"""설정 패널 — 백그라운드 시퀀스 단계에 맞춰 QScrollArea 자동 스크롤."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from PyQt6.QtCore import QAbstractAnimation, QEasingCurve, QPropertyAnimation
from PyQt6.QtWidgets import QScrollArea, QWidget

from pipela_qt.ui_adaptive import scale_px_h, scale_px_v

# main 모듈 `settings_sequence_autoscroll_steps` 키와 동기
FEAT_RELOAD = "reload"
FEAT_CALL_MERC = "call_merc"
FEAT_AMMO_RESTOCK = "ammo_restock"
FEAT_START_GAME = "start_game"


def _steps(m: Any) -> dict[str, int]:
    d = getattr(m, "settings_sequence_autoscroll_steps", None)
    if not isinstance(d, dict):
        d = {}
        setattr(m, "settings_sequence_autoscroll_steps", d)
    return d


def seq_scroll_set(m: Any, feature: str, step: int) -> None:
    _steps(m)[str(feature)] = int(step)


def seq_scroll_get(m: Any, feature: str, default: int = 0) -> int:
    try:
        return int(_steps(m).get(str(feature), default))
    except (TypeError, ValueError):
        return int(default)


def _scroll_targets_xy(
    scroll: QScrollArea,
    target: QWidget,
    xm: int,
    ym: int,
) -> tuple[int, int]:
    """ensureWidgetVisible 과 동일한 최소 이동으로 보이게 할 스크롤바 value (가로, 세로)."""
    w = scroll.widget()
    if w is None:
        return 0, 0
    vp = scroll.viewport()
    tl = target.mapTo(w, target.rect().topLeft())
    br = target.mapTo(w, target.rect().bottomRight())
    vbar = scroll.verticalScrollBar()
    hbar = scroll.horizontalScrollBar()
    cur_y = int(vbar.value())
    cur_x = int(hbar.value())
    vh = max(1, vp.height())
    vw = max(1, vp.width())
    y_top, y_bot = int(tl.y()), int(br.y())
    x_left, x_right = int(tl.x()), int(br.x())
    y = cur_y
    if y_top - ym < y:
        y = y_top - ym
    if y_bot + ym > y + vh:
        y = y_bot + ym - vh
    y = max(vbar.minimum(), min(vbar.maximum(), y))
    x = cur_x
    if x_left - xm < x:
        x = x_left - xm
    if x_right + xm > x + vw:
        x = x_right + xm - vw
    x = max(hbar.minimum(), min(hbar.maximum(), x))
    return x, y


def _stop_feature_scroll_anims(panel: QWidget, feature: str) -> None:
    key = f"_seq_autoscroll_anims_{feature}"
    anims: list[QPropertyAnimation] | None = getattr(panel, key, None)
    if not anims:
        return
    for a in anims:
        if a.state() == QAbstractAnimation.State.Running:
            a.stop()
    setattr(panel, key, None)


def _animate_scrollbars(
    panel: QWidget,
    feature: str,
    scroll: QScrollArea,
    target_x: int,
    target_y: int,
    duration_ms: int,
) -> None:
    vbar = scroll.verticalScrollBar()
    hbar = scroll.horizontalScrollBar()
    sx, sy = int(hbar.value()), int(vbar.value())
    anims: list[QPropertyAnimation] = []
    if sy != target_y:
        av = QPropertyAnimation(vbar, b"value", panel)
        av.setDuration(duration_ms)
        av.setStartValue(sy)
        av.setEndValue(target_y)
        av.setEasingCurve(QEasingCurve(QEasingCurve.Type.OutCubic))
        anims.append(av)
    if sx != target_x:
        ah = QPropertyAnimation(hbar, b"value", panel)
        ah.setDuration(duration_ms)
        ah.setStartValue(sx)
        ah.setEndValue(target_x)
        ah.setEasingCurve(QEasingCurve(QEasingCurve.Type.OutCubic))
        anims.append(ah)
    if not anims:
        return
    setattr(panel, f"_seq_autoscroll_anims_{feature}", anims)
    for a in anims:
        a.start()


def apply_sequence_autoscroll(
    *,
    panel: QWidget,
    scroll: QScrollArea,
    pipela_mod: Any,
    feature: str,
    targets: Sequence[QWidget],
    active_check: Callable[[Any], bool] | None = None,
    x_margin_px: int | None = None,
    y_margin_px: int | None = None,
) -> None:
    if not panel.isVisible():
        return
    last_attr = f"_seq_autoscroll_last_{feature}"
    if active_check is not None and not active_check(pipela_mod):
        setattr(panel, last_attr, None)
        return
    if not targets:
        return
    st = seq_scroll_get(pipela_mod, feature, 0)
    st = max(0, min(len(targets) - 1, st))
    if getattr(panel, last_attr, None) == st:
        return
    setattr(panel, last_attr, st)
    xm = int(scale_px_v(8)) if x_margin_px is None else int(x_margin_px)
    ym = int(scale_px_v(24)) if y_margin_px is None else int(y_margin_px)
    tgt = targets[st]
    tx, ty = _scroll_targets_xy(scroll, tgt, xm, ym)
    dur = max(200, min(480, int(scale_px_v(340))))
    _stop_feature_scroll_anims(panel, feature)
    _animate_scrollbars(panel, feature, scroll, tx, ty, dur)
