"""Reload 설정 — 임계값·탄 수·실시간 점수·템플릿 썸네일 (`reload_threshold` 레지)."""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from pipela_core.display_timing import display_tick_ms
from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_float, snapshot_int
from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import (
    add_settings_field_row,
    add_template_similarity_row,
    configure_settings_scroll_area,
    settings_label_align_center_h,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.settings_sequence_autoscroll import FEAT_RELOAD, apply_sequence_autoscroll
from pipela_qt.template_path_connector_arrow import TemplatePathConnectorArrow
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox, DragSpinBox
from pipela_qt.qt_capture import attach_template_toolbar
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v
from pipela_qt.panels.template_last_match_thumb import (
    append_side_by_side_target_and_match_previews,
    fit_template_thumb_label_to_pixmap,
    thumb_preview_max_wh,
    thumb_preview_slot_min_wh,
    update_last_match_thumbnail,
)
from pipela_qt.panels.thumbnail_preview_dialog import attach_template_thumbnail_click_preview
from pipela_qt.template_section_probe_frame import (
    TemplateLiveScoreReadout,
    TemplateProbeSectionFrame,
)
from pipela_qt.typography_refresh_support import TypographyStyleBundle

_THR_MIN = 0.1
_THR_MAX = 1.0

_RELOAD_SLOT_TO_PATH_ATTR: dict[str, str] = {
    "reload_nobullet": "RELOAD_NOBULLET_IMAGE_PATH",
    "reload_bullet": "RELOAD_BULLET_IMAGE_PATH",
    "reload_vault": "RELOAD_VAULT_IMAGE_PATH",
}


def _scaled_pixmap(path: str, max_w: int, max_h: int) -> QPixmap | None:
    if not path or not os.path.isfile(path):
        return None
    img = QImage(path)
    if img.isNull():
        return None
    pm = QPixmap.fromImage(img)
    return pm.scaled(
        max_w,
        max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


class ReloadSettingsPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._typo = TypographyStyleBundle()
        self._path_arrows: list[TemplatePathConnectorArrow] = []

        root = QVBoxLayout(self)
        self._root = root
        root.setSpacing(settings_root_vertical_spacing())
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        self._scroll = scroll
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        self._inner = inner
        self._probe_frames: list[TemplateProbeSectionFrame] = []
        inner_l = QVBoxLayout(inner)
        self._inner_l = inner_l
        inner_l.setSpacing(settings_root_vertical_spacing())

        (
            self._nb_thr,
            self._nb_cur,
            self._nb_thumb,
            self._nb_match_cap,
            self._nb_match_thumb,
        ) = self._add_template_block(
            inner_l,
            "1. 트리거 탄약 없음 안내",
            "reload_nobullet",
        )
        inner_l.addWidget(self._make_path_arrow())
        (
            self._bu_thr,
            self._bu_cur,
            self._bu_thumb,
            self._bu_match_cap,
            self._bu_match_thumb,
        ) = self._add_template_block(
            inner_l,
            "2. 탄약 수급 (금고)",
            "reload_bullet",
        )
        inner_l.addWidget(self._make_path_arrow())
        (
            self._vault_thr,
            self._vault_cur,
            self._vault_thumb,
            self._vault_match_cap,
            self._vault_match_thumb,
        ) = self._add_template_block(
            inner_l,
            "3. 은행 금고",
            "reload_vault",
        )

        inner_l.addWidget(self._make_path_arrow())
        ammo_t = QLabel("4. 장전할 탄 갯수")
        self._ammo_scroll_anchor = ammo_t
        ammo_t.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=ammo_t: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(ammo_t)
        inner_l.addWidget(ammo_t)
        self._ammo = DragSpinBox()
        self._ammo.setRange(1, 99999)
        self._ammo.setMaximumWidth(scale_px_h(88))
        self._ammo.valueChanged.connect(self._commit_ammo)
        add_settings_field_row(inner_l, "", self._ammo)

        inner_l.addStretch(1)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        self._reload_fields()
        # _refresh_path_thumb: 경로/mtime 불변 시 QImage·scaled 생략 (cProfile: _scaled_pixmap 폭주)
        self._thumb_pm_cache: dict[int, tuple[str, float, QPixmap]] = {}
        self._reload_scroll_targets: list[QWidget] = [
            self._probe_frames[0],
            self._probe_frames[1],
            self._probe_frames[2],
            self._ammo_scroll_anchor,
        ]

    def apply_scaled_typography(self) -> None:
        self._root.setSpacing(settings_root_vertical_spacing())
        self._inner_l.setSpacing(settings_root_vertical_spacing())
        for fr in self._probe_frames:
            fr.apply_scale_margins()
        for sp in (self._nb_thr, self._bu_thr, self._vault_thr, self._ammo):
            sp.setMaximumWidth(scale_px_h(88))
        self._typo.apply()
        self._thumb_pm_cache.clear()
        self._tick()

    def _make_path_arrow(self) -> TemplatePathConnectorArrow:
        a = TemplatePathConnectorArrow()
        self._typo.add(a.refresh_for_scale)
        self._path_arrows.append(a)
        return a

    def _add_template_block(
        self,
        lay: QVBoxLayout,
        section_title: str,
        slot: str,
    ) -> tuple[DragDoubleSpinBox, QLabel, QLabel, QLabel, QLabel]:
        fr = TemplateProbeSectionFrame(self._m, slot, self._inner)
        self._probe_frames.append(fr)
        block = fr.content_layout()
        st = QLabel(section_title)
        st.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st)
        block.addWidget(st)
        _tmw, _tmh = thumb_preview_slot_min_wh()
        thumb = QLabel()
        thumb.setMinimumSize(_tmw, _tmh)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px_v(4)}px;")
        path_attr = _RELOAD_SLOT_TO_PATH_ATTR[slot]
        attach_template_thumbnail_click_preview(
            thumb,
            lambda a=path_attr: str(getattr(self._m, a, "") or ""),
        )
        last_cap, last_hit = append_side_by_side_target_and_match_previews(
            block,
            self._typo,
            thumb,
            pipela_mod=self._m,
            hit_kind=slot,
        )
        cur = TemplateLiveScoreReadout(self._m, slot)
        self._typo.add(cur.refresh_metric_font)
        sp = DragDoubleSpinBox()
        sp.setRange(_THR_MIN, _THR_MAX)
        sp.setDecimals(2)
        sp.setSingleStep(0.01)
        sp.setMaximumWidth(scale_px_h(88))
        slot_cb = slot

        def _on_val(_v: float) -> None:
            self._commit_thr_slot(slot_cb)

        sp.valueChanged.connect(_on_val)
        add_template_similarity_row(
            block,
            cur,
            sp,
            pipela_mod=self._m,
            probe_capture_kind=slot,
            typography_bundle=self._typo,
        )
        attach_template_toolbar(
            block,
            self._m,
            slot,
            self._tick,
            typography_bundle=self._typo,
        )
        lay.addWidget(fr)
        return sp, cur, thumb, last_cap, last_hit

    def _commit_thr_slot(self, slot: str) -> None:
        m = self._m
        if slot == "reload_nobullet":
            v = float(self._nb_thr.value())
            m.reload_nobullet_threshold = v
            m.reload_threshold = v
        elif slot == "reload_bullet":
            m.reload_bullet_threshold = float(self._bu_thr.value())
        elif slot == "reload_vault":
            m.reload_vault_threshold = float(self._vault_thr.value())
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()

    def _commit_ammo(self) -> None:
        self._m.reload_ammo_count = int(self._ammo.value())
        sync_registry_snapshot_from_module(self._m)
        self._m.schedule_save_config()

    def _reload_fields(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        for sp in (self._nb_thr, self._bu_thr, self._vault_thr):
            sp.blockSignals(True)
        self._ammo.blockSignals(True)
        self._nb_thr.setValue(
            max(
                _THR_MIN,
                min(
                    _THR_MAX,
                    snapshot_float(snap, "reload_nobullet_threshold", float(m.reload_nobullet_threshold)),
                ),
            )
        )
        self._bu_thr.setValue(
            max(
                _THR_MIN,
                min(
                    _THR_MAX,
                    snapshot_float(snap, "reload_bullet_threshold", float(m.reload_bullet_threshold)),
                ),
            )
        )
        self._vault_thr.setValue(
            max(
                _THR_MIN,
                min(
                    _THR_MAX,
                    snapshot_float(snap, "reload_vault_threshold", float(m.reload_vault_threshold)),
                ),
            )
        )
        self._ammo.setValue(
            max(1, min(99999, snapshot_int(snap, "reload_ammo_count", int(m.reload_ammo_count)))),
        )
        for sp in (self._nb_thr, self._bu_thr, self._vault_thr):
            sp.blockSignals(False)
        self._ammo.blockSignals(False)

    def showEvent(self, e) -> None:
        super().showEvent(e)
        for arr in self._path_arrows:
            arr.reset_edge_state()
        self._reload_fields()
        self._timer.start(max(240, int(display_tick_ms())))

    def hideEvent(self, e) -> None:
        self._timer.stop()
        self._last_reload_scroll_step = None
        for arr in self._path_arrows:
            arr.hide_idle()
        super().hideEvent(e)

    def _tick(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        self._nb_cur.setText(f"{float(m.nobullet_detection_score):.2f}")
        self._bu_cur.setText(f"{float(m.bullet_detection_score):.2f}")
        self._vault_cur.setText(f"{float(m.vault_detection_score):.2f}")

        def _sync_sp(sp: DragDoubleSpinBox, val: float) -> None:
            if sp.hasFocus():
                return
            sp.blockSignals(True)
            sp.setValue(max(_THR_MIN, min(_THR_MAX, float(val))))
            sp.blockSignals(False)

        _sync_sp(
            self._nb_thr,
            snapshot_float(snap, "reload_nobullet_threshold", float(m.reload_nobullet_threshold)),
        )
        _sync_sp(
            self._bu_thr,
            snapshot_float(snap, "reload_bullet_threshold", float(m.reload_bullet_threshold)),
        )
        _sync_sp(
            self._vault_thr,
            snapshot_float(snap, "reload_vault_threshold", float(m.reload_vault_threshold)),
        )
        if not self._ammo.hasFocus():
            self._ammo.blockSignals(True)
            self._ammo.setValue(
                max(
                    1,
                    min(
                        99999,
                        snapshot_int(snap, "reload_ammo_count", int(m.reload_ammo_count)),
                    ),
                )
            )
            self._ammo.blockSignals(False)

        self._refresh_path_thumb(m.RELOAD_NOBULLET_IMAGE_PATH, self._nb_thumb)
        self._refresh_path_thumb(m.RELOAD_BULLET_IMAGE_PATH, self._bu_thumb)
        self._refresh_path_thumb(m.RELOAD_VAULT_IMAGE_PATH, self._vault_thumb)
        update_last_match_thumbnail(
            self._nb_match_thumb,
            m,
            "reload_nobullet",
            match_caption_lbl=self._nb_match_cap,
            orig_thumb=self._nb_thumb,
        )
        update_last_match_thumbnail(
            self._bu_match_thumb,
            m,
            "reload_bullet",
            match_caption_lbl=self._bu_match_cap,
            orig_thumb=self._bu_thumb,
        )
        update_last_match_thumbnail(
            self._vault_match_thumb,
            m,
            "reload_vault",
            match_caption_lbl=self._vault_match_cap,
            orig_thumb=self._vault_thumb,
        )
        if self._path_arrows:
            nb_t = snapshot_float(snap, "reload_nobullet_threshold", float(m.reload_nobullet_threshold))
            self._path_arrows[0].feed_threshold_edge(float(m.nobullet_detection_score), nb_t)
        if len(self._path_arrows) >= 2:
            bu_t = snapshot_float(snap, "reload_bullet_threshold", float(m.reload_bullet_threshold))
            self._path_arrows[1].feed_threshold_edge(float(m.bullet_detection_score), bu_t)
        if len(self._path_arrows) >= 3:
            va_t = snapshot_float(snap, "reload_vault_threshold", float(m.reload_vault_threshold))
            self._path_arrows[2].feed_threshold_edge(float(m.vault_detection_score), va_t)

        apply_sequence_autoscroll(
            panel=self,
            scroll=self._scroll,
            pipela_mod=m,
            feature=FEAT_RELOAD,
            targets=self._reload_scroll_targets,
            active_check=lambda mod: bool(getattr(mod, "reload_active", False)),
        )

    def _refresh_path_thumb(self, path: str, thumb: QLabel) -> None:
        key = id(thumb)
        sig: tuple[str, float] | None = None
        try:
            if path and os.path.isfile(path):
                np = os.path.normpath(path)
                sig = (np, float(os.path.getmtime(np)))
        except OSError:
            sig = None
        if sig is not None:
            hit = self._thumb_pm_cache.get(key)
            if hit is not None and hit[0] == sig[0] and hit[1] == sig[1]:
                pm = hit[2]
            else:
                _tw, _thm = thumb_preview_max_wh()
                pm = _scaled_pixmap(path, _tw, _thm)
                if pm is not None and not pm.isNull():
                    self._thumb_pm_cache[key] = (sig[0], sig[1], pm)
                else:
                    self._thumb_pm_cache.pop(key, None)
                    pm = None
        else:
            self._thumb_pm_cache.pop(key, None)
            pm = None
        fit_template_thumb_label_to_pixmap(
            thumb,
            pm if pm is not None and not pm.isNull() else None,
            empty_text="없음",
        )
