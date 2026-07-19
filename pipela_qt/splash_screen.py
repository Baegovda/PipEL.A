"""Startup splash with smooth animated loading gauge (`shell.run_qt_application`)."""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass

from PyQt6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGradient,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QScreen,
)
from PyQt6.QtWidgets import QApplication, QWidget

from pipela_core.paths import PIPELA_SPLASH_IMAGE_PATH
from pipela_core.win32_game_windows import (
    get_window_outer_rect_screen,
    splash_placement_anchor_hwnd,
)
from pipela_core.version_info import PIPELA_APP_VERSION
from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.qt_icons import qt_application_icon

SPLASH_BRAND_TITLE = "PIP EL.A"

# Terminal-style CRT greens — wordmark / version / 현재 상태 문구
_TERM_HI = QColor(108, 255, 154)
_TERM_MUTED = QColor(74, 200, 120)
_TERM_SHADOW = QColor(10, 36, 22)

# -----------------------------------------------------------------------------
# Layout tokens (zones A/B/C footer grid — keep in sync across image + synth)
# -----------------------------------------------------------------------------
SPLASH_MAX_IMAGE_WIDTH_PX = 720
SYNTH_W = 640
SYNTH_H = 368
MARGIN_X_MIN_PX = 28  # horizontal margin / nominal bottom inset for bar
FOOTER_SCRIM_RATIO = 0.28  # Zone C height ratio (~bottom 28%)

BAR_H_CAP = (17, 27)  # taller capsule; percent lives inside bar
GAP_MSG_AND_BAR = 8


def margin_x_for_width(ww: int) -> int:
    return max(MARGIN_X_MIN_PX, ww // 17)


def _smoothstep01(u: float) -> float:
    u = max(0.0, min(1.0, float(u)))
    return u * u * (3.0 - 2.0 * u)


@dataclass(frozen=True)
class SplashFooterGeom:
    """Footered Zone C numeric layout derived once per paint/frame."""

    ww: int
    hh: int
    margin_x: int
    footer_top: float
    rx: int
    rw: int
    bar_h: int
    y_bar: int
    msg_h: int
    ry_msg: int
    gap_msg_bar: int


def splash_footer_geom(ww: int, hh: int) -> SplashFooterGeom:
    """Stable footer rectangles: status then progress bar (% inside bar)."""
    xm = margin_x_for_width(ww)
    footer_top_f = float(hh) * (1.0 - FOOTER_SCRIM_RATIO)
    bh = max(BAR_H_CAP[0], min(BAR_H_CAP[1], max(17, hh // 26)))
    gap_msg_bar = max(GAP_MSG_AND_BAR, hh // 64)
    bottom_pad = max(xm, MARGIN_X_MIN_PX + 8)
    y_bar = hh - bottom_pad - bh

    ry_limit_top = footer_top_f + max(14.0, hh * 0.03)
    available = float(y_bar) - float(ry_limit_top) - float(gap_msg_bar)
    mh = max(22, min(88, int(available)))

    ry_msg_i = max(int(footer_top_f) + int(max(14.0, hh * 0.03)), 8)
    if ry_msg_i + mh + gap_msg_bar >= y_bar - 4:
        mh = max(18, min(mh, y_bar - ry_msg_i - gap_msg_bar - 6))

    return SplashFooterGeom(
        ww=ww,
        hh=hh,
        margin_x=xm,
        footer_top=footer_top_f,
        rx=xm,
        rw=max(120, ww - 2 * xm),
        bar_h=bh,
        y_bar=max(footer_top_f + 22, min(y_bar, hh - bh - MARGIN_X_MIN_PX)),
        msg_h=max(18, mh),
        ry_msg=ry_msg_i,
        gap_msg_bar=gap_msg_bar,
    )


def footer_overlay_rect(g: SplashFooterGeom) -> QRectF:
    """Cover Zone C band for gradients (full widget width below footer_top)."""
    return QRectF(0.0, g.footer_top, float(g.ww), float(g.hh - g.footer_top))


def _scale_image_pixmap(pm: QPixmap) -> QPixmap:
    """Cap very large splash assets — aspect preserved (plan: ~720 px width max)."""
    if pm.isNull():
        return pm
    w = pm.width()
    if w <= SPLASH_MAX_IMAGE_WIDTH_PX:
        return pm
    th = max(1, int(round(pm.height() * SPLASH_MAX_IMAGE_WIDTH_PX / float(max(1, w)))))
    scaled = pm.scaled(
        SPLASH_MAX_IMAGE_WIDTH_PX,
        th,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    return scaled if not scaled.isNull() else pm


def _splash_pixmap() -> QPixmap:
    """Prefer ``assets/splash.png`` (scaled max width); else light synthetic hero."""
    if os.path.isfile(PIPELA_SPLASH_IMAGE_PATH):
        pm = QPixmap(PIPELA_SPLASH_IMAGE_PATH)
        if not pm.isNull():
            return _scale_image_pixmap(pm)

    W, H = SYNTH_W, SYNTH_H
    bg = QPixmap(W, H)
    if bg.isNull():
        return QPixmap()
    p = QPainter(bg)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    try:
        g0 = QLinearGradient(QPointF(0.0, 0.0), QPointF(float(W), float(H)))
        g0.setColorAt(0.0, QColor("#070910"))
        g0.setColorAt(0.52, QColor("#101523"))
        g0.setColorAt(1.0, QColor("#071220"))
        p.fillRect(0, 0, W, H, QBrush(g0))

        ic = qt_application_icon()
        if not ic.isNull():
            sizes = ic.availableSizes()
            if sizes:
                src = ic.pixmap(sizes[-1])
            else:
                src = ic.pixmap(QSize(256, 256))
            if not src.isNull():
                max_side = min(W - 180, H - int(H * FOOTER_SCRIM_RATIO) - 96)
                max_side = max(96, max_side)
                scaled = src.scaled(
                    max_side,
                    max_side,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                ix = int((W - scaled.width()) * 0.5)
                iy = int(H * 0.38 - scaled.height() * 0.5)
                halo = QRadialGradient(
                    QPointF(ix + scaled.width() * 0.5, iy + scaled.height() * 0.52),
                    max(scaled.width(), scaled.height()) * 0.55,
                )
                halo.setColorAt(0.0, QColor(100, 175, 255, 62))
                halo.setColorAt(0.72, QColor(52, 100, 180, 12))
                halo.setColorAt(1.0, QColor(0, 0, 0, 0))
                p.fillRect(max(0, ix - 24), max(0, iy - 24), scaled.width() + 48, scaled.height() + 48, QBrush(halo))
                p.drawPixmap(ix, iy, scaled)

        ft = SYNTH_H * (1.0 - FOOTER_SCRIM_RATIO - 0.02)
        v_bottom = QLinearGradient(QPointF(0.0, ft), QPointF(0.0, float(H)))
        v_bottom.setColorAt(0.0, QColor(6, 8, 12, 0))
        v_bottom.setColorAt(0.52, QColor(10, 12, 18, int(235 * 0.45)))
        v_bottom.setColorAt(1.0, QColor(5, 7, 12, int(250 * 0.88)))
        p.fillRect(0, max(0, int(ft)), W, max(1, int(H - ft)), QBrush(v_bottom))
    finally:
        p.end()
    return bg


class PipelaSplashProgress(QWidget):
    """Frameless splash + bottom eased gauge — structured zones + subdued motion."""

    _TRACK = QColor(22, 28, 40, int(235 * 0.88))

    def __init__(
        self,
        pixmap: QPixmap,
        *,
        from_file: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(SPLASH_BRAND_TITLE)
        self._pm = pixmap
        self._from_file = from_file

        sz = pixmap.size()
        self.setFixedSize(sz.width(), sz.height())
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.SplashScreen,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._display_progress = 0.0
        self._target_progress = 0.0
        self._shine_phase = 0.0
        self._pulse = 0.0
        self._ambient_t = 0.0
        self._intro_phase = 0.0
        self._anim_t0 = time.perf_counter()
        self._loading_message = "시작 준비 중…"

        self._timer = QTimer(self)
        self._timer.setInterval(1000 // 60)
        self._timer.timeout.connect(self._on_tick)

    def start_animation(self) -> None:
        self._anim_t0 = time.perf_counter()
        self._intro_phase = 0.0
        self._timer.start()
        self.set_loading_target(0.06)

    def set_loading_target(self, t: float) -> None:
        nt = float(max(min(float(t), 1.0), 0.0))
        self._target_progress = max(self._target_progress, nt)

    def set_loading_message(self, text: str) -> None:
        t = str(text).strip()
        self._loading_message = t if t else "준비 중…"
        try:
            self.update()
            QApplication.processEvents()
        except Exception:
            self.update()

    def load_anim_quiescent(self, *, frac_threshold: float = 0.996) -> bool:
        tg = float(self._target_progress)
        dp = float(self._display_progress)
        return tg >= 0.998 and dp >= frac_threshold and abs(tg - dp) <= 4e-3

    def _on_tick(self) -> None:
        dp = float(self._display_progress)
        tp = float(self._target_progress)
        delta = tp - dp
        if abs(delta) < 0.0015:
            self._display_progress = tp
        else:
            alpha = max(0.09, min(0.42, 0.17 + abs(delta) * 0.42))
            self._display_progress += delta * alpha

        self._shine_phase += 0.042
        self._pulse += 0.062
        self._ambient_t += 0.016
        if self._intro_phase < 1.0:
            self._intro_phase = min(
                1.0,
                self._intro_phase + max(0.014, (1.0 - self._intro_phase) * 0.11),
            )
        self.update()

    def _draw_ambient_soft(
        self,
        p: QPainter,
        ww: int,
        hh: int,
        *,
        t: float,
        intro: float,
        from_file: bool,
    ) -> None:
        """Single drifting soft highlight — SourceOver only (plan: tame motion)."""
        intro_k = max(0.15, intro**0.62)
        base_a = int(52 if not from_file else 24)
        cx = ww * (0.48 + math.sin(t * 0.22) * 0.045)
        cy = hh * (0.38 + math.cos(t * 0.31) * 0.038)
        r = float(max(ww, hh)) * (0.38 if not from_file else 0.34)
        g = QRadialGradient(QPointF(cx, cy), r)
        a0 = min(88, int(base_a * intro_k))
        g.setColorAt(0.0, QColor(92, 160, 255, a0))
        g.setColorAt(0.55, QColor(72, 120, 200, int(a0 * 0.15)))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        hero_bottom = max(44, hh * (1.0 - FOOTER_SCRIM_RATIO) - 2.0)
        mask_top = hh * max(0.06, min(hero_bottom / hh, 0.28))
        h_fill = max(8, int(hero_bottom) - int(mask_top))
        if h_fill > 0:
            p.fillRect(0, int(mask_top), ww, h_fill, QBrush(g))

    def _draw_intro_veil(self, p: QPainter, ww: int, hh: int, intro: float) -> None:
        if intro >= 1.0:
            return
        eased = pow(1.0 - intro, 1.26)
        a = max(0, min(248, int(255 * eased)))
        if a <= 1:
            return
        p.fillRect(0, 0, ww, hh, QColor(5, 7, 12, a))

    def _draw_footer_scrim(
        self,
        p: QPainter,
        g: SplashFooterGeom,
        *,
        from_file: bool,
        fk: float,
    ) -> None:
        """Zone C: single vertical scrim gradient (plan: one readability layer)."""
        rect = footer_overlay_rect(g)
        hh_i = int(g.hh)
        drift = math.sin(float(self._ambient_t) * 0.55) * 3.5
        op_base = float(226 if from_file else 236)
        op_peak = max(212.0, min(266.0, op_base + drift))

        lg = QLinearGradient(QPointF(0.0, rect.top()), QPointF(0.0, float(hh_i)))
        lg.setColorAt(0.0, QColor(4, 6, 10, int(130 * fk)))
        lg.setColorAt(0.22, QColor(7, 9, 15, int(op_peak * 0.38 * fk)))
        lg.setColorAt(0.58, QColor(6, 8, 13, int(op_peak * 0.56 * fk)))
        lg.setColorAt(1.0, QColor(4, 5, 10, min(255, int((op_peak + 22.0) * fk))))
        p.fillRect(rect, QBrush(lg))

    def _draw_zone_a_brand_synthetic(
        self,
        p: QPainter,
        g: SplashFooterGeom,
        *,
        intro: float,
        t_wall: float,
    ) -> None:
        xm = float(g.margin_x)
        y0 = max(MARGIN_X_MIN_PX + 12, g.hh * 0.11)

        a_title = min(255, int(255 * _smoothstep01((intro - 0.06) / 0.52)))
        a_ver = min(255, int(255 * _smoothstep01((intro - 0.2) / 0.52)))

        accent_w = 3.5
        accent_h = 44.0
        sk = math.sin(t_wall * 1.6 + float(self._pulse) * 0.35)
        acg = QLinearGradient(
            QPointF(xm, float(y0 - 5)),
            QPointF(xm + accent_w, float(y0 - 5 + accent_h)),
        )
        tm = float(a_title / 255.0)
        acg.setColorAt(0.0, QColor(28, 100, 58, min(255, int(230 * tm))))
        acg.setColorAt(0.4 + 0.28 * (0.5 + 0.5 * sk), QColor(96, 255, 154, min(255, int(246 * tm))))
        acg.setColorAt(1.0, QColor(46, 160, 90, min(255, int(218 * tm))))
        p.fillRect(QRectF(xm, float(y0 - 5), accent_w, accent_h), QBrush(acg))

        ti = int(xm + accent_w + 13)
        title = SPLASH_BRAND_TITLE
        if a_title > 6:
            f_brand = app_default_qfont(18, QFont.Weight.DemiBold)
            f_brand.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.65)
            p.setFont(f_brand)
            sd = QColor(_TERM_SHADOW)
            sd.setAlpha(min(148, int(112 * (a_title / max(255, 1)))))
            p.setPen(sd)
            p.drawText(ti + 1, int(y0 - 4), g.ww - ti - int(xm), 34, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
            hi = QColor(_TERM_HI)
            hi.setAlpha(a_title)
            p.setPen(hi)
            p.drawText(ti, int(y0 - 5), g.ww - ti - int(xm), 34, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

        if a_ver > 6:
            f_ver = app_default_qfont(10, QFont.Weight.Medium)
            f_ver.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
            p.setFont(f_ver)
            ver = PIPELA_APP_VERSION.strip() or "—"
            mu = QColor(_TERM_MUTED)
            mu.setAlpha(int(242 * (a_ver / max(255, 1))))
            p.setPen(mu)
            p.drawText(ti, int(y0 + 36), g.ww - ti - int(xm), 22, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, ver)

    def _draw_footer_text_and_progress(
        self,
        p: QPainter,
        g: SplashFooterGeom,
        *,
        fk: float,
    ) -> None:
        pct_int = max(0, min(100, int(round(max(0.0, min(1.0, float(self._display_progress))) * 100.0))))
        pct_txt = f"{pct_int}%"
        msg = str(getattr(self, "_loading_message", "") or "").strip()

        rx, rw = int(g.rx), int(g.rw)
        hh = int(g.hh)

        flags_msg = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap

        if msg:
            fmsg = app_default_qfont(
                max(9, min(13, round(hh * 0.033))),
                QFont.Weight.Medium,
            )
            fmsg.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            p.setFont(fmsg)
            st = QColor(_TERM_HI)
            st.setAlpha(int(242 * 0.78 * fk))
            p.setPen(st)
            reserve = max(6, int(g.gap_msg_bar))
            msg_h_actual = max(22, min(int(g.msg_h), int(g.y_bar) - int(g.ry_msg) - reserve - 2))
            p.drawText(rx, int(g.ry_msg), rw, msg_h_actual, flags_msg, msg)

        w_track = float(max(124.0, g.ww - 2 * g.margin_x))
        x0 = (g.ww - w_track) * 0.5
        frac = max(0.0, min(1.0, float(self._display_progress)))
        yb = float(g.y_bar)
        bar_h = float(g.bar_h)
        rd = bar_h / 2.0
        pct_flags = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter

        track_rf = QRectF(x0, yb, w_track, bar_h)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rf, rd, rd)
        p.fillPath(track_path, self._TRACK)

        pen_track_outer = QPen(QColor(255, 255, 255, 26))
        pen_track_outer.setWidthF(1.0)
        p.setPen(pen_track_outer)
        p.drawPath(track_path)
        pen_track_inner = QPen(QColor(0, 0, 0, 46))
        pen_track_inner.setWidthF(0.85)
        p.setPen(pen_track_inner)
        inner_rf = QRectF(x0 + 0.55, yb + 0.55, w_track - 1.1, bar_h - 1.1)
        inner_path = QPainterPath()
        inner_path.addRoundedRect(inner_rf, max(0.0, rd - 0.55), max(0.0, rd - 0.55))
        p.drawPath(inner_path)

        wf = max(0.0, w_track * frac)

        fpct_sz = max(11, min(17, round(bar_h * 0.49)))
        fpct = app_default_qfont(fpct_sz, QFont.Weight.DemiBold)
        fpct.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.45)
        p.setFont(fpct)

        if wf >= 0.5:
            fill_rf = QRectF(x0, yb, wf, bar_h)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rf, rd, rd)

            lg = QLinearGradient(QPointF(x0, 0.0), QPointF(float(x0 + w_track), 0.0))
            lg.setColorAt(0.0, QColor(38, 110, 210, int(246 * 0.96)))
            lg.setColorAt(0.38, QColor(72, 168, 240, int(251 * 0.98)))
            lg.setColorAt(0.72, QColor(126, 210, 255, int(244 * 0.98)))
            lg.setColorAt(1.0, QColor(55, 150, 230, int(239 * 0.96)))
            p.setPen(Qt.PenStyle.NoPen)
            p.fillPath(fill_path, QBrush(lg))

            p.setClipPath(fill_path)
            sk = 0.5 + 0.5 * math.sin(float(self._shine_phase))
            gx_mid = float(x0) + wf * (0.18 + sk * 0.52)
            shine = QLinearGradient(QPointF(gx_mid - 70.0, 0), QPointF(gx_mid + 70.0, 0.0))
            shine.setSpread(QGradient.Spread.PadSpread)
            a_hi = min(146, int(94 + sk * 48))
            shine.setColorAt(0.0, QColor(255, 255, 255, 0))
            shine.setColorAt(0.43, QColor(255, 255, 255, min(138, int(40 + a_hi // 3))))
            shine.setColorAt(0.52, QColor(255, 255, 255, min(134, int(20 + sk * int(a_hi * 1.02)))))
            shine.setColorAt(0.62, QColor(255, 255, 255, 0))
            shine.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.fillRect(QRectF(x0 - 8.0, yb - 8.0, wf + 16.0, bar_h + 16.0), QBrush(shine))
            p.setClipping(False)

            gc_x = float(x0 + wf)
            cy = yb + bar_h * 0.5
            edge_sh = math.sin(float(self._pulse))
            edge = QRadialGradient(QPointF(gc_x, cy), rd * 1.72 + 10.5)
            edge.setColorAt(0.0, QColor(226, 248, 255, min(182, int(114 + edge_sh * 42))))
            edge.setColorAt(0.42, QColor(118, 200, 255, 62))
            edge.setColorAt(1.0, QColor(46, 120, 220, 0))
            p.fillPath(fill_path, QBrush(edge))

            lip = QPen(
                QColor(
                    232,
                    246,
                    255,
                    min(192, int(104 + math.sin(float(self._shine_phase)) * 58)),
                )
            )
            lip.setWidthF(1.02)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.strokePath(fill_path, lip)

        ix0, iy0, iw, ih = int(x0), int(yb), int(w_track), int(bar_h)
        sh_alpha = max(105, min(190, int(130 * fk)))
        shade = QColor(10, 12, 16, min(200, int(sh_alpha * 1.05)))
        for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            p.setPen(shade)
            p.drawText(ix0 + dx, iy0 + dy, iw, ih, pct_flags, pct_txt)
        p.setPen(QColor(246, 252, 255, int(min(254, int(246 * fk)))))
        p.drawText(ix0, iy0, iw, ih, pct_flags, pct_txt)

    def paintEvent(self, _event) -> None:
        ip = float(self._intro_phase)
        t_wall = time.perf_counter() - float(self._anim_t0)
        ww = self.width()
        hh = self.height()
        g = splash_footer_geom(ww, hh)
        fk = max(0.08, float(_smoothstep01((ip - 0.08) / 0.64)))

        if g.y_bar <= 12:
            super().paintEvent(_event)
            return

        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            # Zone B — hero pixmap
            p.drawPixmap(0, 0, self._pm)
            self._draw_ambient_soft(
                p, ww, hh, t=t_wall, intro=ip, from_file=self._from_file
            )

            self._draw_intro_veil(p, ww, hh, ip)

            if not self._from_file:
                self._draw_zone_a_brand_synthetic(p, g, intro=ip, t_wall=t_wall)

            self._draw_footer_scrim(p, g, from_file=self._from_file, fk=fk)

            self._draw_footer_text_and_progress(p, g, fk=fk)
        finally:
            p.end()


def _center_splash_on_anchor_or_primary(
    splash: QWidget,
    app: QApplication,
    anchor_hwnd: int | None,
) -> None:
    """게임/런처 HWND가 있으면 그 모니터 작업 영역 중앙, 없으면 primary 작업 영역 중앙."""

    scr: QScreen | None = None
    if anchor_hwnd is not None:
        r = get_window_outer_rect_screen(anchor_hwnd)
        if r is not None:
            cx = int((r[0] + r[2]) // 2)
            cy = int((r[1] + r[3]) // 2)
            try:
                scr = app.screenAt(QPoint(cx, cy))
            except Exception:
                scr = None
    if scr is None:
        try:
            scr = app.primaryScreen()
        except Exception:
            scr = None
    if scr is None:
        return
    try:
        ag = scr.availableGeometry()
        ww, hh = int(splash.width()), int(splash.height())
        x = int(ag.left() + max(0, (ag.width() - ww) // 2))
        y = int(ag.top() + max(0, (ag.height() - hh) // 2))
        splash.move(x, y)
    except Exception:
        pass


def create_startup_splash(
    app: QApplication,
    pipela_mod: object | None = None,
) -> PipelaSplashProgress | None:
    raw = os.environ.get("PIPELA_NO_SPLASH", "0").strip().lower()
    if raw in ("1", "true", "yes", "on", "y"):
        return None
    from_file = os.path.isfile(PIPELA_SPLASH_IMAGE_PATH)
    pm = _splash_pixmap()
    if pm.isNull():
        return None

    splash = PipelaSplashProgress(pm, from_file=from_file)
    hwnd_anchor = splash_placement_anchor_hwnd(pipela_mod) if pipela_mod is not None else None
    _center_splash_on_anchor_or_primary(splash, app, hwnd_anchor)
    splash.show()
    splash.start_animation()
    app.processEvents()
    return splash


def finish_startup_splash(
    app: QApplication,
    splash: PipelaSplashProgress | None,
    main_window: object | None,
) -> None:
    """Animate gauge to completion, drain events, close splash."""
    _ = main_window
    if splash is None:
        return
    try:
        splash.set_loading_message("실행 준비 완료…")
    except Exception:
        pass
    try:
        splash.set_loading_target(1.0)
    except Exception:
        pass

    deadline = time.perf_counter() + 4.5
    while time.perf_counter() < deadline:
        try:
            app.processEvents()
        except Exception:
            break
        try:
            if splash.load_anim_quiescent():
                break
        except Exception:
            break

    try:
        splash.close()
        splash.deleteLater()
    except Exception:
        pass