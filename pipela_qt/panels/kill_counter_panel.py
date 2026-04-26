"""킬 카운터 패널 — 현재 킬·통계·랩·목표·일별. 스크롤 없이 한눈에 읽히는 카드·그리드 배치."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pipela_core.display_timing import display_tick_ms
from pipela_core.registry_config_snapshot import (
    get_registry_config_snapshot,
    sync_registry_snapshot_from_module,
)
from pipela_core.registry_snapshot_read import snapshot_bool, snapshot_int
from pipela_qt import theme as T
from pipela_qt.panels.settings_chrome import (
    panel_primary_button_qss,
    panel_secondary_button_qss,
    panel_toolbar_button_qss,
)
from pipela_qt.qt_capture import attach_kill_counter_region_toolbar
from pipela_qt.scrub_spinboxes import DragSpinBox
from pipela_qt.ui_adaptive import qss_pad_all, scale_px, scaled_design_pt
from pipela_qt.qt_fonts import app_default_qfont
from pipela_qt.typography_refresh_support import TypographyStyleBundle


# --- 타이포 토큰 (역할: 히어로 / 값 / 캡션 / 보조) ---
def _px_hero() -> str:
    return T.spt(22)


def _px_value() -> str:
    return T.spt(11)


def _px_subval() -> str:
    return T.spt(9.5)


def _px_caption() -> str:
    return T.spt(7.75)


def _px_tool() -> str:
    return T.spt(8.5)


class KillCounterPanel(QWidget):
    def __init__(self, pipela_mod, parent=None) -> None:
        super().__init__(parent)
        self._m = pipela_mod
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._typo = TypographyStyleBundle()
        # 일별 — 최대 줄 수(스크롤 없이 맞출 높이와 동일)
        self._daily_max_lines = 6
        self._last_sess_k = 0
        self._last_ocr_raw = ""
        self._last_sess_html: str | None = None
        self._last_daily_plain: str | None = None
        self._slow_tick_mono: float = 0.0

        root = QVBoxLayout(self)
        self._root = root
        root.setSpacing(scale_px(6))
        root.setContentsMargins(0, 0, 0, 0)

        # —— 상단: 타이틀 + 히어로 숫자 ——
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(scale_px(8))
        self._title_lbl = QLabel("Kill Counter")
        self._title_lbl.setStyleSheet(
            f"font-weight: 800; font-size: {T.spt(11.5)}; color: {T.FG_MUTED}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: 0.04em;",
        )
        self._typo.add(
            lambda w=self._title_lbl: w.setStyleSheet(
                f"font-weight: 800; font-size: {T.spt(11.5)}; color: {T.FG_MUTED}; "
                f"font-family: {T.FONT_CSS_UI}; letter-spacing: 0.04em;",
            ),
        )
        hero_box = QVBoxLayout()
        hero_box.setSpacing(0)
        hero_box.setContentsMargins(0, 0, 0, 0)
        cap = QLabel("현재 인식")
        cap.setAlignment(Qt.AlignmentFlag.AlignRight)
        cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 600; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        self._typo.add(
            lambda w=cap: w.setStyleSheet(
                f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 600; "
                f"font-family: {T.FONT_CSS_UI};",
            ),
        )
        self._prog_big = QLabel("—")
        self._prog_big.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self._prog_big.setStyleSheet(
            f"font-family: {T.FONT_CSS_UI}; font-size: {_px_hero()}; font-weight: 800; "
            f"color: {T.ACCENT}; letter-spacing: -0.02em;",
        )
        self._typo.add(
            lambda w=self._prog_big: w.setStyleSheet(
                f"font-family: {T.FONT_CSS_UI}; font-size: {_px_hero()}; font-weight: 800; "
                f"color: {T.ACCENT}; letter-spacing: -0.02em;",
            ),
        )
        head.addWidget(self._title_lbl, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        head.addStretch(1)
        hero_box.addWidget(cap)
        hero_box.addWidget(self._prog_big)
        head.addLayout(hero_box)
        root.addLayout(head)

        # —— 세션 + OCR (리치 한 줄) ——
        self._sess = QLabel()
        self._sess.setTextFormat(Qt.TextFormat.RichText)
        self._sess.setWordWrap(False)
        self._sess.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._sess.setText(self._fmt_sess_html(0, ""))
        self._typo.add(self._reapply_sess_rich)
        root.addWidget(self._sess)

        # —— ROI 툴바 ——
        self._kc_region_toolbar_btns = attach_kill_counter_region_toolbar(root, pipela_mod)

        # —— 상태 배너 ——
        st_fr = QFrame()
        self._st_fr = st_fr
        st_fr.setObjectName("pipelaKcStatusBanner")
        st_fr.setStyleSheet(
            f"QFrame#pipelaKcStatusBanner {{"
            f"  background: {T.SURFACE};"
            f"  border: none;"
            f"  border-left: 3px solid {T.ACCENT};"
            f"  border-radius: {T.RADIUS_SM};"
            f"  padding: {qss_pad_all(6)};"
            f"}}"
        )
        st_l = QVBoxLayout(st_fr)
        st_l.setContentsMargins(scale_px(8), scale_px(6), scale_px(8), scale_px(6))
        st_l.setSpacing(0)
        st_cap = QLabel("OCR / 세션")
        st_cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 700; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        self._typo.add(
            lambda w=st_cap: w.setStyleSheet(
                f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 700; "
                f"font-family: {T.FONT_CSS_UI};",
            ),
        )
        st_l.addWidget(st_cap)
        self._st_main = QLabel("")
        self._st_main.setWordWrap(True)
        self._st_main.setStyleSheet(
            f"color: {T.STATUS_OK}; font-size: {_px_subval()}; font-weight: 600; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        st_l.addWidget(self._st_main)
        root.addWidget(st_fr)

        # —— 롤링 (2×2 스탯 타일) ——
        root.addWidget(self._section_rule("최근 구간 누적"))
        roll_fr = self._make_card()
        rg = QGridLayout(roll_fr)
        rg.setContentsMargins(scale_px(8), scale_px(6), scale_px(8), scale_px(6))
        rg.setHorizontalSpacing(scale_px(6))
        rg.setVerticalSpacing(scale_px(4))
        self._r1, w1 = self._stat_pair("1시간", rg, 0, 0)
        self._r6, w2 = self._stat_pair("6시간", rg, 0, 1)
        self._r24, w3 = self._stat_pair("24시간", rg, 1, 0)
        self._rkph, w4 = self._stat_pair("24h 평균 / 시", rg, 1, 1)
        for t in (w1, w2, w3, w4):
            self._typo.add(t)
        root.addWidget(roll_fr)

        # —— 달력 요약 (한 줄 3칸) ——
        root.addWidget(self._section_rule("달력·집계"))
        cal_fr = self._make_card()
        ch = QHBoxLayout(cal_fr)
        ch.setContentsMargins(scale_px(8), scale_px(6), scale_px(8), scale_px(6))
        ch.setSpacing(scale_px(4))
        self._ctoday, a = self._mini_stat_column("오늘 (0시~)", ch)
        self._cweek, b = self._mini_stat_column("이번 주", ch)
        self._cmonth, c = self._mini_stat_column("이번 달", ch)
        for t in (a, b, c):
            self._typo.add(t)
        root.addWidget(cal_fr)

        # —— 동시간대 (헤더 + 값) ——
        root.addWidget(self._section_rule("동시간대 (어제 동시 · 오늘)"))
        dod_fr = self._make_card()
        dv = QVBoxLayout(dod_fr)
        dv.setContentsMargins(scale_px(8), scale_px(6), scale_px(8), scale_px(6))
        dv.setSpacing(scale_px(2))
        hdr = QHBoxLayout()
        hdr.setSpacing(0)
        for title in ("어제 동시", "오늘", "차이", "증감률"):
            lb = QLabel(title)
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb.setStyleSheet(
                f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 700; "
                f"font-family: {T.FONT_CSS_UI};",
            )
            self._typo.add(lambda w=lb: w.setStyleSheet(
                f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 700; "
                f"font-family: {T.FONT_CSS_UI};",
            ))
            hdr.addWidget(lb, 1)
        dv.addLayout(hdr)
        drow = QHBoxLayout()
        drow.setSpacing(0)
        self._dod_lbls: list[QLabel] = []
        for _ in range(4):
            lb = QLabel("—")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lb.setStyleSheet(
                f"color: {T.ACCENT}; font-size: {_px_value()}; font-weight: 800; "
                f"font-family: {T.FONT_CSS_UI};",
            )
            self._typo.add(
                lambda w=lb: w.setStyleSheet(
                    f"color: {T.ACCENT}; font-size: {_px_value()}; font-weight: 800; "
                    f"font-family: {T.FONT_CSS_UI};",
                ),
            )
            drow.addWidget(lb, 1)
            self._dod_lbls.append(lb)
        dv.addLayout(drow)
        root.addWidget(dod_fr)

        # —— 목표 (2열) ——
        root.addWidget(self._section_rule("다음 구간 · 초이노"))
        goal_fr = self._make_card()
        gg = QGridLayout(goal_fr)
        gg.setContentsMargins(scale_px(8), scale_px(6), scale_px(8), scale_px(6))
        gg.setHorizontalSpacing(scale_px(10))
        gg.setVerticalSpacing(scale_px(2))
        c1 = QLabel("구간")
        c1.setStyleSheet(
            f"color: {T.ACCENT}; font-size: {_px_caption()}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        c2 = QLabel("초이노")
        c2.setStyleSheet(
            f"color: {T.FG_MUTED}; font-size: {_px_caption()}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        self._typo.add(lambda w=c1: w.setStyleSheet(
            f"color: {T.ACCENT}; font-size: {_px_caption()}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI};",
        ))
        self._typo.add(lambda w=c2: w.setStyleSheet(
            f"color: {T.FG_MUTED}; font-size: {_px_caption()}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI};",
        ))
        gg.addWidget(c1, 0, 0)
        gg.addWidget(c2, 0, 1)
        self._gtier = QLabel("")
        self._gtr = QLabel("")
        self._grem = QLabel("")
        self._geta = QLabel("")
        self._gchp = QLabel("")
        self._gcrm = QLabel("")
        self._gcel = QLabel("")
        for i, lb in enumerate((self._gtier, self._gtr, self._grem, self._geta), start=1):
            lb.setWordWrap(True)
            lb.setStyleSheet(
                f"color: {T.FG}; font-size: {_px_subval()}; font-weight: 500; "
                f"font-family: {T.FONT_CSS_UI};",
            )
            self._typo.add(
                lambda w=lb: w.setStyleSheet(
                    f"color: {T.FG}; font-size: {_px_subval()}; font-weight: 500; "
                    f"font-family: {T.FONT_CSS_UI};",
                ),
            )
            gg.addWidget(lb, i, 0)
        for i, lb in enumerate((self._gchp, self._gcrm, self._gcel), start=1):
            lb.setWordWrap(True)
            lb.setStyleSheet(
                f"color: {T.FG_MUTED}; font-size: {_px_subval()}; font-weight: 500; "
                f"font-family: {T.FONT_CSS_UI};",
            )
            self._typo.add(
                lambda w=lb: w.setStyleSheet(
                    f"color: {T.FG_MUTED}; font-size: {_px_subval()}; font-weight: 500; "
                    f"font-family: {T.FONT_CSS_UI};",
                ),
            )
            gg.addWidget(lb, i, 1)
        root.addWidget(goal_fr)

        # —— 랩 ——
        root.addWidget(self._section_rule("랩 (세그먼트)"))
        lap_fr = self._make_card()
        lap_outer = QVBoxLayout(lap_fr)
        lap_outer.setContentsMargins(scale_px(8), scale_px(6), scale_px(8), scale_px(6))
        lap_outer.setSpacing(scale_px(4))
        # 제목과 스톱워치를 한 줄에 두면 좁은 도킹 폭에서 오른쪽 초·밀리초가 잘림 → 두 줄로 분리.
        lap_head = QVBoxLayout()
        lap_head.setSpacing(scale_px(2))
        lap_head.setContentsMargins(0, 0, 0, 0)
        lap_title_row = QHBoxLayout()
        lap_title_row.setContentsMargins(0, 0, 0, 0)
        lap_title_row.setSpacing(0)
        self._lap_title = QLabel("")
        self._lap_title.setStyleSheet(
            f"color: {T.FG}; font-size: {_px_value()}; font-weight: 800; font-family: {T.FONT_CSS_UI};",
        )
        self._typo.add(
            lambda w=self._lap_title: w.setStyleSheet(
                f"color: {T.FG}; font-size: {_px_value()}; font-weight: 800; font-family: {T.FONT_CSS_UI};",
            ),
        )
        self._lap_meta = QLabel("")
        self._lap_meta.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_subval()}; font-weight: 600; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        self._lap_meta.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        lap_title_row.addWidget(self._lap_title, 0)
        lap_title_row.addStretch(1)
        lap_meta_row = QHBoxLayout()
        lap_meta_row.setContentsMargins(0, 0, 0, 0)
        lap_meta_row.setSpacing(0)
        lap_meta_row.addStretch(1)
        lap_meta_row.addWidget(self._lap_meta, 0, Qt.AlignmentFlag.AlignRight)
        lap_head.addLayout(lap_title_row)
        lap_head.addLayout(lap_meta_row)
        lap_outer.addLayout(lap_head)
        lap_grid = QGridLayout()
        lap_grid.setHorizontalSpacing(scale_px(4))
        lap_grid.setVerticalSpacing(scale_px(2))
        self._lap_r1, t1 = self._lap_cell("랩 1H", lap_grid, 0, 0)
        self._lap_r6, t2 = self._lap_cell("랩 6H", lap_grid, 0, 1)
        self._lap_r12, t3 = self._lap_cell("랩 12H", lap_grid, 1, 0)
        self._lap_r24, t4 = self._lap_cell("랩 24H", lap_grid, 1, 1)
        for t in (t1, t2, t3, t4):
            self._typo.add(t)
        lap_outer.addLayout(lap_grid)
        lap_row = QHBoxLayout()
        lap_row.setSpacing(scale_px(4))
        self._lap_main = QPushButton()
        self._lap_main.clicked.connect(self._lap_toggle)
        lap_row.addWidget(self._lap_main, 1)
        self._lap_clear_btn = QPushButton("초기화")
        self._lap_clear_btn.setToolTip("랩 누적을 지금 기준으로 다시 시작")
        self._lap_clear_btn.clicked.connect(self._lap_clear)
        lap_row.addWidget(self._lap_clear_btn)
        self._lap_end_btn = QPushButton("종료")
        self._lap_end_btn.setToolTip("랩 세그먼트 종료")
        self._lap_end_btn.clicked.connect(self._lap_end)
        lap_row.addWidget(self._lap_end_btn)
        lap_outer.addLayout(lap_row)
        root.addWidget(lap_fr)

        # —— 날짜별 (콤팩트, 스크롤 없음) ——
        root.addWidget(self._section_rule("일별 (최근)"))
        daily_fr = self._make_card()
        dv_daily = QVBoxLayout(daily_fr)
        dv_daily.setContentsMargins(scale_px(6), scale_px(4), scale_px(6), scale_px(4))
        dv_daily.setSpacing(0)
        self._daily = QPlainTextEdit()
        self._daily.setReadOnly(True)
        self._daily.setObjectName("pipelaKcDaily")
        self._daily.document().setMaximumBlockCount(32)
        self._daily.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._daily.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._daily.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._daily.setFrameShape(QFrame.Shape.NoFrame)
        _df = app_default_qfont(9, QFont.Weight.Medium)
        _df.setPointSizeF(max(7.0, min(10.0, scaled_design_pt(8.5))))
        self._daily.setFont(_df)
        self._daily.setStyleSheet(
            f"QPlainTextEdit#pipelaKcDaily {{"
            f"  background: transparent; color: {T.METER_LABEL};"
            f"  font-family: {T.FONT_CSS_UI}; font-size: {T.spt(8.5)};"
            f"  padding: 0; selection-background-color: {T.ACCENT_SOFT};"
            f"}}"
        )
        self._typo.add(lambda: self._style_daily())
        dv_daily.addWidget(self._daily)
        root.addWidget(daily_fr)

        # —— 하단 도구 (한 행) ——
        tools_row = QHBoxLayout()
        tools_row.setSpacing(scale_px(6))
        self._sess_reset_btn = QPushButton("세션 킬 기준")
        self._sess_reset_btn.setToolTip("세션 누적 킬 기준을 초기화")
        self._sess_reset_btn.clicked.connect(self._reset_session)
        self._gscale_lbl = QLabel("그래프 %")
        self._gscale_lbl.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_tool()}; font-weight: 600; font-family: {T.FONT_CSS_UI};",
        )
        self._typo.add(
            lambda w=self._gscale_lbl: w.setStyleSheet(
                f"color: {T.METER_LABEL}; font-size: {_px_tool()}; font-weight: 600; "
                f"font-family: {T.FONT_CSS_UI};",
            ),
        )
        self._gscale = DragSpinBox()
        self._gscale.setRange(50, 300)
        self._gscale.setSingleStep(5)
        self._gscale.setFixedWidth(scale_px(64))
        self._gscale.valueChanged.connect(self._commit_gscale)
        tools_row.addWidget(self._sess_reset_btn, 0)
        tools_row.addStretch(1)
        tools_row.addWidget(self._gscale_lbl, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tools_row.addWidget(self._gscale, 0)
        root.addLayout(tools_row)

        self._inner_lay = root  # apply_scaled compatibility
        self._apply_kill_panel_button_styles()
        self._set_daily_height()
        self._sync_lap_meta_min_width()
        self._timer.setInterval(max(16, int(display_tick_ms())))
        self._timer.start()

    def _set_daily_height(self) -> None:
        ln = max(1, int(self._daily_max_lines))
        fm = self._daily.fontMetrics()
        h = int(fm.lineSpacing() * ln + scale_px(6))
        self._daily.setFixedHeight(h)
        self._daily.setMinimumHeight(h)
        self._daily.setMaximumHeight(h)

    def _style_daily(self) -> None:
        self._daily.setStyleSheet(
            f"QPlainTextEdit#pipelaKcDaily {{"
            f"  background: transparent; color: {T.METER_LABEL};"
            f"  font-family: {T.FONT_CSS_UI}; font-size: {T.spt(8.5)};"
            f"  padding: 0; selection-background-color: {T.ACCENT_SOFT};"
            f"}}"
        )

    @staticmethod
    def _make_card() -> QFrame:
        fr = QFrame()
        fr.setObjectName("pipelaKcCard")
        fr.setStyleSheet(
            f"QFrame#pipelaKcCard {{"
            f"  background: {T.CARD_BG};"
            f"  border: 1px solid {T.BORDER_HAIR};"
            f"  border-radius: {T.RADIUS_SM};"
            f"}}"
        )
        return fr

    def _section_rule(self, title: str) -> QLabel:
        """섹션 구분 — 한 줄 제목 + 머지 구분 느낌."""
        lb = QLabel(title)
        lb.setStyleSheet(
            f"color: {T.FG_MUTED}; font-size: {T.spt(8.25)}; font-weight: 800; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: 0.12em; margin-top: {scale_px(2)}px;",
        )
        self._typo.add(
            lambda w=lb: w.setStyleSheet(
                f"color: {T.FG_MUTED}; font-size: {T.spt(8.25)}; font-weight: 800; "
                f"font-family: {T.FONT_CSS_UI}; letter-spacing: 0.12em; margin-top: {scale_px(2)}px;",
            ),
        )
        return lb

    def _stat_pair(self, caption: str, grid: QGridLayout, r: int, c: int) -> tuple[QLabel, callable]:
        box = QFrame()
        box.setObjectName("pipelaKcTile")
        box.setStyleSheet(
            f"QFrame#pipelaKcTile {{"
            f"  background: {T.SURFACE}; border: 1px solid {T.BORDER_HAIR}; border-radius: 4px; padding: 0;"
            f"}}"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(scale_px(6), scale_px(4), scale_px(6), scale_px(4))
        v.setSpacing(scale_px(1))
        cap = QLabel(caption)
        cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 700; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val = QLabel("—")
        val.setStyleSheet(
            f"color: {T.FG}; font-size: {_px_value()}; font-weight: 800; font-family: {T.FONT_CSS_UI};",
        )
        v.addWidget(cap)
        v.addWidget(val)
        grid.addWidget(box, r, c)
        return val, (lambda: self._reapply_stat_tile_cap(cap, val))

    def _reapply_stat_tile_cap(self, cap: QLabel, val: QLabel) -> None:
        cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 700; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val.setStyleSheet(
            f"color: {T.FG}; font-size: {_px_value()}; font-weight: 800; font-family: {T.FONT_CSS_UI};",
        )

    def _mini_stat_column(self, title: str, row: QHBoxLayout) -> tuple[QLabel, callable]:
        w = QFrame()
        w.setObjectName("pipelaKcMini")
        w.setStyleSheet(
            f"QFrame#pipelaKcMini {{"
            f"  background: {T.SURFACE}; border: 1px solid {T.BORDER_HAIR};"
            f"  border-radius: 4px; padding: 0; min-width: 0; }}"
        )
        v = QVBoxLayout(w)
        v.setContentsMargins(scale_px(4), scale_px(4), scale_px(4), scale_px(4))
        v.setSpacing(scale_px(0))
        t = QLabel(title)
        t.setWordWrap(True)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 700; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val = QLabel("—")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val.setStyleSheet(
            f"color: {T.ACCENT}; font-size: {_px_subval()}; font-weight: 800; font-family: {T.FONT_CSS_UI};",
        )
        v.addWidget(t)
        v.addWidget(val)
        row.addWidget(w, 1)
        return val, (lambda: self._reapply_mini(t, val))

    def _reapply_mini(self, t: QLabel, val: QLabel) -> None:
        t.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 700; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val.setStyleSheet(
            f"color: {T.ACCENT}; font-size: {_px_subval()}; font-weight: 800; font-family: {T.FONT_CSS_UI};",
        )

    def _lap_cell(self, caption: str, grid: QGridLayout, r: int, c: int) -> tuple[QLabel, callable]:
        box = QFrame()
        box.setObjectName("pipelaKcLapCell")
        box.setStyleSheet(
            f"QFrame#pipelaKcLapCell {{"
            f"  background: {T.SURFACE}; border: 1px solid {T.BORDER_HAIR}; border-radius: 4px; }}"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(scale_px(4), scale_px(2), scale_px(4), scale_px(2))
        cap = QLabel(caption)
        cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 600; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val = QLabel("—")
        val.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_subval()}; font-weight: 700; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        v.addWidget(cap)
        v.addWidget(val)
        grid.addWidget(box, r, c)
        return val, (lambda: self._reapply_lap_cap(cap, val))

    def _reapply_lap_cap(self, cap: QLabel, val: QLabel) -> None:
        cap.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_caption()}; font-weight: 600; "
            f"font-family: {T.FONT_CSS_UI};",
        )
        val.setStyleSheet(
            f"color: {T.METER_LABEL}; font-size: {_px_subval()}; font-weight: 700; "
            f"font-family: {T.FONT_CSS_UI};",
        )

    def _reapply_sess_rich(self) -> None:
        _sh = self._fmt_sess_html(self._last_sess_k, self._last_ocr_raw)
        self._last_sess_html = _sh
        self._sess.setText(_sh)

    def _apply_kill_panel_button_styles(self) -> None:
        tq = panel_toolbar_button_qss()
        for b in getattr(self, "_kc_region_toolbar_btns", ()):
            b.setStyleSheet(tq)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        sq = panel_secondary_button_qss()
        self._lap_clear_btn.setStyleSheet(sq)
        self._lap_end_btn.setStyleSheet(sq)
        self._sess_reset_btn.setStyleSheet(sq)
        for b in (self._lap_clear_btn, self._lap_end_btn, self._sess_reset_btn):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lap_main.setStyleSheet(panel_primary_button_qss())
        self._lap_main.setCursor(Qt.CursorShape.PointingHandCursor)

    def _fmt_sess_html(self, sess: int, raw: str) -> str:
        esc = _html_esc
        r = (raw or "").strip() or "—"
        if len(r) > 20:
            r = r[:17] + "…"
        try:
            sn = f"{int(sess):,}"
        except (TypeError, ValueError):
            sn = "—"
        return (
            f"<span style='color:{T.METER_LABEL}; font-size:{_px_caption()}; font-weight:600;'>누적</span> "
            f"<span style='color:{T.ACCENT}; font-size:{T.spt(10.5)}; font-weight:800;'>"
            f"{sn}</span> "
            f"<span style='color:{T.FG_DIM};'>&nbsp;·&nbsp;</span> "
            f"<span style='color:{T.METER_LABEL}; font-size:{_px_caption()}; font-weight:600;'>OCR</span> "
            f"<span style='color:{T.FG_MUTED}; font-size:{T.spt(9)}; font-weight:500; font-family:{T.FONT_CSS_UI};'>"
            f"{esc(r)}</span>"
        )

    def apply_scaled_typography(self) -> None:
        self._root.setSpacing(scale_px(6))
        self._st_fr.setStyleSheet(
            f"QFrame#pipelaKcStatusBanner {{"
            f"  background: {T.SURFACE};"
            f"  border: none;"
            f"  border-left: 3px solid {T.ACCENT};"
            f"  border-radius: {T.RADIUS_SM};"
            f"  padding: {qss_pad_all(6)};"
            f"}}"
        )
        self._title_lbl.setStyleSheet(
            f"font-weight: 800; font-size: {T.spt(11.5)}; color: {T.FG_MUTED}; "
            f"font-family: {T.FONT_CSS_UI}; letter-spacing: 0.04em;",
        )
        self._prog_big.setStyleSheet(
            f"font-family: {T.FONT_CSS_UI}; font-size: {_px_hero()}; font-weight: 800; "
            f"color: {T.ACCENT}; letter-spacing: -0.02em;",
        )
        df = self._daily.font()
        df.setPointSizeF(max(7.0, min(10.0, scaled_design_pt(8.5))))
        self._daily.setFont(df)
        self._set_daily_height()
        self._style_daily()
        self._typo.apply()
        # Restore sess rich after typo (sess uses dynamic HTML in _tick)
        self._apply_kill_panel_button_styles()
        self._sync_lap_meta_min_width()
        self._tick()

    def _sync_lap_meta_min_width(self) -> None:
        try:
            self._lap_meta.setMinimumWidth(
                self._lap_meta.fontMetrics().horizontalAdvance("경과 00:00:00.00")
                + scale_px(4),
            )
        except Exception:
            pass

    def _commit_gscale(self, v: int) -> None:
        m = self._m
        snapped = m._kill_counter_graph_bar_scale_snap(v)
        if snapped != v:
            self._gscale.blockSignals(True)
            self._gscale.setValue(snapped)
            self._gscale.blockSignals(False)
        if snapped == m.kill_counter_graph_bar_scale_percent:
            return
        m.kill_counter_graph_bar_scale_percent = snapped
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()

    def _reset_session(self) -> None:
        self._m._kill_counter_reset_session_kills()
        print("[Kill Counter] 세션 킬 기준 초기화", flush=True)

    def _lap_toggle(self) -> None:
        m = self._m
        if m.kill_counter_lap_start_ts is None:
            m.kill_counter_lap_pause_segments = []
            m.kill_counter_lap_start_ts = time.time()
            sync_registry_snapshot_from_module(m)
            m.schedule_save_config()
            print("[Kill Counter] 랩 시작", flush=True)
        elif m._kill_counter_lap_is_paused():
            segs = m.kill_counter_lap_pause_segments
            if segs and segs[-1][1] is None:
                segs[-1][1] = time.time()
            sync_registry_snapshot_from_module(m)
            m.schedule_save_config()
            print("[Kill Counter] 랩 재개", flush=True)
        else:
            m.kill_counter_lap_pause_segments.append([time.time(), None])
            sync_registry_snapshot_from_module(m)
            m.schedule_save_config()
            print("[Kill Counter] 랩 일시중지", flush=True)
        self._sync_lap_buttons()

    def _lap_clear(self) -> None:
        m = self._m
        if m.kill_counter_lap_start_ts is None:
            return
        m.kill_counter_lap_pause_segments = []
        m.kill_counter_lap_start_ts = time.time()
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
        print("[Kill Counter] 랩 초기화(재시작)", flush=True)

    def _lap_end(self) -> None:
        m = self._m
        if m.kill_counter_lap_start_ts is None:
            return
        m.kill_counter_lap_start_ts = None
        m.kill_counter_lap_pause_segments = []
        sync_registry_snapshot_from_module(m)
        m.schedule_save_config()
        print("[Kill Counter] 랩 종료", flush=True)

    def _sync_lap_buttons(self) -> None:
        m = self._m
        has = m.kill_counter_lap_start_ts is not None
        paused = m._kill_counter_lap_is_paused()
        if not has:
            self._lap_main.setText("시작")
        elif paused:
            self._lap_main.setText("재개")
        else:
            self._lap_main.setText("일시중지")
        self._lap_clear_btn.setEnabled(has)
        self._lap_end_btn.setEnabled(has)

    def _tick(self) -> None:
        m = self._m
        snap = get_registry_config_snapshot()
        prog = m._kill_counter_panel_progress_value_text(m.kill_counter_last_progress)
        self._prog_big.setText(prog)
        try:
            win = self.window()
            if win is not None and win.objectName() == "pipelaKcFrameless":
                win.setWindowTitle(f"Kill Counter · {prog}")
        except Exception:
            pass
        sess = m._kill_counter_session_total_kills_display()
        raw = (m.kill_counter_last_progress or "").strip()
        try:
            self._last_sess_k = int(sess)
        except (TypeError, ValueError):
            self._last_sess_k = 0
        self._last_ocr_raw = raw
        _sh = self._fmt_sess_html(self._last_sess_k, raw)
        if _sh != self._last_sess_html:
            self._last_sess_html = _sh
            self._sess.setText(_sh)

        tess_ok = m._kill_counter_tesseract_available_cached()
        phase = m.kill_counter_last_poll_phase
        if not snapshot_bool(snap, "kill_counter_enabled", bool(m.kill_counter_enabled)):
            self._st_main.setText("Kill Counter 꺼짐 (제어창에서 켤 수 있음)")
            self._st_main.setStyleSheet(
                f"color: {T.STATUS_ERR}; font-size: {_px_subval()}; font-weight: 600; "
                f"font-family: {T.FONT_CSS_UI};",
            )
        elif not tess_ok:
            self._st_main.setText("Tesseract 미설치 — 설정 → Tesseract")
            self._st_main.setStyleSheet(
                f"color: {T.STATUS_WARN}; font-size: {_px_subval()}; font-weight: 600; "
                f"font-family: {T.FONT_CSS_UI};",
            )
        else:
            ph = f"{phase}" if phase is not None else "—"
            self._st_main.setText(f"폴링: {ph}")
            self._st_main.setStyleSheet(
                f"color: {T.STATUS_OK}; font-size: {_px_subval()}; font-weight: 600; "
                f"font-family: {T.FONT_CSS_UI};",
            )

        # 통계·캘린더·일별·랩·목표/그래프 스핀: 구간 합·strftime 루프가 무거움 — ~0.35s 마다 갱신.
        now = time.monotonic()
        if self._slow_tick_mono == 0.0 or (now - self._slow_tick_mono) >= 0.35:
            self._slow_tick_mono = now
            k1 = m._kill_counter_stats_sum_last_seconds(3600.0)
            k6 = m._kill_counter_stats_sum_last_seconds(21600.0)
            k24 = m._kill_counter_stats_sum_last_seconds(86400.0)
            kph = (k24 / 24.0) if k24 else 0.0
            self._r1.setText(f"{k1:,}")
            self._r6.setText(f"{k6:,}")
            self._r24.setText(f"{k24:,}")
            self._rkph.setText(f"{kph:.1f}")

            td = m._kill_counter_stats_calendar_today_total()
            wk = m._kill_counter_stats_calendar_week_to_date_total()
            mo = m._kill_counter_stats_calendar_month_to_date_total()
            yst = m._kill_counter_stats_yesterday_same_elapsed_total()
            self._ctoday.setText(f"{td:,}")
            self._cweek.setText(f"{wk:,}")
            self._cmonth.setText(f"{mo:,}")

            dodv = m._kill_counter_dod_grid_values(td, yst)
            for i, (lb, val) in enumerate(zip(self._dod_lbls, dodv)):
                lb.setText(val)
                if i == 2:
                    s = str(val).strip().replace(",", "")
                    try:
                        d = int(s) if s and s not in ("—", "+", "-") else 0
                    except (TypeError, ValueError):
                        d = 0
                    if d > 0:
                        col = "#6bdc9b"
                    elif d < 0:
                        col = T.STATUS_ERR
                    else:
                        col = T.FG
                    lb.setStyleSheet(
                        f"color: {col}; font-size: {_px_value()}; font-weight: 800; "
                        f"font-family: {T.FONT_CSS_UI};",
                    )
                else:
                    lb.setStyleSheet(
                        f"color: {T.FG}; font-size: {_px_value()}; font-weight: 800; "
                        f"font-family: {T.FONT_CSS_UI};",
                    )

            pct_f = m._kill_counter_goal_tier_pct_float()
            self._gtier.setText(
                f"진행 {pct_f:.0f}%" if pct_f is not None else "진행 —",
            )
            self._gtr.setText(m._kill_counter_goal_transition_line())
            self._grem.setText(m._kill_counter_goal_rem_line())
            self._geta.setText(m._kill_counter_goal_eta_line(float(k1), float(kph)))
            pct_ch = m._kill_counter_goal_choin_pct_float()
            self._gchp.setText(
                f"진행 {pct_ch:.0f}%" if pct_ch is not None else "진행 —",
            )
            self._gcrm.setText(m._kill_counter_goal_choin_rem_line())
            self._gcel.setText(m._kill_counter_goal_choin_eta_line(float(k1), float(kph)))

            self._lap_title.setText(m._kill_counter_lap_group_title_text())
            meta = m._kill_counter_lap_header_meta_text()
            self._lap_meta.setText(f"경과 {meta}")
            fg = m._kill_counter_lap_stopwatch_label_fg()
            self._lap_meta.setStyleSheet(
                f"color: {fg}; font-size: {_px_subval()}; font-weight: 600; font-family: {T.FONT_CSS_UI};",
            )
            if m.kill_counter_lap_start_ts is None:
                for lb in (self._lap_r1, self._lap_r6, self._lap_r12, self._lap_r24):
                    lb.setText("—")
            else:
                a = m._kill_counter_stats_sum_lap_in_last_seconds(3600.0)
                b = m._kill_counter_stats_sum_lap_in_last_seconds(21600.0)
                c = m._kill_counter_stats_sum_lap_in_last_seconds(43200.0)
                d = m._kill_counter_stats_sum_lap_in_last_seconds(86400.0)
                self._lap_r1.setText(f"{a:,}")
                self._lap_r6.setText(f"{b:,}")
                self._lap_r12.setText(f"{c:,}")
                self._lap_r24.setText(f"{d:,}")

            _daily_txt = m._kill_counter_stats_daily_lines_text(self._daily_max_lines)
            if _daily_txt != self._last_daily_plain:
                self._last_daily_plain = _daily_txt
                self._daily.setPlainText(_daily_txt)
            if not self._gscale.hasFocus():
                self._gscale.blockSignals(True)
                gv = int(
                    m._kill_counter_graph_bar_scale_snap(
                        snapshot_int(
                            snap,
                            "kill_counter_graph_bar_scale_percent",
                            int(m.kill_counter_graph_bar_scale_percent),
                        ),
                    )
                )
                if self._gscale.value() != gv:
                    self._gscale.setValue(gv)
                self._gscale.blockSignals(False)
        self._sync_lap_buttons()


def _html_esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
