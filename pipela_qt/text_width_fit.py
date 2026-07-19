"""QLabel·``QPushButton`` 플레인 문자열 폭 피팅 — **비활성(no-op)**.

가로 연동 스케일 제거 정책에 따라 ``setFont`` 기반 폭 맞춤은 호출해도 아무 것도 하지 않는다.

기존 호출부·시그니처는 유지한다.
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QWidget


PIP_NO_PLAIN_WIDTH_FIT = "pipela_no_plain_width_fit"


def fit_plain_line_to_width_px(
    w: QWidget,
    *,
    avail_px: int,
    hi_pt: float,
    lo_pt: float,
    weight: QFont.Weight,
    txt: str | None = None,
) -> None:
    """비활성 — 가로 연동 폰트 피팅 제거."""
    del w, avail_px, hi_pt, lo_pt, weight, txt


def fit_plain_extrabold_to_width_px(
    w: QWidget,
    txt: str | None,
    avail_px: int,
    hi_pt: float,
    lo_pt: float,
) -> None:
    del w, txt, avail_px, hi_pt, lo_pt


def fit_plain_extrabold_to_label_width_minus(
    lbl: QLabel,
    *,
    hi_pt: float,
    lo_pt: float,
    margin_px: int | None = None,
    txt: str | None = None,
) -> None:
    del lbl, hi_pt, lo_pt, margin_px, txt


def fit_plain_medium_wrap_width(
    w: QWidget,
    *,
    hi_pt: float,
    lo_pt: float,
    weight: QFont.Weight = QFont.Weight.Medium,
) -> None:
    del w, hi_pt, lo_pt, weight


def refresh_plain_label_width_fits_under(
    root: QWidget,
    *,
    line_hi_pt: float | Callable[[], float] | None = None,
    line_lo_pt: float | Callable[[], float] | None = None,
    wrap_hi_pt: float | Callable[[], float] | None = None,
    wrap_lo_pt: float | Callable[[], float] | None = None,
    long_plain_char_threshold: int = 112,
) -> None:
    """비활성 — 제어창 리사이즈 시 폭 피팅 순회 제거."""
    del (
        root,
        line_hi_pt,
        line_lo_pt,
        wrap_hi_pt,
        wrap_lo_pt,
        long_plain_char_threshold,
    )
