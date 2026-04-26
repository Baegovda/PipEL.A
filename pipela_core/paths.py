"""번들 루트(SCRIPT_DIR)·템플릿·아이콘 경로 — PyInstaller / 소스 공통.

`pipela_core` 는 `Pipela/pipela_core/` 에 있으므로, 소스 실행 시 루트는
`dirname(dirname(paths.__file__))` (= main.py 가 있는 디렉터리).
frozen 시에는 `sys._MEIPASS` 와 동일하게 맞춘다.
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
PIPELA_TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")


def migrate_legacy_bundle_template_path(saved_path):
    """레지스트리에 예전 번들 루트(.../nobullet.png)가 남아 있는데 파일이 없으면 templates/ 동일 파일명으로 대체."""
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
    cand = os.path.normpath(os.path.join(PIPELA_TEMPLATES_DIR, fn))
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
PIPELA_ICON_DIR = os.path.join(SCRIPT_DIR, "icon")
# 창 제목 표시줄·작업 표시줄·트레이(Qt) — PNG 우선. PyInstaller EXE 아이콘은 루트 `Pipela.ico`(빌드 시 동일 그래픽 권장).
PIPELA_APP_ICON_PATH = os.path.join(PIPELA_ICON_DIR, "vaultboy.png")
# HUD·제어창 공통 — `icon/*.png` (소스/번들 루트의 icon 폴더)
CURSOR_RIDE_ICON_PATH = os.path.join(PIPELA_ICON_DIR, "chopper.png")
MOVE_ICON_PATH = os.path.join(PIPELA_ICON_DIR, "arrow.png")
FIRE_ICON_PATH = os.path.join(PIPELA_ICON_DIR, "gunfire.png")
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
