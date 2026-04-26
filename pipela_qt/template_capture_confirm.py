"""템플릿 캡처 결과 확인 — Qt 다이얼로그."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from pipela_core.template_apply import (
    template_capture_output_path_for_kind,
    write_pil_rgb_to_png_cv2,
)
from pipela_qt import theme
from pipela_qt.panels.image_preview import pixmap_from_pil
from pipela_qt.ui_adaptive import qss_pad_all, qss_pad_vh, scale_px


def show_template_capture_confirm_qt(
    pipela_mod: Any,
    kind: str,
    pil_capture,
    on_applied: Callable[..., Any] | None = None,
) -> None:
    meta = pipela_mod._template_capture_kind_meta(kind)
    if meta is None:
        return
    _fname, _reg_key, label = meta

    accent = pipela_mod._SETTINGS_TEMPLATE_HIT_ACCENT_BY_KIND.get(
        kind, pipela_mod._SETTINGS_TEMPLATE_HIT_ACCENT_DEFAULT,
    )

    dlg = QDialog()
    dlg.setWindowTitle("캡처")
    dlg.setModal(True)
    dlg.setWindowFlags(dlg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
    dlg.setStyleSheet(
        f"QDialog {{ background-color: {theme.WINDOW_BG}; color: {theme.FG}; }}"
        f"QLabel {{ color: {theme.FG}; }}"
        f"QPushButton {{ padding: {qss_pad_vh(6, 14)}; border: none; }}"
    )

    root_lay = QVBoxLayout(dlg)
    title = QLabel(f"{label}\n드래그한 영역을 매칭 템플릿으로 지정합니다.")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet(f"color: {theme.FG}; font-size: {theme.spt(12)};")
    root_lay.addWidget(title)

    def _thumb_block(title_txt: str, pil_img, *, accent_border: bool) -> None:
        lt = QLabel(title_txt)
        lt.setStyleSheet(f"color: {theme.FG_MUTED}; font-weight: 600; font-size: {theme.spt(10)};")
        root_lay.addWidget(lt)
        pl = QLabel()
        pl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pm = pixmap_from_pil(pil_img, scale_px(400), scale_px(220))
        if pm is not None:
            pl.setPixmap(pm)
        else:
            pl.setText("없음")
        _bw = scale_px(2)
        if accent_border and pm is not None:
            pl.setStyleSheet(
                f"background: {theme.CARD_BG}; border: {_bw}px solid {accent}; padding: {qss_pad_all(4)};"
            )
        elif accent_border and pm is None:
            pl.setStyleSheet(
                f"color: {theme.FG_DIM}; padding: {qss_pad_vh(28, 48)}; background: {theme.CARD_BG}; "
                f"border: {_bw}px solid {accent};"
            )
        elif pm is None:
            pl.setStyleSheet(
                f"color: {theme.FG_DIM}; padding: {qss_pad_vh(28, 48)}; background: {theme.PANEL_BG};"
            )
        else:
            pl.setStyleSheet(f"background: {theme.PANEL_BG}; padding: {qss_pad_all(4)};")
        root_lay.addWidget(pl)

    _thumb_block("현재 템플릿", pipela_mod._template_capture_load_existing_pil(kind), accent_border=False)
    _thumb_block("캡처본", pil_capture, accent_border=True)

    btn_row = QHBoxLayout()
    ok_btn = QPushButton("확인")
    ok_btn.setStyleSheet(
        f"QPushButton {{ background: {pipela_mod.SETTINGS_ACCENT_BG}; color: {theme.FG}; "
        f"font-size: {theme.spt(10)}; padding: {qss_pad_vh(6, 14)}; border: 1px solid {theme.ACCENT}; "
        f"border-radius: {theme.RADIUS_SM}; }}"
        f"QPushButton:hover {{ background: {theme.BTN_HOVER}; border: 1px solid {theme.ACCENT}; }}"
        f"QPushButton:pressed {{ background: {theme.BTN_PRESSED}; }}"
    )
    cancel_btn = QPushButton("취소")
    cancel_btn.setStyleSheet(
        f"QPushButton {{ background: {pipela_mod.SETTINGS_BTN_BG}; color: {theme.FG}; "
        f"font-size: {theme.spt(10)}; padding: {qss_pad_vh(6, 14)}; border: 1px solid {theme.BORDER_HAIR}; "
        f"border-radius: {theme.RADIUS_SM}; }}"
        f"QPushButton:hover {{ background: {theme.BTN_HOVER}; border: 1px solid {theme.ACCENT}; }}"
        f"QPushButton:pressed {{ background: {theme.BTN_PRESSED}; }}"
    )
    btn_row.addStretch(1)
    btn_row.addWidget(ok_btn)
    btn_row.addWidget(cancel_btn)
    root_lay.addLayout(btn_row)

    def _do_ok() -> None:
        try:
            out_path = template_capture_output_path_for_kind(kind)
            if not out_path:
                print("[캡처] 저장 경로 실패", flush=True)
                return
            if not write_pil_rgb_to_png_cv2(pil_capture, out_path):
                print("[캡처] PNG 저장 실패", flush=True)
                return
            if pipela_mod._apply_template_capture_png(kind, out_path):
                print(f"[캡처] 저장·지정 OK → {out_path}", flush=True)
            dlg.accept()
            if on_applied is not None:
                on_applied()
        except Exception as e:
            print(f"[캡처] 확인 처리 FAIL: {e}", flush=True)

    ok_btn.clicked.connect(_do_ok)
    cancel_btn.clicked.connect(dlg.reject)

    dlg.exec()
