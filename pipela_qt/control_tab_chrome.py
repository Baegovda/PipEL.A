"""제어창 터미널·설정 `QTabWidget#pipelaMainTabs` — 아이콘·라벨 간격·탭바 패딩·균등 분할 상수(단일 출처)."""

from __future__ import annotations

from pipela_qt.ui_adaptive import qss_pad_vh, scale_px, scaled_design_pt, spt


def main_tabs_icon_label_gap_px() -> int:
    """탭 셀 안 아이콘 ↔ 텍스트 (ClusterTabLabelStyle). 거의 붙임 + 클러스터 가로·세로 가운데."""
    return max(0, min(2, scale_px(1)))


def main_tabs_inter_tab_gap_px() -> int:
    """터미널 / 설정 세그먼트 사이 (PairedControlTabBar). 얇은 구분 느낌."""
    return max(0, scale_px(4))


def main_tabs_rail_hpad_px() -> int:
    """탭바 좌·우에 한쪽당 패딩 (논리 px)."""
    return max(4, scale_px(6))


def main_tabs_bar_vertical_inset_px() -> int:
    """tab-bar:: 가로 `padding` 의 위 (아래는 구분선에 맞춤)."""
    return max(2, scale_px(3))


def main_tabs_min_height_px() -> int:
    """QTabBar::tab `min-height`."""
    return max(26, scale_px(30))


def main_tabs_segment_radius_px() -> int:
    """탭 모서리 반경(상단만 쓰임 — 심플하게 낮게)."""
    return max(3, scale_px(4))


def main_tabs_tab_padding_qss() -> str:
    """QTabBar::tab `padding` — 하단 강조선·아이콘+라벨 여유."""
    return qss_pad_vh(6, 12)


def main_tabs_label_font_spt() -> str:
    """탭 글자 pt (QSS)."""
    return spt(9.5)


def main_tabs_bar_icon_size_px() -> int:
    """QTabBar `setIconSize` — 아이콘 한 변 (제어창 `apply_scaled_typography`에서 동기)."""
    return max(14, min(24, scale_px(18)))


def main_tabs_label_font_point_size() -> float:
    """QTabBar `setFont` pt (QSS와 맞출 때 사용)."""
    return max(8.0, min(16.0, float(scaled_design_pt(9.5))))
