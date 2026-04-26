"""UI 타이포·간격 공통 기준 — 루트 pt, 제어창 폭 연동 스케일.

제어창 논리 너비(`set_typography_layout_width_px`)가 주어지면 폰트·자간·`scale_px` 간격이 함께 연동된다.
패널·테마·스트립은 `pipela_qt.ui_adaptive` 를 통해 동일 규칙을 참조하는 것을 권장한다.
"""

from __future__ import annotations

_DESIGN_REF_PT = 11.0
_root_pt: float = _DESIGN_REF_PT
# 제어창 폭(논리 px). None이면 너비 연동 없음(배율 1.0).
_layout_width_px: float | None = None
_REF_LAYOUT_W = 400.0
# 실제 제어창 폭이 매우 좁을 때도 스케일이 반영되도록 하한을 낮춤.
_LAYOUT_W_CLAMP = (220.0, 720.0)
_WIDTH_SCALE_RANGE = (0.58, 1.18)
_LETTER_PX_RANGE = (-0.95, 0.65)


def set_root_font_pt(pt: float) -> None:
    global _root_pt
    _root_pt = max(8.0, min(24.0, float(pt)))


def root_font_pt() -> float:
    return _root_pt


def set_typography_layout_width_px(w: int | None) -> None:
    """제어창 등 기준 너비 — `spt`·자간 배율에 사용. None이면 비활성."""
    global _layout_width_px
    if w is None or int(w) <= 0:
        _layout_width_px = None
    else:
        _layout_width_px = float(int(w))


def typography_layout_width_px() -> float | None:
    return _layout_width_px


def _layout_width_clamped() -> float | None:
    if _layout_width_px is None:
        return None
    lo, hi = _LAYOUT_W_CLAMP
    return max(lo, min(hi, float(_layout_width_px)))


def typography_width_scale() -> float:
    """1.0 @ ~400px 논리 너비. 좁을수록 <1, 넓을수록 >1."""
    w = _layout_width_clamped()
    if w is None:
        return 1.0
    r = float(w) / _REF_LAYOUT_W
    lo, hi = _WIDTH_SCALE_RANGE
    return max(lo, min(hi, r))


def control_action_label_pt_factor() -> float:
    """기능 그리드 라벨 전용 — `typography_width_scale` 외 추가 축소(좁은 2열 셀 대응)."""
    w = _layout_width_clamped()
    if w is None or w >= _REF_LAYOUT_W:
        return 1.0
    t = (float(w) - _LAYOUT_W_CLAMP[0]) / max(1.0, _REF_LAYOUT_W - _LAYOUT_W_CLAMP[0])
    return max(0.84, min(1.0, 0.84 + 0.16 * t))


def letter_spacing_qss() -> str:
    """QSS `letter-spacing` (px). 좁은 폭에서 약간 타이트, 넓으면 살짝 넓게."""
    w = _layout_width_clamped()
    if w is None:
        return "0px"
    t = (float(w) - _REF_LAYOUT_W) / _REF_LAYOUT_W
    px = t * 0.72
    lo, hi = _LETTER_PX_RANGE
    px = max(lo, min(hi, px))
    return f"{px:.2f}px"


def spt(design_pt: float) -> str:
    """디자인 시점 pt(기준 11) → 루트 pt·레이아웃 너비 배율 반영 stylesheet 문자열."""
    v = float(design_pt) * _root_pt / _DESIGN_REF_PT * typography_width_scale()
    s = f"{v:.3g}"
    return f"{s}pt"


def scaled_design_pt(design_pt: float) -> float:
    """`spt()`와 동일 배율의 연속 pt — `QFont.setPointSizeF`, 문서 여백 등."""
    return float(design_pt) * _root_pt / _DESIGN_REF_PT * typography_width_scale()


def scale_px(design_px: float, *, lo: int = 1, hi: int = 160) -> int:
    """디자인 논리 px × `typography_width_scale()` → 정수 px (QSS·setFixedWidth 등)."""
    v = int(round(float(design_px) * typography_width_scale()))
    return max(int(lo), min(int(hi), v))


def qss_pad_vh(vert: float, horiz: float) -> str:
    """QSS padding: `상하 좌우` (px)."""
    return f"{scale_px(vert)}px {scale_px(horiz)}px"


def qss_pad_all(same: float) -> str:
    return f"{scale_px(same)}px"


def qss_pad_trbl(top: float, right: float, bottom: float, left: float) -> str:
    """QSS padding 네 값 순서: top right bottom left."""
    return (
        f"{scale_px(top)}px {scale_px(right)}px {scale_px(bottom)}px {scale_px(left)}px"
    )
