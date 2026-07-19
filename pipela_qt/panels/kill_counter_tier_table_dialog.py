"""킬 카운터 등급·몬스터킬 구간 표 — 카드 팝업 + 테이블."""

from __future__ import annotations

import sys
from math import sin
from typing import Any

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QFontMetrics, QGuiApplication
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from pipela_core.display_timing import ui_anim_tick_ms_for_pipela
from pipela_core.kill_counter_tier_colors import (
    KILL_COUNTER_TIER_HONORIFIC_FG_HEX,
    kill_counter_honorific_key,
)
from pipela_core.kill_counter_tier_data import get_kill_counter_rank_table_rows
from pipela_core.win32_window_ops import win32_set_window_topmost
from pipela_qt import theme as T
from pipela_qt.card_popup_shell import CardFramelessDialog, center_card_popup
from pipela_qt.dpi import win32_dpi_scale_for_hwnd
from pipela_qt.qt_dock_anchor import resolve_game_only_anchor_hwnd
from pipela_qt.ui_adaptive import scale_px_h, scale_px_v

# 비모달 표시 — 같은 버튼/링크로 다시 누르면 닫기
_tier_table_dialog_open: CardFramelessDialog | None = None
# ``show()`` 를 다음 이벤트 루프로 미루는 동안 같은 핸들러가 재입력되는 것을 막음
_tier_dialog_show_pending: bool = False


def _kc_scale_70(px: int) -> int:
    """Kill Counter typography change: shrink to 70% of current size."""
    try:
        v = int(round(float(px) * 0.7))
    except Exception:
        v = int(px)
    return max(6, v)


def _tier_table_singleton_clear() -> None:
    global _tier_table_dialog_open, _tier_dialog_show_pending
    _tier_table_dialog_open = None
    _tier_dialog_show_pending = False


def _tier_table_stylesheet(
    *,
    cell_pv: int,
    cell_ph: int,
    hdr_pv: int,
    hdr_ph: int,
    body_pt: int,
) -> str:
    br = scale_px_v(8)
    return (
        f"QTableWidget {{"
        f"background: {T.PANEL_BG};"
        f"alternate-background-color: {T.SURFACE};"
        f"color: {T.FG};"
        f"gridline-color: {T.BORDER_HAIR};"
        f"font-family: {T.FONT_CSS_UI};"
        f"font-size: {body_pt}px;"
        f"border: 1px solid {T.BORDER_HAIR};"
        f"border-radius: {br}px;"
        f"}}"
        f"QTableWidget::item {{ padding: {cell_pv}px {cell_ph}px; }}"
        f"QHeaderView::section {{"
        f"background: {T.SURFACE};"
        f"color: {T.FG_MUTED};"
        f"font-weight: 600;"
        f"padding: {hdr_pv}px {hdr_ph}px;"
        f"border: none;"
        f"border-bottom: 1px solid {T.BORDER};"
        f"}}"
    )


def _parse_theme_hex6(h: str) -> QColor:
    s = (h or "").strip().lstrip("#")
    if len(s) >= 6:
        try:
            return QColor(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return QColor(61, 212, 201)


_WOW_FG_CACHE: dict[str, QColor] = {
    k: QColor(v) for k, v in KILL_COUNTER_TIER_HONORIFIC_FG_HEX.items()
}


def _tier_row_wow_fg(title: str) -> QColor:
    k = kill_counter_honorific_key(title)
    return _WOW_FG_CACHE.get(k, QColor(T.FG))


def _tier_subtle_row_bg(fg: QColor) -> QColor:
    """패널 배경 위에 호칭 색을 아주 약하게 깔아 행 구분."""
    pb = _parse_theme_hex6(T.PANEL_BG)
    t = 0.13
    return QColor(
        int(fg.red() * t + pb.red() * (1.0 - t)),
        int(fg.green() * t + pb.green() * (1.0 - t)),
        int(fg.blue() * t + pb.blue() * (1.0 - t)),
    )


def _blend_color_under_alpha_overlay(base: QColor, top: QColor) -> QColor:
    """top 에 알파가 있을 때 base 위에 얹은 RGB."""
    ta = top.alpha() / 255.0
    if ta <= 0.0:
        return QColor(base)
    inv = 1.0 - ta
    return QColor(
        min(255, int(top.red() * ta + base.red() * inv)),
        min(255, int(top.green() * ta + base.green() * inv)),
        min(255, int(top.blue() * ta + base.blue() * inv)),
    )


def _resolve_current_tier_row_index(pipela_mod: Any | None, n_rows: int) -> int | None:
    if pipela_mod is None or n_rows <= 0:
        return None
    try:
        n1 = pipela_mod._kill_counter_progress_n1_or_none()
        if n1 is None:
            return None
        st = pipela_mod._kill_counter_tier_state_for_n1(int(n1))
        if st is None:
            return None
        r = int(st["num"])
        if 0 <= r < n_rows:
            return r
    except Exception:
        return None
    return None


def _start_current_tier_row_pulse(
    table: QTableWidget,
    row: int,
    owner: QWidget,
    pipela_mod: Any | None,
    *,
    row_base_bg: QColor,
    row_fg_wow: QColor,
) -> QTimer | None:
    """현재 등급 행 — 호칭 색 글자 유지 + 베이스 행 위에 청록 알파 펄스."""
    col_count = int(table.columnCount())
    if col_count <= 0:
        return None
    accent = _parse_theme_hex6(T.ACCENT)
    phase = [0.0]

    def refresh() -> None:
        t = float(phase[0])
        w = (sin(t) + 1.0) * 0.5
        a_bg = int(36 + w * 100)
        c = QColor(accent)
        c.setAlpha(a_bg)
        pulsed = _blend_color_under_alpha_overlay(row_base_bg, c)
        bg_br = QBrush(pulsed)
        fg_br = QBrush(row_fg_wow)
        base_font = table.font()
        for col in range(col_count):
            it = table.item(row, col)
            if it is None:
                continue
            it.setBackground(bg_br)
            it.setForeground(fg_br)
            f = QFont(base_font)
            f.setWeight(QFont.Weight.DemiBold)
            it.setFont(f)

    refresh()
    tm = QTimer(owner)
    _ms = ui_anim_tick_ms_for_pipela(pipela_mod)
    tm.setInterval(_ms)

    def _tick() -> None:
        # sin 한 주기 짧게 — 틱 간격(`_ms`)에 맞춰 위상 증가량 보정
        phase[0] += 0.7 * (float(_ms) / 48.0)
        refresh()

    tm.timeout.connect(_tick)
    tm.start()
    return tm


def _tier_game_client_inner_height_qt(pipela_mod: Any | None) -> int | None:
    """게임 클라이언트 세로 크기(Qt 논리 px 근사). 실패 시 None."""
    if pipela_mod is None or sys.platform != "win32":
        return None
    hwnd = resolve_game_only_anchor_hwnd(pipela_mod)
    if not hwnd:
        return None
    rect = pipela_mod.get_window_rect(int(hwnd))
    if not rect:
        return None
    _l, t, r, b = (int(x) for x in rect)
    if r <= _l or b <= t:
        return None
    h_phys = b - t
    try:
        sc = float(win32_dpi_scale_for_hwnd(pipela_mod, int(hwnd)))
    except Exception:
        sc = 1.0
    if sc <= 0.01:
        sc = 1.0
    return int(round(float(h_phys) / sc))


def _center_tier_popup_on_game_client(dlg: CardFramelessDialog, pipela_mod: Any) -> bool:
    """이터널시티 클라이언트 영역 정중앙(화면 좌표 → Qt 논리). 성공 시 True."""
    if sys.platform != "win32":
        return False
    hwnd = resolve_game_only_anchor_hwnd(pipela_mod)
    if not hwnd:
        return False
    rect = pipela_mod.get_window_rect(int(hwnd))
    if not rect:
        return False
    l, t, r, b = (int(x) for x in rect)
    if r <= l or b <= t:
        return False
    cx_phys = (l + r) // 2
    cy_phys = (t + b) // 2
    try:
        sc = float(win32_dpi_scale_for_hwnd(pipela_mod, int(hwnd)))
    except Exception:
        sc = 1.0
    if sc <= 0.01:
        sc = 1.0
    cx = int(round(cx_phys / sc))
    cy = int(round(cy_phys / sc))
    dlg.adjustSize()
    fg = dlg.frameGeometry()
    fg.moveCenter(QPoint(cx, cy))
    dlg.move(fg.topLeft())
    return True


def refresh_kill_counter_tier_table_typography_if_open() -> None:
    """`refresh_pipela_typography` — 열려 있는 등급 구간표의 테이블 QSS·기본 행 높이만 재스케일."""
    w = _tier_table_dialog_open
    if w is None:
        return
    try:
        if not w.isVisible():
            return
    except RuntimeError:
        return
    table = w.findChild(QTableWidget)
    if table is None:
        return
    compact = w.property("_pipela_tier_compact") is True
    vh = table.verticalHeader()
    if compact:
        table.setStyleSheet(
            _tier_table_stylesheet(
                cell_pv=scale_px_v(3),
                cell_ph=scale_px_h(8),
                hdr_pv=scale_px_v(4),
                hdr_ph=scale_px_h(8),
                body_pt=_kc_scale_70(scale_px_v(10)),
            ),
        )
        vh.setDefaultSectionSize(scale_px_v(22))
    else:
        _pv = scale_px_v(5)
        _ph = scale_px_h(10)
        _hv = scale_px_v(6)
        _hh = scale_px_h(10)
        table.setStyleSheet(
            _tier_table_stylesheet(
                cell_pv=_pv,
                cell_ph=_ph,
                hdr_pv=_hv,
                hdr_ph=_hh,
                body_pt=_kc_scale_70(scale_px_v(11)),
            ),
        )
        vh.setDefaultSectionSize(scale_px_v(26))


def show_kill_counter_tier_table_dialog(
    parent: QWidget | None,
    *,
    pipela_mod: Any | None = None,
) -> None:
    global _tier_table_dialog_open, _tier_dialog_show_pending
    w = _tier_table_dialog_open
    if w is not None:
        try:
            if w.isVisible():
                w.close()
                return
        except RuntimeError:
            _tier_table_dialog_open = None

    if _tier_dialog_show_pending:
        return

    rows = get_kill_counter_rank_table_rows()
    if pipela_mod is None and parent is not None:
        pipela_mod = getattr(parent, "_m", None)
    _game_h_qt = _tier_game_client_inner_height_qt(pipela_mod)
    # Qt 부모를 킬카 창에 두면 Win32에서 모달처럼 부모가 클릭·포커스를 못 받는 경우가 있음.
    # 위치만 parent 기준으로 잡고, 창은 독립 + 비활성 표시로 토글(아이콘 재클릭) 가능하게 함.
    dlg = CardFramelessDialog(
        None,
        title="킬 카운터 · 등급 구간 표",
        modal=False,
    )
    # 게임 클라(전체·보더리스)가 포그라운드로 남으면 일반 Dialog 는 바로 뒤로 밀려 «잠깐 보였다 사라짐»처럼 보임.
    dlg.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    dlg.setWindowModality(Qt.WindowModality.NonModal)
    # 부모 None 인 독립 창 — 클릭 직후 동기 show 는 같은 입력이 새 창으로 전달되며
    # 깜빡이거나 바로 닫히는 경우가 있어 표시는 다음 틱으로 미룸.
    # WA_ShowWithoutActivating 는 Win32 에서 포커스/활성과 맞물려 즉시 사라짐처럼 보일 수 있어 쓰지 않음.
    lay = dlg.content_layout()

    _cell_pad_v = scale_px_v(5)
    _cell_pad_h = scale_px_h(10)
    _hdr_pad_v = scale_px_v(6)
    _hdr_pad_h = scale_px_h(10)

    table = QTableWidget()
    table.setColumnCount(5)
    table.setHorizontalHeaderLabels(
        ("단계", "구간명", "구간 시작", "다음 상한", "구간 폭"),
    )
    table.setRowCount(len(rows))
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideNone)
    table.verticalHeader().setVisible(False)
    vh = table.verticalHeader()
    vh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    vh.setDefaultSectionSize(scale_px_v(26))
    table.setAlternatingRowColors(False)
    table.setShowGrid(True)
    table.setStyleSheet(
        _tier_table_stylesheet(
            cell_pv=_cell_pad_v,
            cell_ph=_cell_pad_h,
            hdr_pv=_hdr_pad_v,
            hdr_ph=_hdr_pad_h,
            body_pt=_kc_scale_70(scale_px_v(11)),
        ),
    )
    dlg.setProperty("_pipela_tier_compact", False)

    tier_row_fgs: list[QColor] = []
    tier_row_bgs: list[QColor] = []
    for r, row in enumerate(rows):
        nc = row.get("next_cap")
        pt = int(row["point"])
        delta = (int(nc) - pt) if nc is not None else None
        vals = (
            str(int(row["num"])),
            str(row.get("title") or "—"),
            f"{pt:,}",
            f"{int(nc):,}" if nc is not None else "—",
            f"{delta:,}" if delta is not None else "—",
        )
        title = str(row.get("title") or "")
        fg_c = _tier_row_wow_fg(title)
        bg_c = _tier_subtle_row_bg(fg_c)
        tier_row_fgs.append(fg_c)
        tier_row_bgs.append(bg_c)
        for c, text in enumerate(vals):
            it = QTableWidgetItem(text)
            it.setFlags(Qt.ItemFlag.ItemIsEnabled)
            it.setForeground(QBrush(fg_c))
            it.setBackground(QBrush(bg_c))
            table.setItem(r, c, it)

    hh = table.horizontalHeader()
    hh.setMinimumSectionSize(scale_px_h(44))
    table.resizeColumnsToContents()
    _num_min = scale_px_h(112)
    for c in (2, 3, 4):
        table.setColumnWidth(c, max(table.columnWidth(c), _num_min))
    table.setColumnWidth(0, max(table.columnWidth(0), scale_px_h(52)))

    # 구간명: Stretch 제거 — 글자 폭·패딩에 맞춘 고정 폭(가장 긴 행·헤더 반영).
    fm = QFontMetrics(table.font())
    _name_pad = _cell_pad_h * 2 + scale_px_h(14)
    _name_w = fm.horizontalAdvance("구간명")
    for row in rows:
        _name_w = max(_name_w, fm.horizontalAdvance(str(row.get("title") or "—")))
    table.setColumnWidth(1, _name_w + _name_pad)

    hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
    for c in (2, 3, 4):
        hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
    hh.setStretchLastSection(True)

    _tw = sum(table.columnWidth(i) for i in range(5))
    table.setMinimumWidth(max(scale_px_h(480), _tw + scale_px_h(24)))

    # 세로: 작업 영역 높이의 대부분을 테이블에 쓰고, 51행이 안 들어가면 패딩·글자를
    # 한 단계 더 줄인 뒤 행 높이를 균등 분배해 스크롤을 없앤다(극소 높이만 스크롤).
    n = table.rowCount()
    _fudge = scale_px_v(10)

    scr = None
    if parent is not None:
        scr = QGuiApplication.screenAt(parent.mapToGlobal(parent.rect().center()))
    if scr is None:
        scr = QGuiApplication.primaryScreen()
    _avail_h = int(scr.availableGeometry().height()) if scr is not None else 900
    _cap_screen = max(0, _avail_h - scale_px_v(16))

    _reserved = (
        scale_px_v(18) * 2
        + scale_px_v(14) * 2
        + scale_px_v(30)
        + scale_px_v(12)
    )
    if _game_h_qt is not None and _game_h_qt >= scale_px_v(260):
        # 팝업 전체 높이 ≈ 게임 클라(여백 소량), 작업 영역 밖으로는 안 나가게 상한
        _max_dlg_h = max(scale_px_v(240), min(int(_game_h_qt) - scale_px_v(8), _cap_screen))
    else:
        _max_dlg_h = max(0, int(_avail_h * 0.97) - scale_px_v(8))
    _max_table_h = max(scale_px_v(220), _max_dlg_h - _reserved)

    def _hdr_and_rows() -> tuple[int, int]:
        table.resizeRowsToContents()
        hdr_w = table.horizontalHeader()
        fm_m = QFontMetrics(table.font())
        hdr_h = max(
            hdr_w.sizeHint().height(),
            fm_m.height() + scale_px_v(14),
            scale_px_v(34),
        )
        rsum = sum(table.rowHeight(r) for r in range(n))
        return hdr_h, rsum

    _hdr_h, _row_sum = _hdr_and_rows()
    _ideal = _hdr_h + _row_sum + _fudge

    if _ideal > _max_table_h:
        table.setStyleSheet(
            _tier_table_stylesheet(
                cell_pv=scale_px_v(3),
                cell_ph=scale_px_h(8),
                hdr_pv=scale_px_v(4),
                hdr_ph=scale_px_h(8),
                body_pt=_kc_scale_70(scale_px_v(10)),
            ),
        )
        dlg.setProperty("_pipela_tier_compact", True)
        vh.setDefaultSectionSize(scale_px_v(22))
        _hdr_h, _row_sum = _hdr_and_rows()
        _ideal = _hdr_h + _row_sum + _fudge

    # 게임 높이에 맞춘 여유가 있으면 행 높이를 늘려 테이블이 세로를 채움(기존 else 분기 재사용)
    if _game_h_qt is not None and _game_h_qt >= scale_px_v(260) and _ideal <= _max_table_h:
        _ideal = _max_table_h + 1

    if _ideal <= _max_table_h:
        table.setFixedHeight(_ideal)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    else:
        _slack = _max_table_h - _hdr_h - _fudge
        _abs_min = scale_px_v(14)
        if n <= 0 or _slack <= 0:
            table.setMinimumHeight(min(scale_px_v(260), _max_table_h))
            table.setMaximumHeight(_max_table_h)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            _per = _slack // n
            if _per >= _abs_min:
                vh.setDefaultSectionSize(_per)
                for r in range(n):
                    table.setRowHeight(r, _per)
                _fit = min(_hdr_h + n * _per + _fudge, _max_table_h)
                table.setFixedHeight(_fit)
                table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            else:
                vh.setDefaultSectionSize(_abs_min)
                for r in range(n):
                    table.setRowHeight(r, _abs_min)
                table.setMinimumHeight(min(scale_px_v(260), _max_table_h))
                table.setMaximumHeight(_max_table_h)
                table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    if _game_h_qt is not None and _game_h_qt >= scale_px_v(260):
        table.setFixedHeight(_max_table_h)

    lay.addWidget(table)

    cur_row = _resolve_current_tier_row_index(pipela_mod, n)
    _pulse: QTimer | None = None
    if cur_row is not None:
        _pulse = _start_current_tier_row_pulse(
            table,
            cur_row,
            dlg,
            pipela_mod,
            row_base_bg=tier_row_bgs[cur_row],
            row_fg_wow=tier_row_fgs[cur_row],
        )

        def _scroll_to_current() -> None:
            it0 = table.item(cur_row, 0)
            if it0 is not None:
                table.scrollToItem(it0, QAbstractItemView.ScrollHint.PositionAtCenter)

        QTimer.singleShot(0, _scroll_to_current)

    def _stop_tier_pulse(_=None) -> None:
        if _pulse is not None:
            _pulse.stop()

    dlg.finished.connect(_stop_tier_pulse)
    dlg.finished.connect(_tier_table_singleton_clear)

    _tier_table_dialog_open = dlg
    _tier_dialog_show_pending = True

    def _apply_tier_win32_topmost() -> None:
        if sys.platform != "win32":
            return
        try:
            hid = int(dlg.winId())
            if hid:
                win32_set_window_topmost(hid, True)
        except Exception:
            pass

    def _place_and_show_tier() -> None:
        global _tier_dialog_show_pending
        _tier_dialog_show_pending = False
        if _tier_table_dialog_open is not dlg:
            return
        try:
            if pipela_mod is None or not _center_tier_popup_on_game_client(dlg, pipela_mod):
                center_card_popup(dlg, parent)
            dlg.show()
            dlg.raise_()
            dlg.activateWindow()
            _apply_tier_win32_topmost()
        except RuntimeError:
            _tier_table_singleton_clear()

    def _defer_tier_raise() -> None:
        """게임이 첫 프레임 뒤 Z 를 다시 잡는 경우 대비 — 한 번 더 올림(포커스는 건드리지 않음)."""
        if _tier_table_dialog_open is not dlg:
            return
        try:
            if not dlg.isVisible():
                return
            dlg.raise_()
            _apply_tier_win32_topmost()
        except RuntimeError:
            pass

    QTimer.singleShot(0, _place_and_show_tier)
    QTimer.singleShot(160, _defer_tier_raise)
