"""Flame Trigger 메인 액션 버튼 — 발동 시 프리즘 유리 하이라이트 애니메이션."""

from __future__ import annotations

import math

from PyQt6.QtCore import QEvent, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QColor,
    QEnterEvent,
    QLinearGradient,
    QPaintEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import QPushButton, QStyle, QStyleOptionButton, QStylePainter

from pipela_core.display_timing import ui_anim_tick_ms_for_qwidget
from pipela_qt import theme as T
from pipela_qt.ui_adaptive import (
    action_button_qss_padding,
    control_action_label_pt_factor,
    letter_spacing_qss,
    scale_px_v,
    spt,
)


def _parse_hex_rgb(h: str) -> tuple[int, int, int]:
    s = (h or "").strip().lstrip("#")
    if len(s) >= 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return (45, 212, 191)


def _main_btn_radius_px() -> float:
    r = (T.MAIN_GLASS_BTN_RADIUS or "").replace("px", "").strip()
    try:
        v = int(round(float(r)))
    except ValueError:
        v = 10
    return max(4.0, float(scale_px_v(v)))


class FlameTriggerGlassButton(QPushButton):
    """기능 on + 발동 시 커스텀 페인트(프리즘 스윕), 그 외는 QSS `st_off` / `st_on` / `st_emit` 규칙과 동기."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._prism = False
        self._phase = 0.0
        self._qss: tuple[str, str, str] = ("", "", "")
        self._en = False
        self._em = False
        self._anim = QTimer(self)
        self._anim.timeout.connect(self._tick_prism)

    def _tick_prism(self) -> None:
        self._phase = (self._phase + 0.045) % (math.tau * 2.0)
        self.update()

    def set_flame_glass(
        self,
        enabled: bool,
        emitting: bool,
        st_off: str,
        st_on: str,
        st_emit: str,
    ) -> None:
        self._qss = (st_off, st_on, st_emit)
        en = bool(enabled)
        em = en and bool(emitting)
        prev_prism = self._prism
        use_prism = en and em
        self._prism = use_prism
        if use_prism:
            self.setStyleSheet(self._minimal_label_qss())
            if not self._anim.isActive():
                self._anim.setInterval(max(20, int(ui_anim_tick_ms_for_qwidget(self))))
                self._anim.start()
            self.update()
        else:
            self._anim.stop()
            if not en:
                self.setStyleSheet(st_off)
            else:
                self.setStyleSheet(st_on)
            self.update()
        if prev_prism != use_prism:
            self.updateGeometry()

    def _minimal_label_qss(self) -> str:
        _fpt = spt(10.0 * control_action_label_pt_factor())
        _tls = letter_spacing_qss()
        _pad = action_button_qss_padding()
        return (
            f"QPushButton {{"
            f" background: transparent; color: {T.FG}; border: none; padding: {_pad};"
            f" font-weight: 600; font-size: {_fpt}; letter-spacing: {_tls};"
            f"}}"
        )

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if self._prism and not self._anim.isActive():
            self._anim.setInterval(max(20, int(ui_anim_tick_ms_for_qwidget(self))))
            self._anim.start()

    def hideEvent(self, e) -> None:
        self._anim.stop()
        super().hideEvent(e)

    def event(self, e: QEvent) -> bool:
        if e.type() in (
            QEvent.Type.Enter,
            QEvent.Type.Leave,
        ):
            if self._prism:
                self.update()
        return super().event(e)

    def paintEvent(self, e: QPaintEvent) -> None:
        if not self._prism:
            return super().paintEvent(e)
        p = QStylePainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        r = self.rect()
        x, y, w, h = float(r.x()), float(r.y()), float(r.width()), float(r.height())
        rr = _main_btn_radius_px()
        path = QPainterPath()
        path.addRoundedRect(x + 0.5, y + 0.5, w - 1.0, h - 1.0, rr, rr)
        p.setClipPath(path)

        sunken = bool(opt.state & QStyle.StateFlag.State_Sunken)
        hover = bool(
            self.underMouse() and (opt.state & QStyle.StateFlag.State_Enabled)
        ) and not sunken

        if sunken:
            p.fillPath(path, QColor(T.MAIN_GLASS_PRESSED_BG))
            p.setClipping(False)
            p.setPen(QPen(QColor(T.MAIN_GLASS_PRESSED_BORDER), max(1, scale_px_v(1) // 2 or 1)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setClipping(True)
        else:
            # --- 베이스: 발동 유리(emit) 그라데이션
            g0 = QLinearGradient(0.0, y, 0.0, y + h)
            if hover:
                g0.setColorAt(0.0, QColor(180, 255, 245, 88))
                g0.setColorAt(0.45, QColor(32, 110, 102, 210))
                g0.setColorAt(1.0, QColor(8, 58, 54, 248))
            else:
                g0.setColorAt(0.0, QColor(120, 245, 230, 100))
                g0.setColorAt(0.4, QColor(22, 96, 88, 200))
                g0.setColorAt(1.0, QColor(6, 48, 44, 240))
            p.fillPath(path, g0)

            # --- 프리즘 스윕(대각 띠)
            a = self._phase
            k = max(w, h) * 1.35
            cx, cy = x + w * 0.5, y + h * 0.5
            c, sn = math.cos(a), math.sin(a)
            x0, y0 = cx + c * k, cy + sn * k
            x1, y1 = cx - c * k, cy - sn * k
            # 흰 띠 대신 크로매틱 애버레이션(채널 분리) 틴트 스윕
            ph = (self._phase / (math.tau * 2.0)) % 1.0

            def _sweep_grad(angle: float, hue_bias: float, a_peak: int) -> QLinearGradient:
                cc, ss = math.cos(angle), math.sin(angle)
                sx0, sy0 = cx + cc * k, cy + ss * k
                sx1, sy1 = cx - cc * k, cy - ss * k
                g = QLinearGradient(sx0, sy0, sx1, sy1)
                # 띠 외곽은 투명 유지, 중앙만 무지개 틴트(화이트 금지)
                g.setColorAt(0.0, QColor(0, 0, 0, 0))
                g.setColorAt(0.38, QColor(0, 0, 0, 0))
                g.setColorAt(0.62, QColor(0, 0, 0, 0))
                g.setColorAt(1.0, QColor(0, 0, 0, 0))

                hue = (ph + hue_bias) % 1.0
                c48 = QColor.fromHsvF((hue - 0.03) % 1.0, 0.92, 1.0, float(a_peak) / 255.0 * 0.55)
                c50 = QColor.fromHsvF(hue, 0.98, 1.0, float(a_peak) / 255.0)
                c52 = QColor.fromHsvF((hue + 0.03) % 1.0, 0.92, 1.0, float(a_peak) / 255.0 * 0.55)
                g.setColorAt(0.48, c48)
                g.setColorAt(0.50, c50)
                g.setColorAt(0.52, c52)
                return g

            p.save()
            try:
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
            except Exception:
                pass
            # 3-pass RGB split 느낌(각도/색상 약간씩 다르게) — 알파는 화이트 블룸 방지로 낮게
            p.fillPath(path, _sweep_grad(a + 0.0, 0.00, 72))
            p.fillPath(path, _sweep_grad(a + 0.08, 0.08, 58))
            p.fillPath(path, _sweep_grad(a - 0.08, -0.08, 58))
            p.restore()

            # --- 이리데슨(얇은 색 띠, 위상 엇갈림)
            a2 = a * 0.6 + 1.7
            c2, s2 = math.cos(a2), math.sin(a2)
            i0, j0 = cx + c2 * k, cy + s2 * k
            i1, j1 = cx - c2 * k, cy - s2 * k
            iris = QLinearGradient(i0, j0, i1, j1)
            iris.setColorAt(0.0, QColor(80, 255, 230, 0))
            iris.setColorAt(0.42, QColor(160, 220, 255, 0))
            # 중앙 하이라이트를 near-white 대신 분산 톤(phase-driven)으로
            ph_i = (self._phase / (math.tau * 2.0)) % 1.0
            iris_mid = QColor.fromHsvF((ph_i + 0.18) % 1.0, 0.85, 1.0, 0.16)
            iris.setColorAt(0.5, iris_mid)
            iris.setColorAt(0.58, QColor(255, 210, 190, 0))
            iris.setColorAt(1.0, QColor(100, 255, 220, 0))
            p.save()
            p.setOpacity(0.75)
            p.fillPath(path, iris)
            p.restore()

            # --- RGB 크로마(색상환 대각 스윕, 저알파 — 크로마틱 필름 느낌)
            a3 = -a * 0.52 + 2.1
            c3, s3 = math.cos(a3), math.sin(a3)
            u0, v0 = cx + c3 * k, cy + s3 * k
            u1, v1 = cx - c3 * k, cy - s3 * k
            chroma = QLinearGradient(u0, v0, u1, v1)
            ph = (self._phase / (math.tau * 2.0)) % 1.0
            # 더 무지갯빛/프리즘 느낌: 스톱을 촘촘히 + 채도/알파 상향(텍스트 가독성은 유지)
            stops = (0.0, 0.12, 0.24, 0.36, 0.5, 0.64, 0.76, 0.88, 1.0)
            for i, t in enumerate(stops):
                hue = (ph + t * 0.96 + i * 0.018) % 1.0
                sat = 0.56 + 0.26 * math.sin(a * 0.95 + t * 4.6 + float(i) * 0.15)
                sat = min(0.94, max(0.50, sat))
                shimmer = 0.5 + 0.5 * math.sin(a * 1.35 + t * 6.0 + float(i) * 0.55)
                alpha = 0.09 + 0.13 * float(shimmer)
                alpha = min(0.28, max(0.075, alpha))
                chroma.setColorAt(
                    t,
                    QColor.fromHsvF(float(hue), float(sat), 1.0, float(alpha)),
                )
            # additive 합성 + RGB 분리 패스로 크로마틱 애버레이션 느낌 강화
            p.save()
            try:
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
            except Exception:
                pass
            # base pass
            p.fillPath(path, chroma)
            # split passes: 살짝 다른 벡터/위상으로 2회 덧칠
            for j, (da, op) in enumerate(((0.32, 0.62), (-0.27, 0.55)), start=1):
                aj = a3 + float(da)
                cj, sj = math.cos(aj), math.sin(aj)
                uu0, vv0 = cx + cj * k, cy + sj * k
                uu1, vv1 = cx - cj * k, cy - sj * k
                chroma2 = QLinearGradient(uu0, vv0, uu1, vv1)
                ph2 = (ph + 0.07 * float(j)) % 1.0
                for i, t in enumerate(stops):
                    hue2 = (ph2 + t * 0.98 + i * 0.02) % 1.0
                    sat2 = 0.58 + 0.28 * math.sin(a * 1.02 + t * 4.9 + float(i) * 0.18 + float(j) * 0.6)
                    sat2 = min(0.97, max(0.52, sat2))
                    shimmer2 = 0.5 + 0.5 * math.sin(a * 1.42 + t * 6.4 + float(i) * 0.6 + float(j))
                    alpha2 = (0.07 + 0.11 * float(shimmer2)) * float(op)
                    alpha2 = min(0.22, max(0.045, alpha2))
                    chroma2.setColorAt(
                        t,
                        QColor.fromHsvF(float(hue2), float(sat2), 1.0, float(alpha2)),
                    )
                p.fillPath(path, chroma2)
            p.restore()

            # --- 상단 림 라이트(유리 모서리)
            rim = QLinearGradient(0.0, y, 0.0, y + h * 0.55)
            # near-white 림이 과하게 보일 수 있어 약한 틴트 + 낮은 알파로 블룸 방지
            ph_r = (self._phase / (math.tau * 2.0)) % 1.0
            rim_c0 = QColor.fromHsvF((ph_r + 0.10) % 1.0, 0.35, 1.0, 0.11)
            rim.setColorAt(0.0, rim_c0)
            rim.setColorAt(0.35, QColor(0, 0, 0, 0))
            rim.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillPath(path, rim)

            ar, ag, ab = _parse_hex_rgb(T.ACCENT)
            p.setClipping(False)
            br_c = (
                QColor(200, 255, 250, 120)
                if hover
                else QColor(150, 250, 238, 118)
            )
            p.setPen(
                QPen(
                    br_c,
                    max(1, int(round(scale_px_v(1)))),
                ),
            )
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setPen(
                QPen(
                    QColor(ar, ag, ab, 55),
                    max(1, scale_px_v(1) // 2 or 1),
                ),
            )
            _irr = max(0.0, rr - 1.0)
            inner_path = QPainterPath()
            inner_path.addRoundedRect(
                QRectF(x + 1.0, y + 1.0, w - 2.0, h - 2.0),
                _irr,
                _irr,
            )
            p.drawPath(inner_path)
        p.setClipping(False)
        p.drawControl(QStyle.ControlElement.CE_PushButtonLabel, opt)

    def sizeHint(self):
        return super().sizeHint()
