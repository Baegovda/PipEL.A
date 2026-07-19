"""업데이트 패널 — 버전 표시·업데이트·버전 확인."""

from __future__ import annotations

import threading

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    settings_emphasis_line_style,
    settings_label_align_center_h,
    settings_root_vertical_spacing,
)
from pipela_qt.typography_refresh_support import TypographyStyleBundle
from pipela_qt.update_helpers import (
    qt_ask_yes_no,
    qt_message,
    qt_open_update_download,
)


class UpdateSettingsPanel(QWidget):
    _manifest_done = pyqtSignal(object, object)
    _reinstall_done = pyqtSignal(object, object)

    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._manifest_fetch_busy = False
        self._typo = TypographyStyleBundle()
        self._manifest_done.connect(self._on_manifest)
        self._reinstall_done.connect(self._on_reinstall_url)
        lay = QVBoxLayout(self)
        self._root_lay = lay
        lay.setSpacing(settings_root_vertical_spacing())
        lay.setContentsMargins(0, 0, 0, 0)
        self._ver_lbl = QLabel(f"현재 버전: {pipela_mod.PIPELA_APP_VERSION}")
        self._ver_lbl.setWordWrap(True)
        self._ver_lbl.setStyleSheet(settings_emphasis_line_style())
        self._typo.add(lambda w=self._ver_lbl: w.setStyleSheet(settings_emphasis_line_style()))
        settings_label_align_center_h(self._ver_lbl)
        lay.addWidget(self._ver_lbl)
        b_check = QPushButton("버전 확인")
        b_check.clicked.connect(self._request_manifest)
        b_re = QPushButton("업데이트")
        _bf = QFont(b_re.font())
        _bf.setWeight(QFont.Weight.Bold)
        b_re.setFont(_bf)
        b_re.clicked.connect(self._click_reinstall)
        add_settings_field_row(lay, "다운로드·확인", b_check, b_re)
        lay.addStretch(1)

    def apply_scaled_typography(self) -> None:
        self._root_lay.setSpacing(settings_root_vertical_spacing())
        self._typo.apply()

    def run_version_check(self) -> None:
        """제어창이 설정 탭 + 업데이트 패널로 전환될 때 자동 호출 — `버전 확인` 과 동일."""
        self._request_manifest()

    def _request_manifest(self) -> None:
        if self._manifest_fetch_busy:
            return
        self._manifest_fetch_busy = True
        m = self._m

        def _work() -> None:
            d = None
            e = None
            try:
                d, e = m._pipela_fetch_update_manifest()
            except Exception as ex:
                d, e = None, str(ex)
            self._manifest_done.emit(d, e)

        threading.Thread(target=_work, daemon=True).start()

    def _click_reinstall(self) -> None:
        def _work():
            u, e = self._m._pipela_resolve_reinstall_download_url()
            self._reinstall_done.emit(u, e)

        threading.Thread(target=_work, daemon=True).start()

    def _on_reinstall_url(self, url, err) -> None:
        m = self._m
        if err:
            qt_message(self, "업데이트", str(err), tone="danger")
            return
        if not url:
            qt_message(self, "업데이트", "다운로드 URL을 확인할 수 없습니다.", tone="danger")
            return
        if not qt_ask_yes_no(
            self,
            "업데이트",
            f"같은 버전 표시({m.PIPELA_APP_VERSION})의 배포 zip을 브라우저에서 받습니다.\n\n"
            "압축을 푼 뒤 `Pipela\\Pipela.exe` 로 실행하세요.\n\n계속할까요?",
        ):
            return
        qt_open_update_download(self, url)

    def _on_manifest(self, data, err) -> None:
        self._manifest_fetch_busy = False
        m = self._m
        if err == "no_manifest_url":
            qt_message(
                self,
                "업데이트",
                "업데이트 주소(manifest URL)가 비어 있습니다.\n\n"
                "환경 변수 PIPELA_UPDATE_MANIFEST_URL 에 HTTPS JSON 주소를 넣거나,\n"
                "pipela_core/version_info.py 의 PIPELA_UPDATE_MANIFEST_URL 기본값을 수정하세요.",
            )
            return
        if err:
            qt_message(self, "업데이트 확인 실패", str(err), tone="danger")
            return
        rv = (data.get("version") or "").strip()
        if not rv:
            qt_message(self, "업데이트", "manifest에 version 필드가 없습니다.", tone="warn")
            return
        if m._pipela_version_tuple(rv) <= m._pipela_version_tuple(m.PIPELA_APP_VERSION):
            qt_message(
                self,
                "업데이트",
                f"이미 최신 버전입니다.\n\n현재: {m.PIPELA_APP_VERSION}\n배포: {rv}",
            )
            return
        notes = (data.get("notes") or "").strip()
        dl = m._pipela_update_manifest_download_url(data)
        browser_url = m._pipela_update_manifest_browser_url(data) or dl
        msg = f"새 버전이 있습니다.\n\n현재: {m.PIPELA_APP_VERSION}\n배포: {rv}"
        if notes:
            msg += f"\n\n{notes}"
        if dl or browser_url:
            if qt_ask_yes_no(
                self,
                "업데이트",
                msg
                + "\n\n브라우저에서 배포 zip(또는 릴리스 페이지)을 열까요?\n"
                "압축을 푼 뒤 `Pipela\\Pipela.exe` 로 실행하세요.",
            ):
                qt_open_update_download(self, dl or browser_url, browser_url=browser_url)
        else:
            qt_message(
                self,
                "업데이트",
                msg + "\n\nmanifest에 download_url(또는 url)이 없습니다.",
            )
