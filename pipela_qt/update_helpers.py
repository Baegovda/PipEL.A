"""업데이트 자동 설치·공통 대화상자 (메인 스레드에서만 Qt UI)."""

from __future__ import annotations

import os
import tempfile
import threading
import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget

from pipela_core.version_info import PIPELA_APP_DISPLAY_NAME
from pipela_qt.card_popup_shell import (
    confirm_card_dialog,
    message_card_dialog,
    tri_choice_card_dialog,
)


def qt_message(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    tone: str = "info",
) -> None:
    message_card_dialog(parent, title, text, tone=tone)


def qt_ask_yes_no(parent: QWidget | None, title: str, text: str) -> bool:
    return confirm_card_dialog(
        parent,
        title=title,
        message=text,
        confirm_text="예",
        cancel_text="아니오",
        message_tone="muted",
        default_confirm=True,
    )


def qt_ask_yes_no_cancel(parent: QWidget | None, title: str, text: str) -> bool | None:
    return tri_choice_card_dialog(
        parent,
        title=title,
        message=text,
        yes_text="예",
        no_text="아니오",
        cancel_text="취소",
        message_tone="muted",
        default_which="yes",
    )


class _ErrSignal(QObject):
    """다운로드 완료(err: None 이면 성공)."""

    finished = pyqtSignal(object)


def qt_begin_auto_install(m, parent: QWidget | None, download_url: str, new_ver: str) -> None:
    if not m._pipela_is_frozen_exe():
        qt_message(
            parent,
            "업데이트",
            f"자동 설치는 PyInstaller로 만든 {PIPELA_APP_DISPLAY_NAME}.exe 로 실행할 때만 사용할 수 있습니다.",
        )
        return
    dest = m._pipela_current_exe_path()
    if not dest or not os.path.isfile(dest):
        qt_message(
            parent,
            "업데이트",
            "실행 파일 경로를 확인할 수 없습니다.",
            tone="danger",
        )
        return
    stage = os.path.join(
        tempfile.gettempdir(),
        f"Pipela_update_{os.getpid()}_{int(time.time())}.exe",
    )
    bridge = _ErrSignal(parent)
    _once = {"v": False}

    def _done(err):
        if _once["v"]:
            return
        _once["v"] = True
        if err:
            qt_message(parent, "다운로드 실패", str(err), tone="danger")
            try:
                if os.path.isfile(stage):
                    os.unlink(stage)
            except OSError:
                pass
            return
        try:
            m.schedule_save_config()
        except Exception:
            pass
        try:
            m._pipela_launch_exe_replace_and_restart(stage, dest, os.getpid())
        except Exception as ex:
            qt_message(parent, "업데이트", str(ex), tone="danger")
            try:
                if os.path.isfile(stage):
                    os.unlink(stage)
            except OSError:
                pass
            return
        try:
            app = QApplication.instance()
            if app is not None:
                app.quit()
        except Exception:
            pass
        try:
            m.shutdown_after_ui_mainloop()
        except Exception:
            pass
        QTimer.singleShot(400, lambda: os._exit(0))

    bridge.finished.connect(_done)

    def _work():
        err = m._pipela_download_update_file(download_url, stage)
        bridge.finished.emit(err)

    threading.Thread(target=_work, daemon=True).start()
