"""Ammo Restock 설정 — 구매/인벤/은행 임계값·점수·토글 키."""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from pipela_core.ammo_restock_catalog import (
    AMMO_PATH_GLOBAL_BY_KIND,
    AMMO_REGISTRY_DATA_KEY_BY_KIND,
    AMMO_SCORE_ROW_BINDINGS,
    AMMO_THR_GLOBAL_BY_KIND,
)
from pipela_core.display_timing import display_tick_ms
from pipela_core.image_registry import load_image_data_if_path_changed
from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_float, snapshot_int
from pipela_core.template_capture_catalog import AMMO_UI_KIND_TO_TEMPLATE_CAPTURE_KIND
from pipela_qt import theme as T
from pipela_qt.panels.image_preview import pixmap_from_bgr
from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    add_template_similarity_row,
    configure_settings_scroll_area,
    make_settings_hline,
    settings_caption_style,
    settings_footnote_style,
    settings_label_align_center_h,
    settings_page_title_style,
    settings_path_connector_style,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.ui_adaptive import scale_px
from pipela_qt.qt_capture import attach_template_toolbar
from pipela_qt.resizable_text_widgets import ResizableLineEdit
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox
from pipela_qt.template_section_probe_frame import TemplateLiveScoreReadout
from pipela_qt.typography_refresh_support import TypographyStyleBundle

_THR_MIN = 0.1
_THR_MAX = 1.0


class AmmoRestockSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._capturing = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._rows: dict[str, tuple[TemplateLiveScoreReadout, DragDoubleSpinBox, QLabel]] = {}
        self._typo = TypographyStyleBundle()
        # 템플릿 경로·BGR 캐시 — 틱마다 imread/레지 풀기 방지
        self._ammo_thumb_state: dict[str, dict[str, object]] = {}

        outer = QVBoxLayout(self)
        self._outer = outer
        outer.setSpacing(settings_root_vertical_spacing())
        outer.setContentsMargins(0, 0, 0, 0)
        t1 = QLabel("Ammo Restock 설정")
        t1.setStyleSheet(settings_page_title_style())
        self._typo.add(lambda w=t1: w.setStyleSheet(settings_page_title_style()))
        settings_label_align_center_h(t1)
        outer.addWidget(t1)
        outer.addWidget(make_settings_hline())

        scroll = QScrollArea()
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        inner.setContentsMargins(0, 0, 0, 0)
        lay = QVBoxLayout(inner)
        lay.setSpacing(settings_root_vertical_spacing())
        self._inner_lay = lay

        for i, sec in enumerate(pipela_mod._AMMO_SETTINGS_SECTIONS):
            title, kind, *_rest = sec
            if i > 0:
                arr = QLabel("↓")
                arr.setStyleSheet(settings_path_connector_style())
                self._typo.add(lambda w=arr: w.setStyleSheet(settings_path_connector_style()))
                settings_label_align_center_h(arr)
                lay.addWidget(arr)
            st = QLabel(title)
            st.setStyleSheet(settings_section_heading_style())
            self._typo.add(lambda w=st: w.setStyleSheet(settings_section_heading_style()))
            settings_label_align_center_h(st)
            lay.addWidget(st)
            path_attr = AMMO_PATH_GLOBAL_BY_KIND[kind]
            reg_key = AMMO_REGISTRY_DATA_KEY_BY_KIND[kind]
            path = getattr(pipela_mod, path_attr)
            pl = QLabel(f"템플릿: {os.path.basename(path) if path else '—'}")
            pl.setWordWrap(True)
            pl.setStyleSheet(settings_footnote_style())
            self._typo.add(lambda w=pl: w.setStyleSheet(settings_footnote_style()))
            settings_label_align_center_h(pl)
            pl.setObjectName(f"_ammo_path_{kind}")
            lay.addWidget(pl)
            th = QLabel()
            th.setMinimumSize(scale_px(120), scale_px(72))
            th.setAlignment(Qt.AlignmentFlag.AlignCenter)
            th.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;")
            th.setObjectName(f"_ammo_thumb_{kind}")
            lay.addWidget(th)
            cap_kind = AMMO_UI_KIND_TO_TEMPLATE_CAPTURE_KIND.get(kind)
            if cap_kind:
                attach_template_toolbar(lay, pipela_mod, cap_kind, self._tick)
            cur = TemplateLiveScoreReadout(
                pipela_mod,
                AMMO_UI_KIND_TO_TEMPLATE_CAPTURE_KIND[kind],
            )
            self._typo.add(lambda w=cur: w.setStyleSheet(f"font-family: {T.FONT_CSS_UI};"))
            sp = DragDoubleSpinBox()
            sp.setRange(_THR_MIN, _THR_MAX)
            sp.setDecimals(2)
            sp.setSingleStep(0.01)
            sp.setMaximumWidth(scale_px(88))
            thr_g = AMMO_THR_GLOBAL_BY_KIND[kind]

            def _mk_commit(ga: str):
                def _go(v: float) -> None:
                    setattr(self._m, ga, float(v))
                    sync_registry_snapshot_from_module(self._m)
                    self._m.schedule_save_config()

                return _go

            sp.valueChanged.connect(_mk_commit(thr_g))
            add_template_similarity_row(lay, cur, sp)
            self._rows[kind] = (cur, sp, pl)
            setattr(self, f"_thumb_w_{kind}", th)

        lay.addWidget(make_settings_hline())
        hk_t = QLabel("토글 단축키")
        hk_t.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=hk_t: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(hk_t)
        lay.addWidget(hk_t)
        hk_d = QLabel("한 키로 Ammo Restock 감지를 켜고 끕니다.")
        hk_d.setWordWrap(True)
        hk_d.setStyleSheet(settings_caption_style())
        self._typo.add(lambda w=hk_d: w.setStyleSheet(settings_caption_style()))
        settings_label_align_center_h(hk_d)
        lay.addWidget(hk_d)
        self._key_disp = ResizableLineEdit()
        self._key_disp.setReadOnly(True)
        self._key_disp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._key_disp.setMaximumWidth(scale_px(120))
        self._cap_btn = QPushButton("키 입력")
        self._cap_btn.clicked.connect(self._toggle_capture)
        add_settings_field_row(lay, "단축키", self._key_disp, self._cap_btn)
        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

    def apply_scaled_typography(self) -> None:
        self._outer.setSpacing(settings_root_vertical_spacing())
        self._inner_lay.setSpacing(settings_root_vertical_spacing())
        self._key_disp.setMaximumWidth(scale_px(120))
        for kind, (_cur, sp, _pl) in self._rows.items():
            sp.setMaximumWidth(scale_px(88))
            getattr(self, f"_thumb_w_{kind}").setMinimumSize(scale_px(120), scale_px(72))
        self._typo.apply()
        self._tick()

    def _reload(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        kc = snapshot_int(snap, "ammo_restock_toggle_key_code", int(m.ammo_restock_toggle_key_code))
        self._key_disp.setText(m.vk_to_display_name(int(kc) & 0xFF))
        for kind, (_cur, sp, _pl) in self._rows.items():
            thr_g = AMMO_THR_GLOBAL_BY_KIND[kind]
            sp.blockSignals(True)
            sp.setValue(
                max(
                    _THR_MIN,
                    min(
                        _THR_MAX,
                        snapshot_float(snap, thr_g, float(getattr(m, thr_g))),
                    ),
                )
            )
            sp.blockSignals(False)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self._reload()
        self._timer.start(max(16, int(display_tick_ms())))

    def hideEvent(self, e) -> None:
        self._timer.stop()
        if self._capturing:
            self._end_capture(cancel=True)
        super().hideEvent(e)

    def _tick(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        if not self._capturing:
            kc = snapshot_int(snap, "ammo_restock_toggle_key_code", int(m.ammo_restock_toggle_key_code))
            _kdisp = m.vk_to_display_name(int(kc) & 0xFF)
            if getattr(self._key_disp, "_pipela_last_txt", object()) != _kdisp:
                self._key_disp._pipela_last_txt = _kdisp
                self._key_disp.setText(_kdisp)
        for kind, score_g, thr_g in AMMO_SCORE_ROW_BINDINGS:
            cur_l, sp, path_l = self._rows[kind]
            cur_l.setText(f"{float(getattr(m, score_g)):.2f}")
            if not sp.hasFocus():
                sp.blockSignals(True)
                sp.setValue(
                    max(
                        _THR_MIN,
                        min(
                            _THR_MAX,
                            snapshot_float(snap, thr_g, float(getattr(m, thr_g))),
                        ),
                    )
                )
                sp.blockSignals(False)
            path_attr = AMMO_PATH_GLOBAL_BY_KIND[kind]
            reg_key = AMMO_REGISTRY_DATA_KEY_BY_KIND[kind]
            path = getattr(m, path_attr)
            _path_cap = f"템플릿: {os.path.basename(path) if path else '—'}"
            if getattr(path_l, "_pipela_last_txt", None) != _path_cap:
                path_l._pipela_last_txt = _path_cap
                path_l.setText(_path_cap)
            th = getattr(self, f"_thumb_w_{kind}")
            st = self._ammo_thumb_state.get(kind)
            if st is None:
                st = {"last_path": None, "bgr": None}
                self._ammo_thumb_state[kind] = st
            bgr, _lp = load_image_data_if_path_changed(
                path or "",
                reg_key,
                st["last_path"],
                st["bgr"],
            )
            st["last_path"] = _lp
            st["bgr"] = bgr
            if bgr is not None:
                _tw, _thm = scale_px(200), scale_px(120)
                _sig = (id(bgr), int(_tw), int(_thm))
                if getattr(th, "_pipela_last_thumb_sig", None) == _sig:
                    continue
                th._pipela_last_thumb_sig = _sig
                pm = pixmap_from_bgr(bgr, _tw, _thm)
                if pm:
                    th._pipela_thumb_empty = False
                    th.setText("")
                    th.setPixmap(pm)
                    th.setStyleSheet(
                        f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;",
                    )
                else:
                    th._pipela_last_thumb_sig = None
                    th._pipela_thumb_empty = True
                    th.clear()
                    th.setText("없음")
                    th.setStyleSheet(
                        f"background: {T.PANEL_BG}; color: {T.FG_DIM}; border-radius: {scale_px(4)}px;",
                    )
            else:
                _had_bgr = getattr(th, "_pipela_last_thumb_sig", None) is not None
                _empty = getattr(th, "_pipela_thumb_empty", None) is True
                if _had_bgr or not _empty:
                    th._pipela_last_thumb_sig = None
                    th._pipela_thumb_empty = True
                    th.clear()
                    th.setText("없음")
                    th.setStyleSheet(
                        f"background: {T.PANEL_BG}; color: {T.FG_DIM}; border-radius: {scale_px(4)}px;",
                    )

    def _toggle_capture(self) -> None:
        if self._capturing:
            self._end_capture(cancel=True)
            return
        self._capturing = True
        self._cap_btn.setText("키를 누르세요…")
        self.setFocus(Qt.FocusReason.OtherFocusReason)
        self.grabKeyboard()

    def _end_capture(self, *, cancel: bool) -> None:
        if not self._capturing:
            return
        self._capturing = False
        self.releaseKeyboard()
        self._cap_btn.setText("키 입력")
        if not cancel:
            self._m.schedule_save_config()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self._capturing:
            if event.key() == Qt.Key.Key_Escape:
                self._end_capture(cancel=True)
                event.accept()
                return
            vk = int(event.nativeVirtualKey()) & 0xFF
            if vk == 0:
                event.ignore()
                return
            self._m.ammo_restock_toggle_key_code = vk
            sync_registry_snapshot_from_module(self._m)
            self._key_disp.setText(self._m.vk_to_display_name(vk))
            self._end_capture(cancel=False)
            event.accept()
            return
        super().keyPressEvent(event)
