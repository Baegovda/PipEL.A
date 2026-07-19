"""Kill Counter 패널(플로터 본문) — 창 논리 H(및 기준 W)에 비례한 보조 배율.

제어 창 폭 연동인 `scale_px` / `scaled_design_pt` / `T.spt` 위에 한 겹 더 곱하여
플로터를 줄였을 때 섹션·글자가 함께 줄어든다.

가로 스케일(`kc_viewport_width_scale`)은 **세로 스케일과 동일**하게 두어,
창 **가로만** 줄일 때 패딩·글자 크기 등이 줄어들지 않게 한다."""


from __future__ import annotations

import math

from pipela_qt.ui_adaptive import scale_px_h, scale_px_v, scaled_design_pt

# 앱 초기 폭 근처(도킹 기본) — 같은 해상도 밀도에서 참조 크기.
KC_BODY_REF_WIDTH = 440.0
KC_BODY_REF_HEIGHT = 740.0
_KC_ISO_LO = 0.42
_KC_ISO_HI = 1.92

# Matches minimum used in ``kc_viewport_spt`` and KC shimmer toolbar fonts.
KC_VIEWPORT_MIN_PT = 6.25
KC_VIEWPORT_TOOLBAR_MAX_PT = 22.0
# 킬 카운터 창: ``kc_viewport_design_pt_eff_v`` / ``kc_viewport_spt_v`` 로 들어가는 디자인 pt 에만 적용 (여백 px 는 비례 안 함)
KC_WINDOW_FONT_SCALE = 0.49


def kc_viewport_wh_valid(w: int, h: int) -> tuple[int, int]:
    aw = max(120, min(980, int(w)))
    ah = max(260, min(1360, int(h)))
    return aw, ah


def kc_viewport_iso_scale(w: int, h: int) -> float:
    """가로·세로 비율의 기하 평균, 클램프 — 과도 확대·축소 방지."""
    aw, ah = kc_viewport_wh_valid(w, h)
    rx = float(aw) / KC_BODY_REF_WIDTH
    ry = float(ah) / KC_BODY_REF_HEIGHT
    iso = math.sqrt(max(1e-4, rx * ry))
    return max(_KC_ISO_LO, min(_KC_ISO_HI, iso))


def kc_viewport_width_scale(w: int, h: int) -> float:
    """가로 폭(w) 변화만 반영 — 가로 리사이즈가 세로 미트릭에 영향을 주지 않게."""
    aw, _ah = kc_viewport_wh_valid(w, h)
    rx = float(aw) / KC_BODY_REF_WIDTH
    return max(_KC_ISO_LO, min(_KC_ISO_HI, rx))


def kc_viewport_height_scale(w: int, h: int) -> float:
    """세로 높이(h) 변화만 반영 — 가로 리사이즈가 세로 폰트/패딩에 영향 주지 않게."""
    _aw, ah = kc_viewport_wh_valid(w, h)
    ry = float(ah) / KC_BODY_REF_HEIGHT
    return max(_KC_ISO_LO, min(_KC_ISO_HI, ry))


def kc_viewport_wh_from_widget_chain(owner: object | None) -> tuple[int, int]:
    """``KillCounterPanel._kc_vw`` / ``_kc_vh`` 등 조상 위젯에 심긴 참조 크기 후보를 탐색."""
    depth = 0
    p: object | None = owner
    while p is not None and depth < 32:
        depth += 1
        vw = getattr(p, "_kc_vw", None)
        vh = getattr(p, "_kc_vh", None)
        if (
            isinstance(vw, int)
            and isinstance(vh, int)
            and vw >= 120
            and vh >= 260
        ):
            return vw, vh
        p = getattr(p, "parentWidget", lambda: None)()
    return kc_viewport_wh_valid(440, 740)


def kc_viewport_iso_from_widget_chain(owner: object | None) -> float:
    w, h = kc_viewport_wh_from_widget_chain(owner)
    return kc_viewport_iso_scale(w, h)


def kc_viewport_width_scale_from_widget_chain(owner: object | None) -> float:
    w, h = kc_viewport_wh_from_widget_chain(owner)
    return kc_viewport_width_scale(w, h)


def kc_viewport_height_scale_from_widget_chain(owner: object | None) -> float:
    w, h = kc_viewport_wh_from_widget_chain(owner)
    return kc_viewport_height_scale(w, h)


def kc_viewport_px(iso_scale: float, design_px: float, *, lo: int = 1, hi: int = 320) -> int:
    raw = scale_px_v(float(design_px), lo=lo, hi=hi)
    v = int(round(float(raw) * float(iso_scale)))
    return max(int(lo), min(int(hi), v))


def kc_viewport_px_h(ws: float, design_px: float, *, lo: int = 1, hi: int = 320) -> int:
    raw = scale_px_h(float(design_px), lo=lo, hi=hi)
    v = int(round(float(raw) * float(ws)))
    return max(int(lo), min(int(hi), v))


def kc_viewport_px_v(vs: float, design_px: float, *, lo: int = 1, hi: int = 320) -> int:
    raw = scale_px_v(float(design_px), lo=lo, hi=hi)
    v = int(round(float(raw) * float(vs)))
    return max(int(lo), min(int(hi), v))


def kc_viewport_px_loose(
    iso_scale: float, design_px: float, *, lo: int = 1, hi: int = 400,
) -> int:
    """일부 구간에서는 상한 완화(그래프·가로 라벨 등)."""
    raw = scale_px_v(float(design_px), lo=lo, hi=hi)
    v = int(round(float(raw) * float(iso_scale)))
    return max(int(lo), min(int(hi), v))


def kc_viewport_design_pt_eff(iso_scale: float, design_pt: float) -> float:
    return float(scaled_design_pt(float(design_pt))) * float(iso_scale)


def kc_viewport_design_pt_eff_v(vs: float, design_pt: float) -> float:
    return float(
        scaled_design_pt(float(design_pt) * float(KC_WINDOW_FONT_SCALE)),
    ) * float(vs)


def kc_viewport_spt(iso_scale: float, design_pt: float) -> str:
    v = max(KC_VIEWPORT_MIN_PT, float(kc_viewport_design_pt_eff(iso_scale, design_pt)))
    s = f"{v:.4g}"
    return f"{s}pt"


def kc_viewport_spt_v(
    vs: float, design_pt: float, *, clamp_min_pt: bool = True,
) -> str:
    v = float(kc_viewport_design_pt_eff_v(vs, design_pt))
    if clamp_min_pt:
        v = max(KC_VIEWPORT_MIN_PT, v)
    s = f"{v:.4g}"
    return f"{s}pt"


def kc_viewport_apply_qss_px(iso_scale: float, design_px_block: float) -> int:
    """QSS 블록에 쓰이는 순수 디자인 픽셀(예: `settings_chrome` 캘린더)."""
    v = float(design_px_block) * float(iso_scale)
    return max(5, min(36, int(round(v))))
