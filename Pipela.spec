# -*- mode: python ; coding: utf-8 -*-
# 진입: main.py — Qt 전용(main_qt). 표준 GUI 바인딩 없음.

import os

_native_binaries = []
if os.path.isfile("pipela_native.pyd"):
    _native_binaries = [("pipela_native.pyd", ".")]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=_native_binaries,
    datas=[
        ('Pipela.ico', '.'),
        ('assets', 'assets'),
        ('native/cursor_hud_dcomp/build/cursor_hud_dcomp.dll', 'native/cursor_hud_dcomp'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # pipela_core — 동적/지연 import 경로 대비(Analysis 가 일부만 잡을 때)
        'pipela_core',
        'pipela_core.ammo_restock_catalog',
        'pipela_core.ammo_restock_templates',
        'pipela_core.call_merc_catalog',
        'pipela_core.call_merc_match',
        'pipela_core.call_merc_templates',
        'pipela_core.config_parse',
        'pipela_core.config_registry_extended',
        'pipela_core.config_registry_kill_counter',
        'pipela_core.config_registry_load',
        'pipela_core.kill_counter_layout',
        'pipela_core.kill_counter_tier_data',
        'pipela_core.kill_counter_tier_colors',
        'pipela_core.config_registry_query',
        'pipela_core.config_registry_save',
        'pipela_core.config_registry_tables',
        'pipela_core.console_log_constants',
        'pipela_core.display_timing',
        'pipela_core.flame_trigger_automation',
        'pipela_core.image_registry',
        'pipela_core.native_bridge',
        'pipela_core.native_module',
        'pipela_core.worker_runtime_bridge',
        'pipela_core.primary_monitor',
        'pipela_core.region_dispatch',
        'pipela_core.registry_constants',
        'pipela_core.registry_config_snapshot',
        'pipela_core.registry_snapshot_read',
        'pipela_core.reload_idle_secondary',
        'pipela_core.reload_nobullet_bullet',
        'pipela_core.reload_sequence',
        'pipela_core.scale_geometry',
        'pipela_core.template_apply',
        'pipela_core.template_capture_catalog',
        'pipela_core.template_capture_region',
        'pipela_core.template_debug_match',
        'pipela_core.template_match_config',
        'pipela_core.template_matching',
        'pipela_core.template_roi',
        'pipela_core.ui_fonts',
        'pipela_core.version_info',
        'pipela_core.vision_capture',
        'pipela_core.vision_lazy',
        'pipela_core.win32_game_windows',
        'pipela_core.win32_input_constants',
        'pipela_core.win32_window_ops',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 번들에 끌려오기 쉬운 대형·미사용 스택(직접 import 안 해도 의존으로 들어올 때)
        'matplotlib', 'scipy', 'pandas', 'sklearn', 'skimage',
        'IPython', 'jupyter', 'notebook', 'pytest',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# AGENT: onedir distribution (dist/Pipela/) — not onefile; ship as zip via scripts/package_release.bat.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Pipela',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['Pipela.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Pipela',
)
