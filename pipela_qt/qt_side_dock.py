"""게임 앵커 기준 좌/우 패널 도킹 — 제어창(왼)·킬(오른)·스트립 보조 좌표가 동일 수학을 쓰도록."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Literal

from pipela_core.win32_window_ops import (
    dock_outer_rect_touch_client_left,
    dock_outer_rect_touch_client_right,
    get_monitor_work_rect_phys,
)
from pipela_qt.dpi import win32_dpi_scale_for_hwnd

SideDockSide = Literal["left", "right"]


def anchor_client_inner_height_logical_qt(pipela_mod: Any, anchor_hwnd: int) -> int | None:
    """앵커 창 클라이언트 높이를 Qt 논리 px로. ``compute_side_dock_layout`` 의 ``h_log`` 와 동일 규칙."""
    try:
        ah = int(anchor_hwnd)
        if not ah:
            return None
        cr = pipela_mod.get_window_rect(ah)
        if not cr or int(cr[2]) <= int(cr[0]) or int(cr[3]) <= int(cr[1]):
            return None
        fh_phys = max(8, int(cr[3]) - int(cr[1]))
        scale = float(win32_dpi_scale_for_hwnd(pipela_mod, ah))
        if scale <= 0.01:
            scale = 1.0
        return max(8, int(round(fh_phys / scale)))
    except Exception:
        return None


def clamp_dock_logical_geometry(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
    """도킹 Qt 좌표·크기 안전 클램프 — 과도한 setGeometry 로 인한 불안정 완화."""
    from PyQt6.QtGui import QGuiApplication

    w = max(8, min(int(w), 8192))
    h = max(8, min(int(h), 16384))
    x = int(x)
    y = int(y)
    try:
        scr = QGuiApplication.primaryScreen()
        if scr is not None:
            ag = scr.availableGeometry()
            margin = 32000
            xa = ag.x() - margin
            ya = ag.y() - margin
            xr = ag.x() + ag.width() + margin
            yr = ag.y() + ag.height() + margin
            x = max(xa, min(x, xr - w))
            y = max(ya, min(y, yr - h))
    except Exception:
        pass
    x = max(-65535, min(x, 65535))
    y = max(-65535, min(y, 65535))
    return (x, y, w, h)


@dataclass(frozen=True)
class SideDockLayout:
    x_phys: int
    y_phys: int
    fw_phys: int
    fh_phys: int
    scale: float
    w_log: int
    h_log: int
    x_log: int
    y_log: int
    dedupe_sig: object


def chrome_outer_rect_plausible_for_left_dock(
    ch_rect: tuple[int, int, int, int],
    cr: tuple[int, int, int, int],
    *,
    tol_phys: int = 36,
) -> bool:
    """제어창 외곽 오른쪽이 앵커 클라이언트 왼쪽에 붙어 있을 때만 Win32 제어창 좌표를 신뢰."""
    try:
        _gl, _gt, gr, _gb = (int(x) for x in ch_rect)
        cl = int(cr[0])
    except Exception:
        return False
    return abs(int(gr) - cl) <= int(tol_phys)


def compute_side_dock_layout(
    pipela_mod: Any,
    anchor: int,
    *,
    dock_w_log: int,
    side: SideDockSide,
    gr: tuple[int, int, int, int] | None = None,
    cr: tuple[int, int, int, int] | None = None,
) -> SideDockLayout | None:
    """앵커 HWND 기준 패널 물리·논리 사각형. ``gr`` 비어 있고 ``cr``만 있으면 제어창과 동일하게 ``gr`` 폴백."""
    ah = int(anchor)
    if gr is None:
        gr = pipela_mod.get_window_outer_rect_screen(ah)
    if cr is None:
        cr = pipela_mod.get_window_rect(ah)
    if (not gr) and cr and cr[2] > cr[0] and cr[3] > cr[1]:
        gr = (int(cr[0]), int(cr[1]), int(cr[2]), int(cr[3]))
    if not gr:
        return None
    ol, ot, o_right, ob = (int(x) for x in gr)
    scale = float(win32_dpi_scale_for_hwnd(pipela_mod, ah))
    if scale <= 0.01:
        scale = 1.0
    dock_w_log = max(8, int(dock_w_log))
    fw_phys = max(8, int(round(dock_w_log * scale)))
    # 해상도 전환 직후 클라 높이가 1~7px처럼 잠깐만 잡히면 None → 도킹 실패 → dedupe 에 걸려 갱신 안 됨.
    fh_phys = max(
        8,
        int(cr[3] - cr[1]) if cr and (cr[2] > cr[0]) else int(ob - ot),
    )
    y_phys = int(cr[1]) if cr and (cr[2] > cr[0]) else int(ot)
    if side == "left":
        snap = int(cr[0]) if cr and (cr[2] > cr[0]) else int(ol)
        x_phys, y_phys, fw_phys, fh_phys = dock_outer_rect_touch_client_left(
            ah, snap, y_phys, fw_phys, fh_phys,
        )
        dedupe_sig = (snap, ol, ot, o_right, x_phys, y_phys, fw_phys, fh_phys)
    else:
        snap = int(cr[2]) if cr and (cr[2] > cr[0]) else int(o_right)
        x_phys, y_phys, fw_phys, fh_phys = dock_outer_rect_touch_client_right(
            ah, snap, y_phys, fw_phys, fh_phys,
        )
        dedupe_sig = (snap, ol, ot, o_right, ob, x_phys, y_phys, fw_phys, fh_phys)
    fw_phys = max(8, int(fw_phys))
    fh_phys = max(8, int(fh_phys))
    w_log = max(8, int(round(fw_phys / scale)))
    h_log = max(8, int(round(fh_phys / scale)))
    x_log = int(round(x_phys / scale))
    y_log = int(round(y_phys / scale))
    return SideDockLayout(
        x_phys=int(x_phys),
        y_phys=int(y_phys),
        fw_phys=int(fw_phys),
        fh_phys=int(fh_phys),
        scale=scale,
        w_log=w_log,
        h_log=h_log,
        x_log=x_log,
        y_log=y_log,
        dedupe_sig=dedupe_sig,
    )


def compute_dock_pair_fill_w_log(
    pipela_mod: Any, anchor_hwnd: int | None,
) -> int | None:
    """앵커 클라 좌우 작업영역 여백을 같은 폭 패널이 동시에 쓸 수 있는 논리 폭(DOCK_PAIR 패널 W_MAX 무시).

    게임 클라 왼쪽 ~ 모니터 work 왼, 클라 오른 ~ work 오른 각각 허용 물리 폭 중 작은 값.
    """
    if not anchor_hwnd:
        return None
    ah = int(anchor_hwnd)
    if ah <= 0:
        return None
    try:
        cr = pipela_mod.get_window_rect(ah)
    except Exception:
        return None
    if not cr or len(cr) < 4 or int(cr[2]) <= int(cr[0]):
        return None
    from pipela_qt.dock_panel_pair_resize import DOCK_PAIR_PANEL_W_MIN

    c0 = int(cr[0])
    c2 = int(cr[2])
    use_win32 = sys.platform == "win32"

    wl: int | None = None
    wr: int | None = None
    if use_win32:
        work = get_monitor_work_rect_phys(ah)
        if not work:
            return None
        wl, _, wr, _ = (int(x) for x in work)
    else:
        try:
            from PyQt6.QtGui import QGuiApplication

            scr = QGuiApplication.primaryScreen()
            if scr is None:
                return None
            ag = scr.availableGeometry()
            wl = int(ag.x())
            wr = int(ag.x() + ag.width())
        except Exception:
            return None

    space_left = c0 - int(wl)
    space_right = int(wr) - c2
    w_phys = min(max(8, space_left), max(8, space_right))
    if w_phys < 8:
        return None

    if use_win32:
        try:
            sc = float(win32_dpi_scale_for_hwnd(pipela_mod, ah))
        except Exception:
            sc = 1.0
        if sc <= 0.01:
            sc = 1.0
        w_log = int(round(float(w_phys) / sc))
    else:
        w_log = int(w_phys)

    return max(DOCK_PAIR_PANEL_W_MIN, min(int(w_log), 8192))


def apply_dock_pair_width_reset(pipela_mod: Any, main: Any, *, w_log: int) -> None:
    """제어창·킬 패널 동일 폭 반영 후 저장 및 리도킹(더블클릭 채움 등). 상한만 8192 로 막음."""
    from PyQt6.QtCore import QTimer

    from pipela_qt.dock_panel_pair_resize import DOCK_PAIR_PANEL_W_MIN

    w = max(DOCK_PAIR_PANEL_W_MIN, min(int(w_log), 8192))
    try:
        main._dock_w = w
        main._last_dock_sig = None
        main._last_standby_sig = None
    except Exception:
        return
    kc = getattr(main, "_kc_float", None)
    if kc is not None:
        try:
            kc._dock_w = w
            kc._last_dock_sig = None
        except Exception:
            pass
    try:
        setattr(main, "_paired_kill_width_pending", None)
    except Exception:
        pass
    try:
        pipela_mod.control_panel_w = w
        pipela_mod.kill_counter_panel_w = w
    except Exception:
        pass
    ss = getattr(pipela_mod, "schedule_save_config", None)
    if callable(ss):
        try:
            ss()
        except Exception:
            pass
    if kc is not None:
        QTimer.singleShot(0, kc.dock_to_right_of_target_game)
    try:
        QTimer.singleShot(0, lambda: main._dock_to_anchor(force=True))
    except Exception:
        pass


def reset_dock_pair_width_to_monitor_fill(*, pipela_mod: Any, main: Any) -> None:
    """리사이즈 가장자리 더블클릭 등 — 작업영역 채움 폭으로 동기화(앵커 없으면 프리셋 clamp)."""
    from pipela_qt.dock_panel_pair_resize import clamp_dock_pair_panel_w
    from pipela_qt.dpi import get_dock_panel_wh
    from pipela_qt.qt_dock_anchor import resolve_dock_anchor_hwnd

    ah = resolve_dock_anchor_hwnd(pipela_mod)
    w_fill: int | None = None
    if ah:
        try:
            w_fill = compute_dock_pair_fill_w_log(pipela_mod, int(ah))
        except Exception:
            w_fill = None
    if w_fill is None:
        w_fill = clamp_dock_pair_panel_w(get_dock_panel_wh(pipela_mod)[0])
    apply_dock_pair_width_reset(pipela_mod, main, w_log=w_fill)
