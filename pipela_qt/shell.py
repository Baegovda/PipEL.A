"""Qt 앱 기동 — main 모듈 pipela_mod 와 동일 인스턴스 사용 (이중 import 방지)."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from PyQt6.QtCore import QCoreApplication, QTimer, Qt

from pipela_core.version_info import PIPELA_APP_DISPLAY_NAME
from pipela_qt.dpi import get_dock_panel_wh, init_high_dpi
from pipela_qt.control_main import PipelaQtMainWindow
from pipela_qt.qt_icons import qt_application_icon
from pipela_qt.cursor_hud import QtCursorHud, QtFlameStartBanner, pipela_cursor_hud_startup_wanted
from pipela_qt.main_window import configure_app
from pipela_qt.debug_pulse_overlay import QtDebugPulseOverlay
from pipela_qt.game_title_bar_overlay import QtGameTitleBarStrip
from pipela_qt.overlay import QtGameOverlay
from pipela_qt.taskbar_hide import PipelaTaskbarHideFilter


def run_qt_application(*, pipela_mod, start_tray_only: bool) -> None:
    init_high_dpi()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    if sys.platform == "win32":
        app.installEventFilter(PipelaTaskbarHideFilter(app))
    configure_app(app, ui_font_pt=getattr(pipela_mod, "pipela_ui_font_pt", 11))
    _app_icon = qt_application_icon()
    if not _app_icon.isNull():
        app.setWindowIcon(_app_icon)
    get_dock_panel_wh(pipela_mod)

    overlay = QtGameOverlay(pipela_mod)
    pipela_mod._qt_game_overlay = overlay
    overlay.show()

    title_bar_strip = QtGameTitleBarStrip(pipela_mod)
    pipela_mod._qt_title_bar_strip = title_bar_strip
    title_bar_strip.show()

    pipela_mod._qt_debug_pulse_overlay = QtDebugPulseOverlay(pipela_mod)

    if pipela_cursor_hud_startup_wanted(pipela_mod):
        _cursor_hud = QtCursorHud(pipela_mod)
        pipela_mod._qt_cursor_hud = _cursor_hud
        # 같은 스택에서 즉시 show 하면 일부 환경에서 (0,0) 근처 1프레임이 섞일 수 있음 —
        # 좌표는 __init__ 에서 먼저 _HIDDEN 으로 두고, 다음 틱에 연다.
        QTimer.singleShot(0, _cursor_hud.show)
    else:
        pipela_mod._qt_cursor_hud = None
    _flame_banner = QtFlameStartBanner(pipela_mod)

    win = PipelaQtMainWindow(pipela_mod, start_tray_only=start_tray_only)
    pipela_mod._qt_control_main = win
    try:
        from pipela_core.ai_debug_session_log import get_session_log_path, log_heartbeat_pipela_mod

        _ldp = get_session_log_path()
        if _ldp is not None:
            pipela_mod.AI_DEBUG_LOG_PATH = str(_ldp)

        def _ai_debug_hb() -> None:
            try:
                log_heartbeat_pipela_mod(pipela_mod)
            except Exception:
                pass

        _ai_hb = QTimer(win)
        _ai_hb.setInterval(45_000)
        _ai_hb.timeout.connect(_ai_debug_hb)
        _ai_hb.start()
        QTimer.singleShot(4_000, _ai_debug_hb)
    except Exception:
        pass
    if not start_tray_only:
        try:
            print(
                f"[{PIPELA_APP_DISPLAY_NAME}] Qt 제어창 — 게임 옆에 자동 도킹. 안 보이면 트레이 «제어창 표시». 종료는 트레이 메뉴.",
                flush=True,
            )
        except Exception:
            pass

    tray = QSystemTrayIcon(_app_icon, app)
    tray.setToolTip(f"{PIPELA_APP_DISPLAY_NAME} (Qt)")
    menu = QMenu()
    show_act = menu.addAction("제어창 표시")
    show_act.triggered.connect(win.show)
    quit_act = menu.addAction("종료")

    def _quit_from_tray() -> None:
        # QueuedConnection 으로 이미 메뉴가 닫힌 뒤 메인 루프에서 실행됨.
        # tray.hide() 는 aboutToQuit 에서 — quit 직전 hide 가 일부 Windows 에서 루프를 막는 사례가 있음.
        try:
            app.closeAllWindows()
        except Exception:
            pass
        QCoreApplication.exit(0)

    quit_act.triggered.connect(_quit_from_tray, Qt.ConnectionType.QueuedConnection)
    tray.setContextMenu(menu)
    tray.setVisible(True)

    def _tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            win.show()

    tray.activated.connect(_tray_activated)

    def _start_bg():
        pipela_mod._start_pipela_background_threads_and_listeners()

    QTimer.singleShot(int(pipela_mod.PIPELA_BACKGROUND_START_DELAY_MS), _start_bg)

    def _restore_saved_region_preview() -> None:
        try:
            pipela_mod.region_preview_try_restore_saved()
        except Exception:
            pass

    QTimer.singleShot(int(pipela_mod.display_aligned_wall_ms(550.0)), _restore_saved_region_preview)
    QTimer.singleShot(int(pipela_mod.display_aligned_wall_ms(2800.0)), _restore_saved_region_preview)

    def _restore_stdout():
        sys.stdout = sys.__stdout__

    def _persist_region_preview_before_quit() -> None:
        try:
            pipela_mod._region_preview_sync_persist_from_live()
        except Exception:
            pass

    def _hide_tray_on_quit() -> None:
        try:
            tray.hide()
        except Exception:
            pass

    app.aboutToQuit.connect(_hide_tray_on_quit)
    app.aboutToQuit.connect(_persist_region_preview_before_quit)
    app.aboutToQuit.connect(_restore_stdout)
    app.exec()
    _hud_done = getattr(pipela_mod, "_qt_cursor_hud", None)
    if _hud_done is not None:
        try:
            _hud_done.close()
        except Exception:
            pass
    title_bar_strip.close()
    overlay.close()
