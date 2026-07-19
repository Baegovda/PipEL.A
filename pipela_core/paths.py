"""Bundle root (SCRIPT_DIR), default PNG assets — PyInstaller / dev runs.

Bundled template PNGs and UI icons share ``SCRIPT_DIR/assets/`` (legacy ``templates/``
and ``icon/`` dirs are no longer used for shipped files).

``pipela_core`` lives under the repo root, so ``SCRIPT_DIR`` is ``dirname(dirname(paths.__file__))``
when running from source; frozen builds use ``sys._MEIPASS``.
"""

from __future__ import annotations

import os
import sys


def resolve_script_dir() -> str:
    if getattr(sys, "frozen", False):
        return str(sys._MEIPASS)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


SCRIPT_DIR = resolve_script_dir()
# Single shipped PNG folder (Qt icons, HUD, default match templates).
PIPELA_ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
# Name kept for call sites: defaults are filenames under assets/.
PIPELA_TEMPLATES_DIR = PIPELA_ASSETS_DIR


def migrate_legacy_bundle_template_path(saved_path):
    """If registry still points at an old bundle path and the file is missing, try ``assets/<basename>``."""
    if not saved_path:
        return saved_path
    try:
        sp = os.path.normpath(str(saved_path).strip())
    except Exception:
        return saved_path
    if os.path.isfile(sp):
        return sp
    fn = os.path.basename(sp.replace("\\", "/"))
    if not fn.lower().endswith(".png"):
        return saved_path
    cand = os.path.normpath(os.path.join(PIPELA_ASSETS_DIR, fn))
    if os.path.isfile(cand):
        return cand
    return saved_path


RIDE_TARGET_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "target.png")
RELOAD_NOBULLET_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "nobullet.png")
RELOAD_BULLET_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "bullet.png")
RELOAD_VAULT_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "vault.png")

AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "buybutton.png")
AMMO_RESTOCK_INVEN_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "inven.png")
AMMO_RESTOCK_BANK_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "bank.png")

CALL_MERC_1_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "call_merc_1.png")
CALL_MERC_2_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "call_merc_2.png")
CALL_MERC_3_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "call_merc_3.png")
CALL_MERC_4_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "call_merc_4.png")

START_GAME_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "start_game.png")
START_GAME_INTRO_SKIP_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "intro_skip.png")
START_GAME_ACCEPT_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "accept.png")

RIDE_ICON_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "ride.png")
PIPELA_ICON_DIR = PIPELA_ASSETS_DIR
# Window / taskbar / tray — PNG in assets/; EXE icon is root Pipela.ico when present.
PIPELA_APP_ICON_PATH = os.path.join(PIPELA_ICON_DIR, "vaultboy.png")
# Optional startup splash (`run_qt_application`). Entire `assets/` is bundled in PyInstaller.
PIPELA_SPLASH_IMAGE_PATH = os.path.join(PIPELA_ASSETS_DIR, "splash.png")
# HUD + control chrome — same assets/ folder as template defaults
CURSOR_RIDE_ICON_PATH = os.path.join(PIPELA_ICON_DIR, "chopper.png")
MOVE_ICON_PATH = os.path.join(PIPELA_ICON_DIR, "arrow.png")
FIRE_ICON_PATH = os.path.join(PIPELA_ICON_DIR, "gunfire.png")
# Flame Trigger cursor HUD (distinct from gunfire icon)
FLAME_TRIGGER_CURSOR_HUD_ICON_PATH = os.path.join(PIPELA_ICON_DIR, "padlock.png")
UI_ICON_RELOAD_PATH = os.path.join(PIPELA_ICON_DIR, "refresh-arrow.png")
UI_ICON_FLAME_PATH = os.path.join(PIPELA_ICON_DIR, "campfire.png")
UI_ICON_AMMO_PATH = os.path.join(PIPELA_ICON_DIR, "bullets.png")
UI_ICON_MERC_PATH = os.path.join(PIPELA_ICON_DIR, "merc.png")
UI_ICON_KILL_COUNTER_PATH = os.path.join(PIPELA_ICON_DIR, "statistics.png")
UI_ICON_HP_REFILL_PATH = os.path.join(PIPELA_ICON_DIR, "pharmacy.png")
UI_ICON_TERMINAL_PATH = os.path.join(PIPELA_ICON_DIR, "terminal.png")
UI_ICON_SETTINGS_PATH = os.path.join(PIPELA_ICON_DIR, "gear.png")
HP_REFILL_ZKEY_IMAGE_PATH = os.path.join(PIPELA_TEMPLATES_DIR, "zkey.png")
PIPELA_ICO_PATH = os.path.join(SCRIPT_DIR, "Pipela.ico")


def pipela_user_data_dir() -> str:
    """%LOCALAPPDATA%\\Pipela (없으면 생성 시도). 실패 시 SCRIPT_DIR."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("USERPROFILE") or ""
    if not base:
        base = SCRIPT_DIR
    d = os.path.join(base, "Pipela")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def template_capture_user_storage_dir() -> str:
    """드래그 캡처 PNG 저장 디렉터리 (%LOCALAPPDATA%\\Pipela\\templates)."""
    d = os.path.join(pipela_user_data_dir(), "templates")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d
