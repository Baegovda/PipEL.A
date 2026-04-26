"""Call Merc 설정 — 4단계 템플릿 임계값·실시간 점수."""

from __future__ import annotations

import os

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
from pipela_qt.panels.settings_chrome import (
    add_template_similarity_row,
    configure_settings_scroll_area,
    make_settings_hline,
    settings_footnote_style,
    settings_label_align_center_h,
    settings_page_title_style,
    settings_path_connector_style,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.ui_adaptive import scale_px
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
        self._rows: dict[str, tuple[TemplateLiveScoreReadout, DragDoubleSpinBox, QLabel, QLabel]] = {}
        self._typo = TypographyStyleBundle()
        self._merc_thumb_state: dict[str, dict[str, object]] = {}

        outer = QVBoxLayout(self)
        self._outer = outer
        outer.setSpacing(settings_root_vertical_spacing())
        outer.setContentsMargins(0, 0, 0, 0)
        t1 = QLabel("Call Merc 설정")
        t1.setStyleSheet(settings_page_title_style())
        self._typo.add(lambda w=t1: w.setStyleSheet(settings_page_title_style()))
        settings_label_align_center_h(t1)
        outer.addWidget(t1)
        outer.addWidget(make_settings_hline())

        scroll = QScrollArea()
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        inner.setContentsMargins(0, 0, 0, 0)
        self._inner = inner
        self._merc_section_frames: list[TemplateProbeSectionFrame] = []
        lay = QVBoxLayout(inner)
        lay.setSpacing(settings_root_vertical_spacing())
        self._inner_lay = lay

        for i, sec in enumerate(pipela_mod._CALL_MERC_SETTINGS_SECTIONS):
            title, kind, *_r = sec
            if i > 0:
                arr = QLabel("↓")
                arr.setStyleSheet(settings_path_connector_style())
                self._typo.add(lambda w=arr: w.setStyleSheet(settings_path_connector_style()))
                settings_label_align_center_h(arr)
                lay.addWidget(arr)
            fr = TemplateProbeSectionFrame(self._m, kind, inner)
            self._merc_section_frames.append(fr)
            block = fr.content_layout()
            st = QLabel(title)
            st.setStyleSheet(settings_section_heading_style())
            self._typo.add(lambda w=st: w.setStyleSheet(settings_section_heading_style()))
            settings_label_align_center_h(st)
            block.addWidget(st)
            path_key = CALL_MERC_PATH_KEY[kind]
            reg_key = CALL_MERC_REG_DATA_KEY[kind]
            path = getattr(pipela_mod, path_key)
            pl = QLabel(f"템플릿: {os.path.basename(path) if path else '—'}")
            pl.setWordWrap(True)
            pl.setStyleSheet(settings_footnote_style())
            self._typo.add(lambda w=pl: w.setStyleSheet(settings_footnote_style()))
            settings_label_align_center_h(pl)
            block.addWidget(pl)
            th = QLabel()
            th.setMinimumSize(scale_px(120), scale_px(72))
            th.setAlignment(Qt.AlignmentFlag.AlignCenter)
            th.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;")
            block.addWidget(th)
            attach_template_toolbar(block, pipela_mod, kind, self._tick)
            cur = TemplateLiveScoreReadout(self._m, kind)
            self._typo.add(lambda w=cur: w.setStyleSheet(f"font-family: {T.FONT_CSS_UI};"))
            sp = DragDoubleSpinBox()
            sp.setRange(_THR_MIN, _THR_MAX)
            sp.setDecimals(2)
            sp.setSingleStep(0.01)
            sp.setMaximumWidth(scale_px(88))
            thr_attr = CALL_MERC_THR_KEY[kind]

            def _mk_commit(attr: str):
                def _go(v: float) -> None:
                    setattr(self._m, attr, float(v))
                    sync_registry_snapshot_from_module(self._m)
                    self._m.schedule_save_config()

                return _go

            sp.valueChanged.connect(_mk_commit(thr_attr))
            add_template_similarity_row(block, cur, sp)
            self._rows[kind] = (cur, sp, pl, th)
            lay.addWidget(fr)
        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

    def apply_scaled_typography(self) -> None:
        self._outer.setSpacing(settings_root_vertical_spacing())
        self._inner_lay.setSpacing(settings_root_vertical_spacing())
        for fr in self._merc_section_frames:
            fr.apply_scale_margins()
        for _k, (_c, sp, _p, th) in self._rows.items():
            sp.setMaximumWidth(scale_px(88))
            th.setMinimumSize(scale_px(120), scale_px(72))
        self._typo.apply()
        self._tick()

    def _reload(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        for kind, (_c, sp, _p, _t) in self._rows.items():
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
        self._reload()
        self._timer.start(max(16, int(display_tick_ms())))

    def hideEvent(self, e) -> None:
        self._timer.stop()
        super().hideEvent(e)

    def _tick(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        for kind, (cur_l, sp, path_l, th) in self._rows.items():
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
            _path_cap = f"템플릿: {os.path.basename(path) if path else '—'}"
            if getattr(path_l, "_pipela_last_txt", None) != _path_cap:
                path_l._pipela_last_txt = _path_cap
                path_l.setText(_path_cap)
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
                _had = getattr(th, "_pipela_last_thumb_sig", None) is not None
                _empty = getattr(th, "_pipela_thumb_empty", None) is True
                if _had or not _empty:
                    th._pipela_last_thumb_sig = None
                    th._pipela_thumb_empty = True
                    th.clear()
                    th.setText("없음")
                    th.setStyleSheet(
                        f"background: {T.PANEL_BG}; color: {T.FG_DIM}; border-radius: {scale_px(4)}px;",
                    )
