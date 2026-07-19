"""Qt 앱 기동 — main 모듈 pipela_mod 와 동일 인스턴스 사용 (이중 import 방지)."""

from __future__ import annotations

import sys
import threading

from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from pipela_qt.dialog_dismiss_on_outside import PipelaApplication
from PyQt6.QtCore import QCoreApplication, QTimer, Qt

from pipela_core.version_info import PIPELA_APP_DISPLAY_NAME
from pipela_qt.dpi import dock_panel_size, get_dock_panel_wh, init_high_dpi
from pipela_qt.control_main import PipelaQtMainWindow
from pipela_qt.qt_icons import qt_application_icon
from pipela_qt.cursor_hud import QtCursorHud, QtFlameStartBanner
from pipela_qt.main_window import configure_app
from pipela_qt.debug_pulse_overlay import QtDebugPulseOverlay
from pipela_qt.game_title_bar_overlay import QtGameTitleBarStrip
from pipela_qt.overlay import QtGameOverlay
from pipela_qt.taskbar_hide import PipelaTaskbarHideFilter
from pipela_qt.splash_screen import create_startup_splash, finish_startup_splash


def _safe_get_dock_panel_wh(pipela_mod) -> tuple[int, int]:
    """AGENT: avoid startup hard-freeze if phase probe blocks on Win32 path."""
    result: dict[str, tuple[int, int] | BaseException] = {}

    def _work() -> None:
        try:
            result["value"] = get_dock_panel_wh(pipela_mod)
        except BaseException as e:  # pragma: no cover - defensive path
            result["error"] = e

    t = threading.Thread(target=_work, daemon=True)
    t.start()
    t.join(timeout=0.35)
    if t.is_alive():
        w, h = dock_panel_size()
        try:
            pipela_mod.qt_dock_panel_w = int(w)
            pipela_mod.qt_dock_panel_h = int(h)
        except Exception:
            pass
        return int(w), int(h)
    err = result.get("error")
    if err is not None:
        w, h = dock_panel_size()
        try:
            pipela_mod.qt_dock_panel_w = int(w)
            pipela_mod.qt_dock_panel_h = int(h)
        except Exception:
            pass
        return int(w), int(h)
    value = result.get("value")
    if isinstance(value, tuple) and len(value) == 2:
        return int(value[0]), int(value[1])
    w, h = dock_panel_size()
    return int(w), int(h)


def run_qt_application(*, pipela_mod, start_tray_only: bool) -> None:
    init_high_dpi()
    app = PipelaApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    if sys.platform == "win32":
        app.installEventFilter(PipelaTaskbarHideFilter(app))
    configure_app(app, ui_font_pt=getattr(pipela_mod, "pipela_ui_font_pt", 11))
    _app_icon = qt_application_icon()
    if not _app_icon.isNull():
        app.setWindowIcon(_app_icon)
    _safe_get_dock_panel_wh(pipela_mod)
    _splash = create_startup_splash(app, pipela_mod)

    def _splash_raise() -> None:
        s = _splash
        if s is None:
            return
        try:
            s.raise_()
            app.processEvents()
        except Exception:
            pass

    def _splash_prog(m: float) -> None:
        s = _splash
        if s is None:
            return
        try:
            s.set_loading_target(m)
        except Exception:
            pass

    def _splash_msg(text: str) -> None:
        s = _splash
        if s is None:
            return
        try:
            s.set_loading_message(text)
        except Exception:
            pass

    _splash_msg("게임 오버레이 초기화 중…")
    overlay = QtGameOverlay(pipela_mod)
    pipela_mod._qt_game_overlay = overlay
    overlay.show()
    _splash_raise()
    _splash_msg("타이틀 바 오버레이 로딩…")
    _splash_prog(0.32)

    title_bar_strip = QtGameTitleBarStrip(pipela_mod)
    pipela_mod._qt_title_bar_strip = title_bar_strip
    title_bar_strip.show()
    _splash_raise()
    _splash_msg("커서 HUD 초기화…")
    _splash_prog(0.53)

    pipela_mod._qt_debug_pulse_overlay = QtDebugPulseOverlay(pipela_mod)

    _cursor_hud = QtCursorHud(pipela_mod)
    pipela_mod._qt_cursor_hud = _cursor_hud
    # 같은 스택에서 즉시 show 하면 일부 환경에서 (0,0) 근처 1프레임이 섞일 수 있음 —
    # 좌표는 __init__ 에서 먼저 _HIDDEN 으로 두고, 다음 틱에 연다.
    QTimer.singleShot(0, _cursor_hud.show)
    _flame_banner = QtFlameStartBanner(pipela_mod)

    _splash_msg("설정 패널 구성…")
    _splash_prog(0.66)
    win = PipelaQtMainWindow(pipela_mod, start_tray_only=start_tray_only)
    _splash_raise()
    _splash_msg("트레이·백그라운드 시작…")
    _splash_prog(0.93)
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
            # ASCII only: Windows cp949 consoles may throw on em dash / guillemets (print swallowed by caller).
            print(
                f"[{PIPELA_APP_DISPLAY_NAME}] Qt control window: dock beside game; if hidden use tray "
                "\"Show control window\" / quit from tray menu.",
                flush=True,
            )
        except Exception:
            pass

    tray = QSystemTrayIcon(_app_icon, app)
    tray.setToolTip(f"{PIPELA_APP_DISPLAY_NAME} (Qt)")
    menu = QMenu()
    menu.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

    def _tray_menu_bring_above() -> None:
        try:
            menu.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            menu.raise_()
            wh = menu.windowHandle()
            if wh is not None:
                wh.setFlag(Qt.WindowType.WindowStaysOnTopHint, True)
                wh.raise_()
        except Exception:
            pass

    menu.aboutToShow.connect(_tray_menu_bring_above)
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
    _splash_msg("메인 창 표시 준비…")

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
    finish_startup_splash(app, _splash, win)
    app.exec()
    _hud_done = getattr(pipela_mod, "_qt_cursor_hud", None)
    if _hud_done is not None:
        try:
            _hud_done.close()
        except Exception:
            pass
    title_bar_strip.close()
    overlay.close()
