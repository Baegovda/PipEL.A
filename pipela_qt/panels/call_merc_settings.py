"""Call Merc 설정 — 4단계 템플릿 임계값·실시간 점수."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from pipela_core.call_merc_catalog import (
    CALL_MERC_PATH_KEY,
    CALL_MERC_REG_DATA_KEY,
    CALL_MERC_SCORE_KEY,
    CALL_MERC_THR_KEY,
)
from pipela_core.display_timing import display_tick_ms
from pipela_core.image_registry import load_image_data_if_path_changed
from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_float
from pipela_qt import theme as T
from pipela_qt.panels.image_preview import pixmap_from_bgr
from pipela_qt.panels.template_last_match_thumb import (
    append_side_by_side_target_and_match_previews,
    fit_template_thumb_label_to_pixmap,
    thumb_preview_max_wh,
    thumb_preview_slot_min_wh,
    update_last_match_thumbnail,
)
from pipela_qt.panels.thumbnail_preview_dialog import attach_template_thumbnail_click_preview
from pipela_qt.panels.settings_chrome import (
    add_template_similarity_row,
    configure_settings_scroll_area,
    make_settings_hline,
    settings_label_align_center_h,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.settings_sequence_autoscroll import FEAT_CALL_MERC, apply_sequence_autoscroll
from pipela_qt.template_path_connector_arrow import TemplatePathConnectorArrow
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v
from pipela_qt.qt_capture import attach_template_toolbar
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox
from pipela_qt.template_section_probe_frame import (
    TemplateLiveScoreReadout,
    TemplateProbeSectionFrame,
)
from pipela_qt.typography_refresh_support import TypographyStyleBundle

_THR_MIN = 0.1
_THR_MAX = 1.0


class CallMercSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._rows: dict[str, tuple[TemplateLiveScoreReadout, DragDoubleSpinBox, QLabel]] = {}
        self._merc_last_hit: dict[str, QLabel] = {}
        self._typo = TypographyStyleBundle()
        self._merc_thumb_state: dict[str, dict[str, object]] = {}

        outer = QVBoxLayout(self)
        self._outer = outer
        outer.setSpacing(settings_root_vertical_spacing())
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        self._scroll = scroll
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        inner.setContentsMargins(0, 0, 0, 0)
        self._inner = inner
        self._merc_section_frames: list[TemplateProbeSectionFrame] = []
        self._merc_path_arrows: list[TemplatePathConnectorArrow] = []
        self._merc_section_kinds: list[str] = []
        lay = QVBoxLayout(inner)
        lay.setSpacing(settings_root_vertical_spacing())
        self._inner_lay = lay

        for i, sec in enumerate(pipela_mod._CALL_MERC_SETTINGS_SECTIONS):
            title, kind, *_r = sec
            if i > 0:
                arr = TemplatePathConnectorArrow()
                self._typo.add(arr.refresh_for_scale)
                self._merc_path_arrows.append(arr)
                lay.addWidget(arr)
            fr = TemplateProbeSectionFrame(self._m, kind, inner)
            self._merc_section_kinds.append(kind)
            self._merc_section_frames.append(fr)
            block = fr.content_layout()
            st = QLabel(title)
            st.setStyleSheet(settings_section_heading_style())
            self._typo.add(lambda w=st: w.setStyleSheet(settings_section_heading_style()))
            settings_label_align_center_h(st)
            block.addWidget(st)
            path_key = CALL_MERC_PATH_KEY[kind]
            reg_key = CALL_MERC_REG_DATA_KEY[kind]
            _tmw, _tmh = thumb_preview_slot_min_wh()
            th = QLabel()
            th.setMinimumSize(_tmw, _tmh)
            th.setAlignment(Qt.AlignmentFlag.AlignCenter)
            th.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px_v(4)}px;")
            attach_template_thumbnail_click_preview(
                th,
                lambda k=path_key: str(getattr(self._m, k, "") or ""),
            )
            self._merc_last_hit[kind] = append_side_by_side_target_and_match_previews(
                block,
                self._typo,
                th,
                pipela_mod=pipela_mod,
                hit_kind=kind,
            )
            cur = TemplateLiveScoreReadout(self._m, kind)
            self._typo.add(cur.refresh_metric_font)
            sp = DragDoubleSpinBox()
            sp.setRange(_THR_MIN, _THR_MAX)
            sp.setDecimals(2)
            sp.setSingleStep(0.01)
            sp.setMaximumWidth(scale_px_h(88))
            thr_attr = CALL_MERC_THR_KEY[kind]

            def _mk_commit(attr: str):
                def _go(v: float) -> None:
                    setattr(self._m, attr, float(v))
                    sync_registry_snapshot_from_module(self._m)
                    self._m.schedule_save_config()

                return _go

            sp.valueChanged.connect(_mk_commit(thr_attr))
            add_template_similarity_row(
                block,
                cur,
                sp,
                pipela_mod=self._m,
                probe_capture_kind=kind,
                typography_bundle=self._typo,
            )
            attach_template_toolbar(
                block,
                pipela_mod,
                kind,
                self._tick,
                typography_bundle=self._typo,
            )
            self._rows[kind] = (cur, sp, th)
            lay.addWidget(fr)
        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

    def apply_scaled_typography(self) -> None:
        self._outer.setSpacing(settings_root_vertical_spacing())
        self._inner_lay.setSpacing(settings_root_vertical_spacing())
        for fr in self._merc_section_frames:
            fr.apply_scale_margins()
        for k, (_c, sp, _th) in self._rows.items():
            sp.setMaximumWidth(scale_px_h(88))
        self._typo.apply()
        self._tick()

    def _reload(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        for kind, (_c, sp, _t) in self._rows.items():
            thr_attr = CALL_MERC_THR_KEY[kind]
            sp.blockSignals(True)
            sp.setValue(
                max(
                    _THR_MIN,
                    min(
                        _THR_MAX,
                        snapshot_float(snap, thr_attr, float(getattr(m, thr_attr))),
                    ),
                )
            )
            sp.blockSignals(False)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        for arr in self._merc_path_arrows:
            arr.reset_edge_state()
        self._reload()
        self._timer.start(max(16, int(display_tick_ms())))

    def hideEvent(self, e) -> None:
        self._timer.stop()
        for arr in self._merc_path_arrows:
            arr.hide_idle()
        super().hideEvent(e)

    def _tick(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        for kind, (cur_l, sp, th) in self._rows.items():
            score_attr = CALL_MERC_SCORE_KEY[kind]
            thr_attr = CALL_MERC_THR_KEY[kind]
            path_key = CALL_MERC_PATH_KEY[kind]
            reg_key = CALL_MERC_REG_DATA_KEY[kind]
            cur_l.setText(f"{float(getattr(m, score_attr)):.2f}")
            if not sp.hasFocus():
                sp.blockSignals(True)
                sp.setValue(
                    max(
                        _THR_MIN,
                        min(
                            _THR_MAX,
                            snapshot_float(snap, thr_attr, float(getattr(m, thr_attr))),
                        ),
                    )
                )
                sp.blockSignals(False)
            path = getattr(m, path_key)
            st = self._merc_thumb_state.get(kind)
            if st is None:
                st = {"last_path": None, "bgr": None}
                self._merc_thumb_state[kind] = st
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
                _had = getattr(th, "_pipela_last_thumb_sig", None) is not None
                _empty = getattr(th, "_pipela_thumb_empty", None) is True
                if _had or not _empty:
                    th._pipela_last_thumb_sig = None
                    th._pipela_thumb_empty = True
                    fit_template_thumb_label_to_pixmap(th, None, empty_text="없음")
            _mcap, _mthumb = self._merc_last_hit[kind]
            update_last_match_thumbnail(
                _mthumb,
                m,
                kind,
                match_caption_lbl=_mcap,
                orig_thumb=th,
            )
        for j, arr in enumerate(self._merc_path_arrows):
            prev_kind = self._merc_section_kinds[j]
            score_attr = CALL_MERC_SCORE_KEY[prev_kind]
            thr_attr = CALL_MERC_THR_KEY[prev_kind]
            sc = float(getattr(m, score_attr))
            thr = snapshot_float(snap, thr_attr, float(getattr(m, thr_attr)))
            arr.feed_threshold_edge(sc, thr)
        apply_sequence_autoscroll(
            panel=self,
            scroll=self._scroll,
            pipela_mod=m,
            feature=FEAT_CALL_MERC,
            targets=self._merc_section_frames,
            active_check=lambda mod: bool(getattr(mod, "call_merc_active", False)),
        )
