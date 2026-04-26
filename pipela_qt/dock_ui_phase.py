"""도킹 UI — **런처 페이즈** vs **클라이언트(게임) 페이즈** 를 나누고, 페이즈별 패널 폭·높이(논리 px)를 둔다.

- **client**: 이터널시티(target) HWND 가 있고 최소화가 아님 — 제어·킬·스트립 fallback 이 **게임 클라** 기준.
- **launcher**: 게임은 없/비활·스마트업데이터 런처만 — **런처창** 기준.
- **standby(대기 페이즈)**: 둘 다 없을 때(도킹 앵커 없음) — UI 크기는 클라와 동일 기본을 쓴다.

앵커 HWND 의존 API는 :func:`resolve_dock_anchor_hwnd` 가 이미
«게임 우선 → 없으면 런처» 이므로, 여기서는 *현재* 도킹 UI가
어느 ‘페이즈’에 해당하는지만 구분한다.
"""

from __future__ import annotations

import os
import time
from typing import Any

# pipela_mod.pipela_ui_dock_phase 및 외부와 공유하는 문자열
UI_DOCK_PHASE_STANDBY = "standby"  # 런처·게임 둘 다 없을 때(대기 페이즈)
UI_DOCK_PHASE_LAUNCHER = "launcher"
UI_DOCK_PHASE_CLIENT = "client"

# 제어창·스트립이 같은 틱에 여러 번 페이즈를 물을 때 refresh/Enum 부하↓ (ms, 0=끔)
_DOCK_PHASE_CACHE_TTL = max(
    0.0,
    float(os.environ.get("PIPELA_DOCK_PHASE_CACHE_MS", "28") or 28) / 1000.0,
)
_dock_phase_cache_mono: float = -1.0
_dock_phase_cache_phase: str | None = None


def get_ui_dock_phase(pipela_mod: Any) -> str:
    """이 순간의 도킹 UI 페이즈 — 레지스트리 저장하지 않는 런타임 값."""
    global _dock_phase_cache_mono, _dock_phase_cache_phase
    now = time.monotonic()
    if (
        _DOCK_PHASE_CACHE_TTL > 0.0
        and _dock_phase_cache_phase is not None
        and (now - _dock_phase_cache_mono) < _DOCK_PHASE_CACHE_TTL
    ):
        return _dock_phase_cache_phase
    th = pipela_mod.refresh_target_hwnd_if_needed()
    if th and not pipela_mod.is_window_minimized(int(th)):
        phase = UI_DOCK_PHASE_CLIENT
    else:
        luh = pipela_mod.refresh_smart_updater_hwnd_if_needed()
        if luh and not pipela_mod.is_window_minimized(int(luh)):
            phase = UI_DOCK_PHASE_LAUNCHER
        else:
            phase = UI_DOCK_PHASE_STANDBY
    if _DOCK_PHASE_CACHE_TTL > 0.0:
        _dock_phase_cache_mono = time.monotonic()
        _dock_phase_cache_phase = phase
    return phase


def get_ui_dock_phase_from_session(
    pipela_mod: Any,
    target_hwnd: Any,
    launcher_hwnd: Any,
) -> str:
    """이미 갱신된 ``target_hwnd`` / ``launcher_hwnd`` 로 페이즈만 판별 — ``refresh_*`` 재호출 없음."""
    if target_hwnd and not pipela_mod.is_window_minimized(int(target_hwnd)):
        return UI_DOCK_PHASE_CLIENT
    if launcher_hwnd and not pipela_mod.is_window_minimized(int(launcher_hwnd)):
        return UI_DOCK_PHASE_LAUNCHER
    return UI_DOCK_PHASE_STANDBY


def is_start_game_launcher_template1_effective_on(
    pipela_mod: Any,
    snap: Any | None = None,
) -> bool:
    """
    StartGame **런처 START(템플릿①)** 감지·자동클릭이 켜진 것으로 볼지.

    ``start_game_launcher_active`` (스냅/모듈)가 True 이거나 **런처 UI 페이즈**이면 True.
    ``snap`` 이 None 이면 레지 스냅 없이 모듈 속성만 사용(제어창 등 경량 경로).
    """
    from pipela_core.registry_snapshot_read import snapshot_bool

    on = bool(getattr(pipela_mod, "start_game_launcher_active", False))
    if snap is not None:
        if snapshot_bool(snap, "start_game_launcher_active", on):
            return True
    elif on:
        return True
    return get_ui_dock_phase(pipela_mod) == UI_DOCK_PHASE_LAUNCHER


def _client_dock_ui_wh() -> tuple[int, int]:
    """클라이언트(게임) 페이즈 — 제어·킬·스트립과 동일한 기본 도킹 패널."""
    from pipela_qt.dpi import dock_panel_size

    w, h = dock_panel_size()
    return int(w), int(h)


def _launcher_dock_ui_wh() -> tuple[int, int]:
    """런처 페이즈 — 스마트업데이터/런처창에 붙이는 UI (좁고 낮은 상한)."""
    from pipela_qt.dpi import dock_panel_size

    w, h = dock_panel_size()
    w = min(420, int(w))
    h = min(900, int(h))
    return max(8, w), max(8, h)


def get_dock_panel_wh_for_current_phase(pipela_mod: Any) -> tuple[int, int]:
    """
    :func:`pipela_qt.dpi.get_dock_panel_wh` 가 쓰는 (w, h) — **페이즈별**로 나눔.

    * ``launcher`` → :func:`_launcher_dock_ui_wh`
    * ``client`` / ``standby``(대기) → :func:`_client_dock_ui_wh`

    ``pipela_mod.pipela_ui_dock_phase`` 를 여기서 갱신한다.
    """
    ph = get_ui_dock_phase(pipela_mod)
    try:
        pipela_mod.pipela_ui_dock_phase = ph
    except Exception:
        pass
    if ph == UI_DOCK_PHASE_LAUNCHER:
        w, h = _launcher_dock_ui_wh()
    else:
        w, h = _client_dock_ui_wh()
    return max(8, int(w)), max(8, int(h))
