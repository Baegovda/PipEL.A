#pragma once

#include <QString>

namespace pipela::ui::theme {

// AGENT: Main tabs chrome tokens — Python pipela_qt/control_tab_chrome.py parity.
int mainTabsIconLabelGapPx(int layout_width_px);
int mainTabsTabPadVPx(int layout_height_px);
int mainTabsTabPadHPx(int layout_width_px);
int mainTabsInterTabGapPx(int layout_width_px);
int mainTabsRailHpadPx(int layout_width_px);
int mainTabsBarVerticalInsetPx(int layout_height_px);
int mainTabsMinHeightPx(int layout_height_px);
int mainTabsSegmentRadiusPx(int layout_height_px);
QString mainTabsTabPaddingQss(int layout_width_px, int layout_height_px);
QString mainTabsLabelFontSpt(int layout_width_px);
double mainTabsLabelFontPointSize(int layout_width_px);
int mainTabsBarIconSizePx(int layout_width_px, int layout_height_px);
QString mainTabsAreaQss(int layout_width_px, int layout_height_px);
QString settingsBreadcrumbChromeQss(int layout_width_px, int layout_height_px);

}  // namespace pipela::ui::theme
