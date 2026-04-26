"""Qt 고해상도(DPI) — Windows 분수 배율 대응 및 보조 창 크기(논리 좌표).

스타일시트의 ``font-size`` 는 ``px`` 대신 ``pt``(1/72인치)를 쓰면 DPI에 맞게 렌더된다.
위젯 기하는 Qt6 논리 픽셀이며, 별도 배율 곱은 하지 않는다.

Win32 ``ClientToScreen`` / ``GetWindowRect``(클라이언트 화면 좌표)는 **물리 픽셀**이고,
프레임리스 Qt ``QWidget.setGeometry`` 는 **논리(DIP)** 를 쓰므로 오버레이는 반드시 변환한다."""

from __future__ import annotations

import sys
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication


def init_high_dpi() -> None:
    """QApplication 생성 전에 한 번 호출. 125%/150% 등에서 반올림·흐림 완화."""
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough,
    )


def _available_geometry():
    app = QApplication.instance()
    if app is None:
        return None
    s = app.primaryScreen()
    if s is None:
        return None
    return s.availableGeometry()


def hub_window_size() -> tuple[int, int]:
    """설정 허브 등 — 작은 노트북에서도 스크롤 가능한 범위로."""
    ag = _available_geometry()
    if ag is None:
        return 520, 640
    sw, sh = ag.width(), ag.height()
    w = min(720, max(360, int(sw * 0.40)))
    h = min(900, max(480, int(sh * 0.70)))
    return w, h


def dock_panel_size() -> tuple[int, int]:
    """제어창·킬 패널 — 화면 너비·높이 비율(논리 픽셀)."""
    ag = _available_geometry()
    if ag is None:
        return 400, 780
    sw, sh = ag.width(), ag.height()
    w = min(560, max(320, int(sw * 0.235)))
    h = min(1200, max(520, int(sh * 0.90)))
    return w, h


def get_dock_panel_wh(pipela_mod) -> tuple[int, int]:
    """
    메인·킬 패널이 **같이 쓰는** 논리 폭·높이.

    **런처 vs 게임 클라** 페이즈는 ``pipela_qt.dock_ui_phase.get_dock_panel_wh_for_current_phase`` 에서
    구분한다(기본: 클라이언트=전체 `dock_panel_size`, 런처=한 단계 좁힘).

    ``qt_dock_panel_w`` / ``h`` 는 매 호출 시 현재 페이즈에 맞게 갱신한다.
    """
    try:
        from pipela_qt.dock_ui_phase import get_dock_panel_wh_for_current_phase

        w, h = get_dock_panel_wh_for_current_phase(pipela_mod)
        w, h = max(8, int(w)), max(8, int(h))
        try:
            pipela_mod.qt_dock_panel_w = int(w)
            pipela_mod.qt_dock_panel_h = int(h)
        except Exception:
            pass
        return w, h
    except Exception:
        pass
    w, h = dock_panel_size()
    try:
        pipela_mod.qt_dock_panel_w = int(w)
        pipela_mod.qt_dock_panel_h = int(h)
    except Exception:
        pass
    return int(w), int(h)


def win32_physical_screen_rect_to_qt_overlay_geometry(
    pipela_mod: Any,
    anchor_hwnd: int,
    x_phys: int,
    y_phys: int,
    w_phys: int,
    h_phys: int,
) -> tuple[int, int, int, int]:
    """
    Win32 화면 좌표·크기(물리 픽셀) → 프레임리스 Qt 오버레이 ``setGeometry`` 용 논리 픽셀.
    Non-Windows 또는 hwnd 없으면 입력 그대로.
    """
    if sys.platform != "win32" or not anchor_hwnd:
        return (
            int(x_phys),
            int(y_phys),
            max(1, int(w_phys)),
            max(1, int(h_phys)),
        )
    try:
        sc = float(win32_dpi_scale_for_hwnd(pipela_mod, int(anchor_hwnd)))
        if sc <= 0.01:
            sc = 1.0
        # 폭·높이를 `round(w_phys/sc)`만 쓰면 좌·우(상·하) 라운딩이 어긋나 1 DIP 삐져나올 수 있음 —
        # 앵커 외곽(런처 스트립 등)과 정확히 맞추려면 **모서리**를 각각 스케일한 뒤 차이로 둔다.
        x_l = int(round(x_phys / sc))
        y_l = int(round(y_phys / sc))
        right_l = int(round((int(x_phys) + int(w_phys)) / sc))
        bottom_l = int(round((int(y_phys) + int(h_phys)) / sc))
        w_l = max(1, right_l - x_l)
        h_l = max(1, bottom_l - y_l)
        return (x_l, y_l, w_l, h_l)
    except Exception:
        return (
            int(x_phys),
            int(y_phys),
            max(1, int(w_phys)),
            max(1, int(h_phys)),
        )


def win32_dpi_scale_for_hwnd(pipela_mod, anchor_hwnd: int) -> float:
    """
    앵커 HWND 모니터의 effective DPI / 96.

    Win32 ``GetWindowRect`` / ``ClientToScreen`` 은 **물리 픽셀**이고,
    Qt 위젯 ``width()``·``setGeometry``(제어창)는 **논리(DIP)** 에 가깝다.
    도킹 시 둘을 섞지 않도록 물리 폭·좌표를 구할 때 곱한다.
    """
    try:
        dpi = int(pipela_mod.get_dpi_for_monitor_containing_window(int(anchor_hwnd)))
        if dpi <= 0:
            return 1.0
        return max(0.01, float(dpi) / 96.0)
    except Exception:
        return 1.0
