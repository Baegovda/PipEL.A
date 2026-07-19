"""클라·템플릿·DPI 한 줄(리치 텍스트) — 제어창·게임 상단 스트립 공통."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QFont, QTextDocument
from PyQt6.QtWidgets import QLabel

from pipela_qt import theme as T
from pipela_qt.ui_adaptive import root_font_pt, scale_px_h, scale_px_v


@dataclass(frozen=True)
class ResolutionHtmlPalette:
    muted: str
    val: str
    warn: str
    sep: str
    note: str


CONTROL_RESOLUTION_PALETTE = ResolutionHtmlPalette(
    muted=T.FG_DIM,
    val=T.ACCENT,
    warn=T.STATUS_WARN,
    sep=T.BORDER_HAIR,
    note=T.FG_MUTED,
)

STRIP_RESOLUTION_PALETTE = ResolutionHtmlPalette(
    muted=T.STRIP_FG_MUTED,
    val=T.STRIP_ACCENT,
    warn=T.STATUS_WARN,
    sep=T.STRIP_BORDER,
    note=T.STRIP_FG_MUTED,
)


def _windows_dpi_parts(m, hwnd) -> tuple[int, int]:
    """
    창이 올라간 **모니터**의 배율(shcore.GetDpiForMonitor effective).
    hwnd가 없으면 Pipela 제어창 HWND(`pipela_qt_control_win_hwnd`)로 그 모니터를 쓴다.
    반환: (퍼센트 정수, DPI 정수).
    """
    try:
        ref = int(hwnd) if hwnd else getattr(m, "pipela_qt_control_win_hwnd", None)
        if ref:
            d = int(m.get_dpi_for_monitor_containing_window(ref))
        else:
            d = int(m.get_native_window_dpi(None))
    except Exception:
        d = 96
    try:
        pct = int(round(d / 96.0 * 100.0))
    except Exception:
        pct = 100
    return pct, d


def _res_metrics_sep(p: ResolutionHtmlPalette) -> str:
    return f'<span style="color:{p.sep};">·</span>'


def _res_lbl_muted(t: str, p: ResolutionHtmlPalette) -> str:
    return f'<span style="color:{p.muted};">{t}</span>'


def _res_lbl_val(t: str, p: ResolutionHtmlPalette) -> str:
    return f'<span style="color:{p.val}; font-weight:600;">{t}</span>'


def _res_lbl_warn(t: str, p: ResolutionHtmlPalette) -> str:
    return f'<span style="color:{p.warn}; font-weight:600;">{t}</span>'


def _res_tpl_note_html(p: ResolutionHtmlPalette) -> str:
    return (
        f'<span style="color:{p.note}; font-size:92%; font-weight:400;">'
        f"&nbsp;(1440p)"
        f"</span>"
    )


def _dpi_fragment_html(m, hwnd, p: ResolutionHtmlPalette) -> str:
    """% 와 유효 DPI 정수는 한 덩어리로 붙여 표시(구분 `·` 없음, 좁은 공백만)."""
    pct, d = _windows_dpi_parts(m, hwnd)
    _tight = "&#8239;"
    return (
        f"{_res_lbl_muted('DPI', p)}&nbsp;{_res_lbl_val(f'{pct}%', p)}{_tight}"
        f"{_res_lbl_val(str(d), p)}"
    )


def resolution_main_and_dpi_html(
    m,
    p: ResolutionHtmlPalette,
) -> tuple[str, str]:
    """(클라·템플릿 등 본문 HTML, DPI HTML). 오류 시 (한 덩어리, '')."""
    sep = _res_metrics_sep(p)
    try:
        target_hwnd = m.refresh_target_hwnd_if_needed()
        if target_hwnd:
            if m.is_window_minimized(target_hwnd):
                return (
                    f"{_res_lbl_warn('게임 최소화', p)}{sep}"
                    f"{_res_lbl_muted('캡처·매칭 대기', p)}",
                    _dpi_fragment_html(m, target_hwnd, p),
                )
            sz = m.get_window_size(target_hwnd)
            if sz:
                gw, gh = sz
                r = float(gh) / float(m.BASE_HEIGHT)
                note = _res_tpl_note_html(p)
                return (
                    f"{_res_lbl_muted('클라', p)}&nbsp;{_res_lbl_val(f'{gw}×{gh}', p)}{sep}"
                    f"{_res_lbl_muted('템플릿', p)}&nbsp;{_res_lbl_val(f'{r:.3f}', p)}{note}",
                    _dpi_fragment_html(m, target_hwnd, p),
                )
        _luh = m.refresh_smart_updater_hwnd_if_needed()
        if _luh and not m.is_window_minimized(_luh):
            sz_l = m.get_window_size(_luh)
            if sz_l:
                lw, lh = sz_l
                r = float(lh) / float(m.BASE_HEIGHT)
                note = _res_tpl_note_html(p)
                return (
                    f"{_res_lbl_muted('클라', p)}&nbsp;{_res_lbl_val(f'{lw}×{lh}', p)}{sep}"
                    f"{_res_lbl_muted('템플릿', p)}&nbsp;{_res_lbl_val(f'{r:.3f}', p)}{note}",
                    _dpi_fragment_html(m, _luh, p),
                )
            return (
                f"{_res_lbl_muted('연결', p)}&nbsp;{_res_lbl_val('런처만', p)}",
                _dpi_fragment_html(m, _luh, p),
            )
        return (
            f"{_res_lbl_muted('이터널시티 창 없음', p)}",
            _dpi_fragment_html(m, None, p),
        )
    except Exception:
        return (
            f'<span style="color:{p.muted};">해상도 정보 오류</span>',
            "",
        )


def resolution_block_html(m, p: ResolutionHtmlPalette) -> str:
    """클라·템플릿·DPI 지표를 한 줄(리치 텍스트)로 표시."""
    sep = _res_metrics_sep(p)
    main, dpi = resolution_main_and_dpi_html(m, p)
    if not dpi:
        return main
    return f"{main}{sep}{dpi}"


def resolution_block_content_key(m) -> tuple:
    """`resolution_block_html` 결과가 바뀔 때만 달라지는 값 — HTML 문자열 없이 저비용 비교용."""
    try:
        target_hwnd = m.refresh_target_hwnd_if_needed()
        if target_hwnd:
            if m.is_window_minimized(target_hwnd):
                return ("gmin", int(target_hwnd))
            sz = m.get_window_size(target_hwnd)
            if sz:
                gw, gh = int(sz[0]), int(sz[1])
                r = round(float(gh) / float(m.BASE_HEIGHT), 4)
                try:
                    d = int(m.get_dpi_for_monitor_containing_window(int(target_hwnd)))
                except Exception:
                    d = 96
                return ("game", int(target_hwnd), gw, gh, r, d)
        _luh = m.refresh_smart_updater_hwnd_if_needed()
        if _luh and not m.is_window_minimized(_luh):
            sz_l = m.get_window_size(_luh)
            if sz_l:
                lw, lh = int(sz_l[0]), int(sz_l[1])
                r = round(float(lh) / float(m.BASE_HEIGHT), 4)
                try:
                    d = int(m.get_dpi_for_monitor_containing_window(int(_luh)))
                except Exception:
                    d = 96
                return ("l_sz", int(_luh), lw, lh, r, d)
            try:
                d = int(m.get_dpi_for_monitor_containing_window(int(_luh)))
            except Exception:
                d = 96
            return ("l_only", int(_luh), d)
        ref = getattr(m, "pipela_qt_control_win_hwnd", None)
        try:
            if ref:
                d = int(m.get_dpi_for_monitor_containing_window(int(ref)))
            else:
                d = int(m.get_native_window_dpi(None))
        except Exception:
            d = 96
        return ("none", d)
    except Exception:
        return ("err",)


_RES_FIT_LETTER_SPACING_EM: tuple[float, ...] = (
    0.03,
    0.02,
    0.01,
    0.0,
    -0.015,
    -0.03,
    -0.045,
    -0.06,
    -0.075,
    -0.09,
)
_RES_FIT_BASE_DESIGN_PT = 10.5
_RES_FIT_MIN_DESIGN_PT = 3.85
_RES_FIT_ABSOLUTE_MIN_DESIGN_PT = 1.55
_RES_FIT_PT_STEP = 0.35
_RES_FIT_PT_STEP_FINE = 0.12


def _res_line_wrap(inner_html: str, letter_spacing_em: float) -> str:
    l = float(letter_spacing_em)
    return (
        '<div style="white-space:nowrap; '
        f'letter-spacing:{l:.3f}em;">{inner_html}</div>'
    )


def _measure_res_rich_width(font: QFont, html: str) -> float:
    doc = QTextDocument()
    doc.setDefaultFont(font)
    doc.setHtml(html)
    doc.setTextWidth(-1)
    return float(doc.idealWidth())


def apply_resolution_rich_label_fit(
    lbl: QLabel,
    m,
    avail_css_px: float,
    *,
    palette: ResolutionHtmlPalette,
    design_scale: float = 1.0,
    block_html: str | None = None,
) -> None:
    """가용 폭 안에 **항상 한 줄** — 필요 시 pt·자간 축소.

    ``block_html`` 이 있으면 ``resolution_main_and_dpi_html`` 재호출 없이 그대로 피팅(호출부에서
    ``resolution_block_html`` 과 짝지을 것).
    """
    if block_html is not None:
        single_inner = block_html
        if not single_inner:
            return
    else:
        main, dpi = resolution_main_and_dpi_html(m, palette)
        if not main and not dpi:
            return
        sep = _res_metrics_sep(palette)
        single_inner = f"{main}{sep}{dpi}" if dpi else main
    avail = max(40.0, float(avail_css_px))
    avail_fit = max(40.0, avail - float(scale_px_v(4)))
    avail_i = max(40, int(round(avail)))
    _rf = round(float(root_font_pt()), 3)
    _fit_k = (single_inner, avail_i, round(float(design_scale), 4), _rf)
    if getattr(lbl, "_pipela_res_fit_cache_k", None) == _fit_k:
        return
    # 가용 폭은 **부모(스트립의 _res_fill 등)에서 넘긴 값** — lbl.width() 로 잡지 말 것(자기축소 루프).
    try:
        lbl.setMaximumWidth(avail_i)
    except Exception:
        pass
    fit_limit = max(24.0, avail_fit * 0.99)
    scale = (float(root_font_pt()) / 11.0) * float(design_scale)
    base_pt = _RES_FIT_BASE_DESIGN_PT * scale
    coarse_floor = _RES_FIT_MIN_DESIGN_PT * scale
    abs_floor = _RES_FIT_ABSOLUTE_MIN_DESIGN_PT * scale
    chosen_pt = float(abs_floor)
    chosen_lsem = float(_RES_FIT_LETTER_SPACING_EM[-1])
    found = False
    pt = float(base_pt)
    # 넓으면 기본 pt·첫 자간에서 이미 맞는 경우가 많음 — QTextDocument 측정 횟수 대폭 감소
    try:
        _f_quick = QFont(lbl.font())
        _f_quick.setPointSizeF(pt)
        _w_quick = _res_line_wrap(single_inner, float(_RES_FIT_LETTER_SPACING_EM[0]))
        if _measure_res_rich_width(_f_quick, _w_quick) <= fit_limit:
            chosen_pt, chosen_lsem = pt, float(_RES_FIT_LETTER_SPACING_EM[0])
            found = True
    except Exception:
        pass
    while not found and pt >= coarse_floor - 1e-9:
        for lsem in _RES_FIT_LETTER_SPACING_EM:
            fnt = QFont(lbl.font())
            fnt.setPointSizeF(pt)
            wrapped = _res_line_wrap(single_inner, lsem)
            if _measure_res_rich_width(fnt, wrapped) <= fit_limit:
                chosen_pt, chosen_lsem = pt, float(lsem)
                found = True
                break
        if found:
            break
        pt -= _RES_FIT_PT_STEP
    if not found:
        pt = min(float(base_pt), coarse_floor)
        while pt >= abs_floor - 1e-9:
            for lsem in _RES_FIT_LETTER_SPACING_EM:
                fnt = QFont(lbl.font())
                fnt.setPointSizeF(pt)
                wrapped = _res_line_wrap(single_inner, lsem)
                if _measure_res_rich_width(fnt, wrapped) <= fit_limit:
                    chosen_pt, chosen_lsem = pt, float(lsem)
                    found = True
                    break
            if found:
                break
            pt -= _RES_FIT_PT_STEP_FINE
    if not found:
        chosen_pt = float(abs_floor)
        chosen_lsem = float(_RES_FIT_LETTER_SPACING_EM[-1])
    fnt = QFont(lbl.font())
    fnt.setPointSizeF(chosen_pt)
    lbl.setFont(fnt)
    lbl.setText(_res_line_wrap(single_inner, chosen_lsem))
    try:
        mh = lbl.fontMetrics().height()
        lbl.setMinimumHeight(max(scale_px_v(8), mh))
    except Exception:
        pass
    lbl._pipela_res_fit_cache_k = _fit_k


def apply_resolution_rich_label_fixed(
    lbl: QLabel,
    *,
    block_html: str,
    design_scale: float = 1.0,
) -> None:
    """스트립 등 — 적응형 축소 없이 고정 pt·자간 0으로 한 줄 리치 텍스트."""
    single_inner = (block_html or "").strip()
    if not single_inner:
        return
    _rf = round(float(root_font_pt()), 3)
    _fit_k = ("fixed", single_inner, round(float(design_scale), 4), _rf)
    if getattr(lbl, "_pipela_res_fit_cache_k", None) == _fit_k:
        return
    try:
        lbl.setMaximumWidth(16777215)
    except Exception:
        pass
    scale = (float(root_font_pt()) / 11.0) * float(design_scale)
    chosen_pt = float(_RES_FIT_BASE_DESIGN_PT * scale)
    fnt = QFont(lbl.font())
    fnt.setPointSizeF(chosen_pt)
    lbl.setFont(fnt)
    lbl.setText(_res_line_wrap(single_inner, 0.0))
    try:
        mh = lbl.fontMetrics().height()
        lbl.setMinimumHeight(max(scale_px_v(8), mh))
    except Exception:
        pass
    lbl._pipela_res_fit_cache_k = _fit_k
