"""Intro Skip(런처·게임) — 런처 자동 클릭, Intro Skip·Accept 템플릿·임계값."""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from pipela_core.display_timing import display_tick_ms
from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_float
from pipela_qt import theme as T
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox
from pipela_qt.dock_ui_phase import (
    UI_DOCK_PHASE_LAUNCHER,
    get_ui_dock_phase,
    is_start_game_launcher_template1_effective_on,
)
from pipela_qt.panels.image_preview import pixmap_from_pil
from pipela_qt.panels.settings_chrome import (
    add_settings_control_row_centered,
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
from pipela_qt.settings_binary_toggle import SettingsBinaryToggleSwitch
from pipela_qt.ui_adaptive import scale_px
from pipela_qt.qt_capture import attach_template_toolbar
from pipela_qt.template_section_probe_frame import TemplateLiveScoreReadout
from pipela_qt.typography_refresh_support import TypographyStyleBundle

_THR_MIN = 0.1
_THR_MAX = 1.0


class StartGameSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._typo = TypographyStyleBundle()

        outer = QVBoxLayout(self)
        self._outer = outer
        outer.setSpacing(settings_root_vertical_spacing())
        outer.setContentsMargins(0, 0, 0, 0)
        t1 = QLabel("Intro Skip")
        t1.setStyleSheet(settings_page_title_style())
        self._typo.add(lambda w=t1: w.setStyleSheet(settings_page_title_style()))
        settings_label_align_center_h(t1)
        outer.addWidget(t1)

        self._cb_lbl = QLabel("스마트업데이터 런처 창에서 자동 감지·클릭 사용")
        self._cb_lbl.setWordWrap(True)
        self._cb_lbl.setStyleSheet(f"color: {T.FG}; font-family: {T.FONT_CSS_UI};")
        self._typo.add(
            lambda w=self._cb_lbl: w.setStyleSheet(
                f"color: {T.FG}; font-family: {T.FONT_CSS_UI};",
            ),
        )
        settings_label_align_center_h(self._cb_lbl)
        outer.addWidget(self._cb_lbl)
        self._cb = SettingsBinaryToggleSwitch()
        self._cb.toggled.connect(self._commit_cb)
        add_settings_control_row_centered(outer, self._cb)

        outer.addWidget(make_settings_hline())

        scroll = QScrollArea()
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        inner.setContentsMargins(0, 0, 0, 0)
        lay = QVBoxLayout(inner)
        lay.setSpacing(settings_root_vertical_spacing())
        self._inner_lay = lay

        self._blk_launch = self._add_block(
            lay,
            "런처 START 버튼 (템플릿)",
            pil_kind="start_game_launcher",
            path_attr="START_GAME_IMAGE_PATH",
            score_attr="start_game_launcher_score",
            thr_attr="start_game_launcher_threshold",
            hint=None,
        )
        lay.addWidget(self._arrow())
        self._blk_intro = self._add_block(
            lay,
            "Intro Skip (이터널시티 게임 창)",
            pil_kind="start_game_intro_skip",
            path_attr="START_GAME_INTRO_SKIP_IMAGE_PATH",
            score_attr="start_game_intro_skip_score",
            thr_attr="start_game_intro_skip_threshold",
            hint=(
                "런처에서 START GAME을 클릭한 뒤에만 게임 클라이언트에서 Intro Skip UI를 한 번 클릭합니다."
            ),
        )
        to_intro = QLabel(
            f"Intro Skip: 런처 클릭 직후부터 "
            f"{int(pipela_mod.START_GAME_INTRO_SKIP_ARM_TIMEOUT_SEC)}초 동안만 게임 창 매칭·점수 갱신.",
        )
        to_intro.setWordWrap(True)
        to_intro.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=to_intro: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(to_intro)
        lay.addWidget(to_intro)
        lay.addWidget(self._arrow())
        self._blk_accept = self._add_block(
            lay,
            "Accept (이터널시티 게임 창)",
            pil_kind="start_game_accept",
            path_attr="START_GAME_ACCEPT_IMAGE_PATH",
            score_attr="start_game_accept_score",
            thr_attr="start_game_accept_threshold",
            hint="Intro Skip 클릭이 끝난 뒤에만 Accept UI를 한 번 클릭합니다.",
        )
        to_ac = QLabel(
            f"Accept: Intro Skip 직후부터 "
            f"{int(pipela_mod.START_GAME_ACCEPT_ARM_TIMEOUT_SEC)}초 동안만 게임 창 매칭·점수 갱신.",
        )
        to_ac.setWordWrap(True)
        to_ac.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=to_ac: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(to_ac)
        lay.addWidget(to_ac)
        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

    def apply_scaled_typography(self) -> None:
        self._outer.setSpacing(settings_root_vertical_spacing())
        self._inner_lay.setSpacing(settings_root_vertical_spacing())
        self._cb.refresh_for_scale()
        for blk in (self._blk_launch, self._blk_intro, self._blk_accept):
            blk["sp"].setMaximumWidth(scale_px(88))
            blk["thumb"].setMinimumSize(scale_px(120), scale_px(72))
        self._typo.apply()
        self._tick()

    def _arrow(self) -> QLabel:
        a = QLabel("↓")
        a.setStyleSheet(settings_path_connector_style())
        self._typo.add(lambda w=a: w.setStyleSheet(settings_path_connector_style()))
        settings_label_align_center_h(a)
        return a

    def _add_block(
        self,
        lay: QVBoxLayout,
        title: str,
        *,
        pil_kind: str,
        path_attr: str,
        score_attr: str,
        thr_attr: str,
        hint: str | None,
    ) -> dict:
        st = QLabel(title)
        st.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st)
        lay.addWidget(st)
        if hint:
            h = QLabel(hint)
            h.setWordWrap(True)
            h.setStyleSheet(settings_footnote_style())
            self._typo.add(lambda w=h: w.setStyleSheet(settings_footnote_style()))
            settings_label_align_center_h(h)
            lay.addWidget(h)
        path_lbl = QLabel("")
        path_lbl.setWordWrap(True)
        path_lbl.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=path_lbl: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(path_lbl)
        lay.addWidget(path_lbl)
        thumb = QLabel()
        thumb.setMinimumSize(scale_px(120), scale_px(72))
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;")
        lay.addWidget(thumb)
        attach_template_toolbar(lay, self._m, pil_kind, self._tick)
        cur = TemplateLiveScoreReadout(self._m, pil_kind)
        self._typo.add(lambda w=cur: w.setStyleSheet(f"font-family: {T.FONT_CSS_UI};"))
        sp = DragDoubleSpinBox()
        sp.setRange(_THR_MIN, _THR_MAX)
        sp.setDecimals(2)
        sp.setSingleStep(0.01)
        sp.setMaximumWidth(scale_px(88))

        def _commit(_v: float) -> None:
            setattr(self._m, thr_attr, float(_v))
            sync_registry_snapshot_from_module(self._m)
            self._m.schedule_save_config()

        sp.valueChanged.connect(_commit)
        add_template_similarity_row(lay, cur, sp)
        return {
            "pil_kind": pil_kind,
            "path_attr": path_attr,
            "score_attr": score_attr,
            "thr_attr": thr_attr,
            "path_lbl": path_lbl,
            "thumb": thumb,
            "cur": cur,
            "sp": sp,
        }

    def _commit_cb(self) -> None:
        if get_ui_dock_phase(self._m) == UI_DOCK_PHASE_LAUNCHER:
            self._cb.blockSignals(True)
            self._cb.setChecked(True)
            self._cb.blockSignals(False)
            return
        self._m.start_game_launcher_active = self._cb.isChecked()
        sync_registry_snapshot_from_module(self._m)
        self._m.schedule_save_config()

    def _reload(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        self._cb.blockSignals(True)
        self._cb.setChecked(is_start_game_launcher_template1_effective_on(m, snap))
        self._cb.setEnabled(get_ui_dock_phase(m) != UI_DOCK_PHASE_LAUNCHER)
        self._cb.blockSignals(False)
        for blk in (self._blk_launch, self._blk_intro, self._blk_accept):
            sp = blk["sp"]
            thr_a = blk["thr_attr"]
            sp.blockSignals(True)
            sp.setValue(
                max(
                    _THR_MIN,
                    min(
                        _THR_MAX,
                        snapshot_float(snap, thr_a, float(getattr(m, thr_a))),
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
        want = is_start_game_launcher_template1_effective_on(m, snap)
        if self._cb.isChecked() != want:
            self._cb.blockSignals(True)
            self._cb.setChecked(want)
            self._cb.blockSignals(False)
        self._cb.setEnabled(get_ui_dock_phase(m) != UI_DOCK_PHASE_LAUNCHER)
        for blk in (self._blk_launch, self._blk_intro, self._blk_accept):
            score_a = blk["score_attr"]
            thr_a = blk["thr_attr"]
            path_a = blk["path_attr"]
            pil_kind = blk["pil_kind"]
            blk["cur"].setText(f"{float(getattr(m, score_a)):.2f}")
            sp = blk["sp"]
            if not sp.hasFocus():
                sp.blockSignals(True)
                sp.setValue(
                    max(
                        _THR_MIN,
                        min(
                            _THR_MAX,
                            snapshot_float(snap, thr_a, float(getattr(m, thr_a))),
                        ),
                    )
                )
                sp.blockSignals(False)
            path = getattr(m, path_a)
            blk["path_lbl"].setText(f"템플릿: {os.path.basename(path) if path else '—'}")
            pil_img = m._template_capture_load_existing_pil(pil_kind)
            pm = pixmap_from_pil(pil_img, scale_px(200), scale_px(120))
            th = blk["thumb"]
            if pm:
                th.setText("")
                th.setPixmap(pm)
                th.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;")
            else:
                th.clear()
                th.setText("없음")
                th.setStyleSheet(
                    f"background: {T.PANEL_BG}; color: {T.FG_DIM}; border-radius: {scale_px(4)}px;",
                )
