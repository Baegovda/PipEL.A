"""UI 타이포·간격 공통 기준 — 루트 pt, 제어창 폭(가로)·앵커 클라 높이(세로) 분리 스케일.

- 가로: ``set_typography_layout_width_px`` → ``typography_width_scale``, ``scale_px_h``
- 세로(폰트 pt, 상하 패딩 등): ``set_typography_layout_height_px`` → ``typography_height_scale``, ``scale_px_v``

``scale_px`` 는 하위 호환 별칭으로 ``scale_px_h`` 와 동일(가로 연동). 세로 의미 호출부는 ``scale_px_v`` 사용.
"""

from __future__ import annotations

from typing import Any

_DESIGN_REF_PT = 11.0
_root_pt: float = _DESIGN_REF_PT
# 제어창 폭(논리 px). None이면 너비 연동 없음(배율 1.0).
_layout_width_px: float | None = None
_REF_LAYOUT_W = 400.0
_LAYOUT_W_CLAMP = (220.0, 720.0)
_WIDTH_SCALE_RANGE = (0.58, 1.18)
_LETTER_PX_RANGE = (-0.95, 0.65)

# 앵커 클라이언트 논리 높이(px). None이면 세로 연동 없음(배율 1.0).
_layout_height_px: float | None = None
_REF_LAYOUT_H = 900.0
_LAYOUT_H_CLAMP = (360.0, 1200.0)
_HEIGHT_SCALE_RANGE = (0.58, 1.18)


def set_root_font_pt(pt: float) -> None:
    global _root_pt
    _root_pt = max(8.0, min(24.0, float(pt)))


def root_font_pt() -> float:
    return _root_pt


def set_typography_layout_width_px(w: int | None) -> None:
    """제어창 등 기준 너비 — 가로 픽셀·자간 등에 사용. None이면 비활성."""
    global _layout_width_px
    if w is None or int(w) <= 0:
        _layout_width_px = None
    else:
        _layout_width_px = float(int(w))


def typography_layout_width_px() -> float | None:
    return _layout_width_px


def set_typography_layout_height_px(h: int | None) -> None:
    """앵커 클라이언트 논리 높이 — 폰트·세로 픽셀·상하 패딩에 사용. None이면 비활성."""
    global _layout_height_px
    if h is None or int(h) <= 0:
        _layout_height_px = None
    else:
        _layout_height_px = float(int(h))


def typography_layout_height_px() -> float | None:
    return _layout_height_px


def _layout_width_clamped() -> float | None:
    if _layout_width_px is None:
        return None
    lo, hi = _LAYOUT_W_CLAMP
    return max(lo, min(hi, float(_layout_width_px)))


def _layout_height_clamped() -> float | None:
    if _layout_height_px is None:
        return None
    lo, hi = _LAYOUT_H_CLAMP
    return max(lo, min(hi, float(_layout_height_px)))


def typography_width_scale() -> float:
    """1.0 @ ~400px 논리 너비. 좁을수록 <1, 넓을수록 >1."""
    w = _layout_width_clamped()
    if w is None:
        return 1.0
    r = float(w) / _REF_LAYOUT_W
    lo, hi = _WIDTH_SCALE_RANGE
    return max(lo, min(hi, r))


def typography_height_scale() -> float:
    """1.0 @ ~900px 앵커 클라 논리 높이. 작을수록 <1, 클수록 >1."""
    h = _layout_height_clamped()
    if h is None:
        return 1.0
    r = float(h) / _REF_LAYOUT_H
    lo, hi = _HEIGHT_SCALE_RANGE
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
    """디자인 시점 pt → 루트 pt·앵커 클라 높이 배율 반영 stylesheet 문자열."""
    v = float(design_pt) * _root_pt / _DESIGN_REF_PT * typography_height_scale()
    s = f"{v:.3g}"
    return f"{s}pt"


def scaled_design_pt(design_pt: float) -> float:
    """`spt()`와 동일 배율의 연속 pt — `QFont.setPointSizeF`, 문서 여백 등."""
    return float(design_pt) * _root_pt / _DESIGN_REF_PT * typography_height_scale()


def scale_px_h(design_px: float, *, lo: int = 1, hi: int = 160) -> int:
    """디자인 논리 px × 가로 배율 — 좌우 마진·min-width·가로 간격 등."""
    v = int(round(float(design_px) * typography_width_scale()))
    return max(int(lo), min(int(hi), v))


def scale_px_v(design_px: float, *, lo: int = 1, hi: int = 160) -> int:
    """디자인 논리 px × 세로 배율 — 상하 마진·min-height·세로 간격·아이콘 변(세로 기준) 등."""
    v = int(round(float(design_px) * typography_height_scale()))
    return max(int(lo), min(int(hi), v))


def scale_px(design_px: float, *, lo: int = 1, hi: int = 160) -> int:
    """Deprecated alias: 가로 연동 ``scale_px_h`` (하위 호환). 세로는 ``scale_px_v``."""
    return scale_px_h(design_px, lo=lo, hi=hi)


def qss_pad_vh(vert: float, horiz: float) -> str:
    """QSS padding: `상하 좌우` (px)."""
    return f"{scale_px_v(vert)}px {scale_px_h(horiz)}px"


def qss_pad_all(same: float) -> str:
    return f"{scale_px_v(same)}px"


def qss_pad_trbl(top: float, right: float, bottom: float, left: float) -> str:
    """QSS padding 네 값 순서: top right bottom left."""
    return (
        f"{scale_px_v(top)}px {scale_px_h(right)}px "
        f"{scale_px_v(bottom)}px {scale_px_h(left)}px"
    )


_KC_BTN_PT_STEP = 0.3
_KC_BTN_LSPX_LADDER: tuple[float, ...] = (
    0.0,
    -0.22,
    -0.45,
    -0.7,
    -0.95,
    -1.2,
    -1.5,
    -1.85,
    -2.2,
    -2.6,
    -3.05,
    -3.5,
    -4.0,
)


def fit_qpushbutton_text_width_qss(
    button: Any,
    text: str,
    *,
    horizontal_padding_px: int,
    base_design_pt: float = 9.25,
    min_design_pt: float = 4.05,
    min_measure_width_px: int | None = None,
    base_pt_eff: float | None = None,
    min_pt_eff: float | None = None,
) -> tuple[str, str]:
    """``QPushButton`` 가로 안에 `text` 가 들어가도록 `font-size`·`letter-spacing` (QSS) 페어를 고른다."""
    if (base_pt_eff is None) ^ (min_pt_eff is None):
        raise ValueError("base_pt_eff and min_pt_eff must both be set or both omitted")

    def _initial_qss_pt() -> str:
        if base_pt_eff is not None:
            return f"{float(base_pt_eff):.2f}pt"
        return spt(base_design_pt)

    if not (text and str(text).strip()):
        return (_initial_qss_pt(), letter_spacing_qss())
    try:
        w_btn = int(button.width()) if button is not None else 0
    except Exception:
        w_btn = 0
    if min_measure_width_px is not None:
        try:
            w_btn = max(w_btn, int(min_measure_width_px))
        except (TypeError, ValueError):
            pass
    if w_btn <= 2:
        return (_initial_qss_pt(), letter_spacing_qss())
    hpad = max(0, int(horizontal_padding_px))
    w_avail = w_btn - 2 * hpad - 2
    w_avail = max(6, w_avail)
    mtxt = str(text)
    n = max(0, len(mtxt) - 1)
    from PyQt6.QtGui import QFont, QFontMetrics
    from pipela_qt.qt_fonts import app_default_qfont

    def _inter_char_letter_spacing_px() -> float:
        s = (letter_spacing_qss() or "0px").strip()
        if s.endswith("px"):
            try:
                return float(s[:-2].strip())
            except ValueError:
                return 0.0
        return 0.0

    def _width_at(pt: float, lspx: float) -> int:
        f = app_default_qfont(11, QFont.Weight.DemiBold)
        f.setPointSizeF(float(pt))
        fm = QFontMetrics(f)
        w = int(fm.horizontalAdvance(mtxt))
        if n > 0:
            if abs(lspx) < 1e-9:
                w += int(round(_inter_char_letter_spacing_px() * n))
            else:
                w += int(round(float(lspx) * n))
        return w

    if base_pt_eff is not None:
        min_root = max(3.0, float(min_pt_eff))
        pt = float(base_pt_eff)
    else:
        min_root = max(3.0, float(scaled_design_pt(min_design_pt)))
        pt = float(scaled_design_pt(base_design_pt))
    lsem_def = letter_spacing_qss()
    while pt + 1e-6 >= min_root:
        for lspx in _KC_BTN_LSPX_LADDER:
            if _width_at(float(pt), float(lspx)) <= w_avail:
                if lspx == 0.0:
                    lsq = lsem_def
                else:
                    lsq = f"{lspx:.2f}px"
                return (f"{float(pt):.2f}pt", lsq)
        next_pt = float(
            int(max(min_root, pt - _KC_BTN_PT_STEP) * 1000) / 1000.0,
        )
        if next_pt >= pt - 1e-9:
            break
        pt = next_pt
    lsq0 = f"{_KC_BTN_LSPX_LADDER[-1]:.2f}px"
    return (f"{min_root:.2f}pt", lsq0)
