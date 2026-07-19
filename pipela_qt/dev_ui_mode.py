"""Developer UI mode — docked chrome without game/launcher anchor."""

from __future__ import annotations

import os
import sys
from typing import Any

_TRUTHY = frozenset({"1", "true", "yes", "on", "y"})
_FALSY = frozenset({"0", "false", "no", "off", "n"})


def pipela_dev_ui_enabled() -> bool:
    """Dev UI master switch.

    - Explicit: ``PIPELA_DEV_UI=1``, ``PIPELA_DEBUG_UI=1``, or ``--dev-ui``
    - Off: ``PIPELA_DEV_UI=0``, ``--no-dev-ui``, or frozen PyInstaller exe (unless forced on)
    - Default: **on** for ``python main.py`` (unfrozen) so F5/dev runs show panels without game
    """
    if "--dev-ui" in sys.argv:
        return True
    if "--no-dev-ui" in sys.argv:
        return False
    for key in ("PIPELA_DEV_UI", "PIPELA_DEBUG_UI"):
        raw = (os.environ.get(key, "") or "").strip().lower()
        if raw in _TRUTHY:
            return True
        if raw in _FALSY:
            return False
    if getattr(sys, "frozen", False):
        return False
    return True


def pipela_dev_ui_no_anchor(pipela_mod: Any) -> bool:
    """True when neither game nor launcher HWND is a valid dock anchor."""
    from pipela_qt.dock_ui_phase import UI_DOCK_PHASE_STANDBY, get_ui_dock_phase_from_session

    try:
        r_th = pipela_mod.refresh_target_hwnd_if_needed
        r_lu = pipela_mod.refresh_smart_updater_hwnd_if_needed
        is_min = pipela_mod.is_window_minimized
        th = r_th()
        luh = r_lu()
        return get_ui_dock_phase_from_session(pipela_mod, th, luh) == UI_DOCK_PHASE_STANDBY
    except Exception:
        return True


def pipela_dev_ui_standby_chrome(pipela_mod: Any) -> bool:
    """Show control + kill + dev title strip while standby (no game/launcher)."""
    return pipela_dev_ui_enabled() and pipela_dev_ui_no_anchor(pipela_mod)
