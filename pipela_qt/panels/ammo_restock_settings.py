"""Ammo Restock 설정 — 구매/인벤/은행 임계값·점수·토글 키."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFontMetrics, QKeyEvent
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
from pipela_qt.panels.template_last_match_thumb import (
    append_side_by_side_target_and_match_previews,
    append_template_target_image_caption,
    fit_template_thumb_label_to_pixmap,
    thumb_preview_max_wh,
    thumb_preview_slot_min_wh,
    update_last_match_thumbnail,
)
from pipela_qt.panels.thumbnail_preview_dialog import attach_template_thumbnail_click_preview
from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    add_template_similarity_row,
    configure_settings_scroll_area,
    make_settings_hline,
    settings_footnote_style,
    settings_label_align_center_h,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.settings_sequence_autoscroll import FEAT_AMMO_RESTOCK, apply_sequence_autoscroll
from pipela_qt.template_path_connector_arrow import TemplatePathConnectorArrow
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v
from pipela_qt.qt_capture import attach_template_toolbar
from pipela_qt.resizable_text_widgets import ResizableLineEdit
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox
from pipela_qt.template_section_probe_frame import (
    TemplateLiveScoreReadout,
    TemplateProbeSectionFrame,
)
from pipela_qt.typography_refresh_support import TypographyStyleBundle

_THR_MIN = 0.1
_THR_MAX = 1.0


def _h_advance(fm: QFontMetrics, s: str) -> int:
    return int(fm.horizontalAdvance(s))


_AMMO_SCORE_THR_BY_KIND: dict[str, tuple[str, str]] = {
    k: (sg, tg) for k, sg, tg in AMMO_SCORE_ROW_BINDINGS
}


class AmmoRestockSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._capturing = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._rows: dict[str, tuple[TemplateLiveScoreReadout, DragDoubleSpinBox]] = {}
        self._typo = TypographyStyleBundle()
        # 템플릿 경로·BGR 캐시 — 틱마다 imread/레지 풀기 방지
        self._ammo_thumb_state: dict[str, dict[str, object]] = {}
        self._ammo_last_hit: dict[str, QLabel] = {}
        self._ammo_probe_frames: list[TemplateProbeSectionFrame] = []
        self._ammo_path_arrows: list[TemplatePathConnectorArrow] = []
        self._ammo_kinds_order: list[str] = []

        outer = QVBoxLayout(self)
        self._outer = outer
        outer.setSpacing(settings_root_vertical_spacing())
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        self._scroll = scroll
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        inner.setContentsMargins(0, 0, 0, 0)
        lay = QVBoxLayout(inner)
        lay.setSpacing(settings_root_vertical_spacing())
        self._inner_lay = lay

        for i, sec in enumerate(pipela_mod._AMMO_SETTINGS_SECTIONS):
            title, kind, *_rest = sec
            if i > 0:
                arr = TemplatePathConnectorArrow()
                self._typo.add(arr.refresh_for_scale)
                self._ammo_path_arrows.append(arr)
                lay.addWidget(arr)
            self._ammo_kinds_order.append(kind)
            cap_kind = AMMO_UI_KIND_TO_TEMPLATE_CAPTURE_KIND[kind]
            fr = TemplateProbeSectionFrame(pipela_mod, cap_kind, inner)
            self._ammo_probe_frames.append(fr)
            block = fr.content_layout()
            st = QLabel(title)
            st.setStyleSheet(settings_section_heading_style())
            self._typo.add(lambda w=st: w.setStyleSheet(settings_section_heading_style()))
            settings_label_align_center_h(st)
            block.addWidget(st)
            path_attr = AMMO_PATH_GLOBAL_BY_KIND[kind]
            reg_key = AMMO_REGISTRY_DATA_KEY_BY_KIND[kind]
            _tmw, _tmh = thumb_preview_slot_min_wh()
            th = QLabel()
            th.setMinimumSize(_tmw, _tmh)
            th.setAlignment(Qt.AlignmentFlag.AlignCenter)
            th.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px_v(4)}px;")
            th.setObjectName(f"_ammo_thumb_{kind}")
            attach_template_thumbnail_click_preview(
                th,
                lambda a=path_attr: str(getattr(self._m, a, "") or ""),
            )
            if cap_kind:
                self._ammo_last_hit[kind] = append_side_by_side_target_and_match_previews(
                    block,
                    self._typo,
                    th,
                    pipela_mod=pipela_mod,
                    hit_kind=cap_kind,
                )
            else:
                append_template_target_image_caption(block, self._typo)
                block.addWidget(th, 0, Qt.AlignmentFlag.AlignHCenter)
            cur = TemplateLiveScoreReadout(
                pipela_mod,
                cap_kind,
            )
            self._typo.add(cur.refresh_metric_font)
            sp = DragDoubleSpinBox()
            sp.setRange(_THR_MIN, _THR_MAX)
            sp.setDecimals(2)
            sp.setSingleStep(0.01)
            sp.setMaximumWidth(scale_px_h(88))
            thr_g = AMMO_THR_GLOBAL_BY_KIND[kind]

            def _mk_commit(ga: str):
                def _go(v: float) -> None:
                    setattr(self._m, ga, float(v))
                    sync_registry_snapshot_from_module(self._m)
                    self._m.schedule_save_config()

                return _go

            sp.valueChanged.connect(_mk_commit(thr_g))
            add_template_similarity_row(
                block,
                cur,
                sp,
                pipela_mod=pipela_mod,
                probe_capture_kind=cap_kind,
                typography_bundle=self._typo,
            )
            attach_template_toolbar(
                block,
                pipela_mod,
                cap_kind,
                self._tick,
                typography_bundle=self._typo,
            )
            self._rows[kind] = (cur, sp)
            setattr(self, f"_thumb_w_{kind}", th)
            lay.addWidget(fr)

        lay.addWidget(make_settings_hline())
        hk_t = QLabel("지정할 키")
        hk_t.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=hk_t: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(hk_t)
        lay.addWidget(hk_t)
        self._key_disp = ResizableLineEdit()
        self._key_disp.setReadOnly(True)
        self._key_disp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cap_btn = QPushButton("키 입력")
        self._cap_btn.clicked.connect(self._toggle_capture)
        add_settings_field_row(lay, "키", self._key_disp, self._cap_btn)
        self._key_hint = QLabel(
            "한 키로 Ammo Restock 감지를 켜고 끕니다. "
            "「키 입력」 후 원하는 키를 한 번 누르면 바인딩됩니다. 키 입력 중 Esc는 취소.",
        )
        self._key_hint.setWordWrap(True)
        self._key_hint.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=self._key_hint: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(self._key_hint)
        lay.addWidget(self._key_hint)
        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        self._ammo_seq_targets: list[QWidget] = [*self._ammo_probe_frames, hk_t]

    def apply_scaled_typography(self) -> None:
        self._outer.setSpacing(settings_root_vertical_spacing())
        self._inner_lay.setSpacing(settings_root_vertical_spacing())
        for _pf in self._ammo_probe_frames:
            _pf.apply_scale_margins()
        for kind, (_cur, sp) in self._rows.items():
            sp.setMaximumWidth(scale_px_h(88))
        self._typo.apply()
        self._fit_key_disp_width()
        self._tick()

    def _reload(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        kc = snapshot_int(snap, "ammo_restock_toggle_key_code", int(m.ammo_restock_toggle_key_code))
        self._key_disp.setText(m.vk_to_display_name(int(kc) & 0xFF))
        self._fit_key_disp_width()
        for kind, (_cur, sp) in self._rows.items():
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
        for arr in self._ammo_path_arrows:
            arr.reset_edge_state()
        self._reload()
        self._timer.start(max(16, int(display_tick_ms())))

    def hideEvent(self, e) -> None:
        self._timer.stop()
        for arr in self._ammo_path_arrows:
            arr.hide_idle()
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
                self._fit_key_disp_width()
        for kind, score_g, thr_g in AMMO_SCORE_ROW_BINDINGS:
            cur_l, sp = self._rows[kind]
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
                _tw, _thm = thumb_preview_max_wh()
                _sig = (id(bgr), int(_tw), int(_thm))
                if getattr(th, "_pipela_last_thumb_sig", None) != _sig:
                    th._pipela_last_thumb_sig = _sig
                    pm = pixmap_from_bgr(bgr, _tw, _thm)
                    if pm:
                        th._pipela_thumb_empty = False
                        fit_template_thumb_label_to_pixmap(th, pm, empty_text="없음")
                    else:
                        th._pipela_last_thumb_sig = None
                        th._pipela_thumb_empty = True
                        fit_template_thumb_label_to_pixmap(th, None, empty_text="없음")
            else:
                _had_bgr = getattr(th, "_pipela_last_thumb_sig", None) is not None
                _empty = getattr(th, "_pipela_thumb_empty", None) is True
                if _had_bgr or not _empty:
                    th._pipela_last_thumb_sig = None
                    th._pipela_thumb_empty = True
                    fit_template_thumb_label_to_pixmap(th, None, empty_text="없음")
            lh = self._ammo_last_hit.get(kind)
            ck = AMMO_UI_KIND_TO_TEMPLATE_CAPTURE_KIND.get(kind)
            if lh is not None and ck:
                _acap, _ath = lh
                update_last_match_thumbnail(
                    _ath,
                    m,
                    ck,
                    match_caption_lbl=_acap,
                    orig_thumb=th,
                )
        for j, arr in enumerate(self._ammo_path_arrows):
            kind = self._ammo_kinds_order[j]
            sg, tg = _AMMO_SCORE_THR_BY_KIND[kind]
            sc = float(getattr(m, sg))
            thr = snapshot_float(snap, tg, float(getattr(m, tg)))
            arr.feed_threshold_edge(sc, thr)
        apply_sequence_autoscroll(
            panel=self,
            scroll=self._scroll,
            pipela_mod=m,
            feature=FEAT_AMMO_RESTOCK,
            targets=self._ammo_seq_targets,
            active_check=lambda mod: bool(getattr(mod, "ammo_restock_active", False)),
        )

    def _fit_key_disp_width(self) -> None:
        fm = self._key_disp.fontMetrics()
        t = self._key_disp.text() or "—"
        ref = _h_advance(fm, t)
        pad = scale_px_v(14)
        lo = scale_px_v(30)
        hi = scale_px_v(220)
        self._key_disp.setFixedWidth(max(lo, min(hi, ref + pad)))

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
            self._fit_key_disp_width()
            self._end_capture(cancel=False)
            event.accept()
            return
        super().keyPressEvent(event)
