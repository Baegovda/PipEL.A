"""앱 대표 QIcon — 창 왼쪽 위·작업 표시줄·시스템 트레이."""

from __future__ import annotations

import os

from PyQt6.QtGui import QIcon

from pipela_core.paths import PIPELA_APP_ICON_PATH, PIPELA_ICO_PATH


def qt_application_icon() -> QIcon:
    """`icon/vaultboy.png` 우선, 없거나 로드 실패 시 `Pipela.ico`."""
    for path in (PIPELA_APP_ICON_PATH, PIPELA_ICO_PATH):
        if path and os.path.isfile(path):
            ic = QIcon(path)
            if not ic.isNull():
                return ic
    return QIcon()
