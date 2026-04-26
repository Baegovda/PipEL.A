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
    make_settings_hline,
    settings_footnote_style,
    settings_label_align_center_h,
    settings_page_title_style,
    settings_path_connector_style,
    settings_root_vertical_spacing,
    settings_section_heading_style,
)
from pipela_qt.scrub_spinboxes import DragDoubleSpinBox, DragSpinBox
from pipela_qt.qt_capture import attach_template_toolbar
from pipela_qt.ui_adaptive import scale_px
from pipela_qt.template_section_probe_frame import (
    TemplateLiveScoreReadout,
    TemplateProbeSectionFrame,
)
from pipela_qt.typography_refresh_support import TypographyStyleBundle

_THR_MIN = 0.1
_THR_MAX = 1.0


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

        root = QVBoxLayout(self)
        self._root = root
        root.setSpacing(settings_root_vertical_spacing())
        root.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Reload 설정")
        title.setStyleSheet(settings_page_title_style())
        self._typo.add(lambda w=title: w.setStyleSheet(settings_page_title_style()))
        settings_label_align_center_h(title)
        root.addWidget(title)

        root.addWidget(make_settings_hline())

        scroll = QScrollArea()
        configure_settings_scroll_area(scroll)
        inner = QWidget()
        self._inner = inner
        self._probe_frames: list[TemplateProbeSectionFrame] = []
        inner_l = QVBoxLayout(inner)
        self._inner_l = inner_l
        inner_l.setSpacing(settings_root_vertical_spacing())

        self._nb_thr, self._nb_cur, self._nb_path, self._nb_thumb = self._add_template_block(
            inner_l,
            "탄약 없음 · 노불릿",
            "reload_nobullet",
        )
        inner_l.addWidget(self._arrow())
        self._bu_thr, self._bu_cur, self._bu_path, self._bu_thumb = self._add_template_block(
            inner_l,
            "재장전 · 불릿 UI",
            "reload_bullet",
        )
        inner_l.addWidget(self._arrow())
        self._vault_thr, self._vault_cur, self._vault_path, self._vault_thumb = self._add_template_block(
            inner_l,
            "Vault · 보관함",
            "reload_vault",
            extra_hint=(
                "ROI와 Vault 템플릿을 지정하면, Bullet이 안 잡힐 때 이 영역에서 더블클릭 후 "
                "Bullet을 한 번 더 시도합니다."
            ),
        )

        inner_l.addWidget(self._arrow())
        ammo_t = QLabel("입력할 탄 수 (장전)")
        ammo_t.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=ammo_t: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(ammo_t)
        inner_l.addWidget(ammo_t)
        ammo_hint = QLabel(
            "Bullet.png 영역 더블클릭 후, 아래 발수가 숫자 키로 입력되고 Enter가 눌립니다.",
        )
        ammo_hint.setWordWrap(True)
        ammo_hint.setStyleSheet(settings_footnote_style())
        self._typo.add(lambda w=ammo_hint: w.setStyleSheet(settings_footnote_style()))
        settings_label_align_center_h(ammo_hint)
        inner_l.addWidget(ammo_hint)
        self._ammo = DragSpinBox()
        self._ammo.setRange(1, 99999)
        self._ammo.valueChanged.connect(self._commit_ammo)
        add_settings_field_row(inner_l, "장전 발수", self._ammo, QLabel("발"))

        inner_l.addStretch(1)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        self._reload_fields()
        # _refresh_path_thumb: 경로/mtime 불변 시 QImage·scaled 생략 (cProfile: _scaled_pixmap 폭주)
        self._thumb_pm_cache: dict[int, tuple[str, float, QPixmap]] = {}

    def apply_scaled_typography(self) -> None:
        self._root.setSpacing(settings_root_vertical_spacing())
        self._inner_l.setSpacing(settings_root_vertical_spacing())
        for fr in self._probe_frames:
            fr.apply_scale_margins()
        for sp in (self._nb_thr, self._bu_thr, self._vault_thr):
            sp.setMaximumWidth(scale_px(88))
        for th in (self._nb_thumb, self._bu_thumb, self._vault_thumb):
            th.setMinimumSize(scale_px(120), scale_px(72))
        self._typo.apply()
        self._thumb_pm_cache.clear()
        self._tick()

    def _arrow(self) -> QLabel:
        a = QLabel("↓")
        a.setStyleSheet(settings_path_connector_style())
        self._typo.add(lambda w=a: w.setStyleSheet(settings_path_connector_style()))
        settings_label_align_center_h(a)
        return a

    def _add_template_block(
        self,
        lay: QVBoxLayout,
        section_title: str,
        slot: str,
        *,
        extra_hint: str | None = None,
    ) -> tuple[DragDoubleSpinBox, QLabel, QLabel, QLabel]:
        fr = TemplateProbeSectionFrame(self._m, slot, self._inner)
        self._probe_frames.append(fr)
        block = fr.content_layout()
        st = QLabel(section_title)
        st.setStyleSheet(settings_section_heading_style())
        self._typo.add(lambda w=st: w.setStyleSheet(settings_section_heading_style()))
        settings_label_align_center_h(st)
        block.addWidget(st)
        if extra_hint:
            eh = QLabel(extra_hint)
            eh.setWordWrap(True)
            eh.setStyleSheet(settings_footnote_style())
            self._typo.add(lambda w=eh: w.setStyleSheet(settings_footnote_style()))
            settings_label_align_center_h(eh)
            block.addWidget(eh)
        path_lbl = QLabel("")
        path_lbl.setWordWrap(True)
        path_lbl.setStyleSheet(settings_footnote_style())
        self._typo.add(
            lambda w=path_lbl: w.setStyleSheet(settings_footnote_style()),
        )
        settings_label_align_center_h(path_lbl)
        block.addWidget(path_lbl)
        thumb = QLabel()
        thumb.setMinimumSize(scale_px(120), scale_px(72))
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;")
        block.addWidget(thumb)
        attach_template_toolbar(block, self._m, slot, self._tick)
        cur = TemplateLiveScoreReadout(self._m, slot)
        self._typo.add(lambda w=cur: w.setStyleSheet(f"font-family: {T.FONT_CSS_UI};"))
        sp = DragDoubleSpinBox()
        sp.setRange(_THR_MIN, _THR_MAX)
        sp.setDecimals(2)
        sp.setSingleStep(0.01)
        sp.setMaximumWidth(scale_px(88))
        slot_cb = slot

        def _on_val(_v: float) -> None:
            self._commit_thr_slot(slot_cb)

        sp.valueChanged.connect(_on_val)
        add_template_similarity_row(block, cur, sp)
        lay.addWidget(fr)
        return sp, cur, path_lbl, thumb

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
        self._reload_fields()
        self._timer.start(max(240, int(display_tick_ms())))

    def hideEvent(self, e) -> None:
        self._timer.stop()
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

        self._refresh_path_thumb(
            m.RELOAD_NOBULLET_IMAGE_PATH,
            self._nb_path,
            self._nb_thumb,
        )
        self._refresh_path_thumb(
            m.RELOAD_BULLET_IMAGE_PATH,
            self._bu_path,
            self._bu_thumb,
        )
        self._refresh_path_thumb(
            m.RELOAD_VAULT_IMAGE_PATH,
            self._vault_path,
            self._vault_thumb,
        )

    def _refresh_path_thumb(self, path: str, path_lbl: QLabel, thumb: QLabel) -> None:
        base = os.path.basename(path) if path else "—"
        path_lbl.setText(f"템플릿: {base}")
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
                pm = _scaled_pixmap(path, scale_px(200), scale_px(120))
                if pm is not None and not pm.isNull():
                    self._thumb_pm_cache[key] = (sig[0], sig[1], pm)
                else:
                    self._thumb_pm_cache.pop(key, None)
                    pm = None
        else:
            self._thumb_pm_cache.pop(key, None)
            pm = None
        if pm is not None and not pm.isNull():
            thumb.setText("")
            thumb.setPixmap(pm)
            thumb.setStyleSheet(f"background: {T.PANEL_BG}; border-radius: {scale_px(4)}px;")
        else:
            thumb.clear()
            thumb.setText("없음")
            thumb.setStyleSheet(
                f"background: {T.PANEL_BG}; color: {T.FG_DIM}; border-radius: {scale_px(4)}px;",
            )
