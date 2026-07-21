#include "theme/control_tab_chrome.hpp"

#include <algorithm>
#include <cmath>

#include "theme/theme_engine.hpp"
#include "theme/ui_adaptive.hpp"

namespace pipela::ui::theme {

namespace {

constexpr double kTabPadVDesign = 8.0;
constexpr double kTabPadHDesign = 14.0;
constexpr double kLabelDesignPt = 9.5;

}  // namespace

int mainTabsIconLabelGapPx(int layout_width_px) {
    return std::max(4, scalePxH(6, layout_width_px));
}

int mainTabsTabPadVPx(int layout_height_px) {
    return scalePxV(static_cast<int>(std::lround(kTabPadVDesign)), layout_height_px);
}

int mainTabsTabPadHPx(int layout_width_px) {
    return scalePxH(static_cast<int>(std::lround(kTabPadHDesign)), layout_width_px);
}

int mainTabsInterTabGapPx(int layout_width_px) {
    return std::max(2, scalePxH(4, layout_width_px));
}

int mainTabsRailHpadPx(int layout_width_px) {
    return std::max(6, scalePxH(8, layout_width_px));
}

int mainTabsBarVerticalInsetPx(int layout_height_px) {
    return std::max(4, scalePxV(6, layout_height_px));
}

int mainTabsMinHeightPx(int layout_height_px) {
    return std::max(30, scalePxV(34, layout_height_px));
}

int mainTabsSegmentRadiusPx(int layout_height_px) {
    return std::max(6, scalePxV(radiusPx("RADIUS_SM", 8), layout_height_px));
}

QString mainTabsTabPaddingQss(int layout_width_px, int layout_height_px) {
    const int pv = mainTabsTabPadVPx(layout_height_px);
    const int ph = mainTabsTabPadHPx(layout_width_px);
    return QString::fromUtf8("%1px %2px").arg(pv).arg(ph);
}

QString mainTabsLabelFontSpt(int layout_width_px) {
    const double pt = mainTabsLabelFontPointSize(layout_width_px);
    return QString::number(pt, 'g', 4) + QString::fromUtf8("pt");
}

double mainTabsLabelFontPointSize(int layout_width_px) {
    const double ui = typographyWidthScale(layout_width_px);
    return std::clamp(scaledDesignPt(kLabelDesignPt, ui), 8.0, 16.0);
}

int mainTabsBarIconSizePx(int layout_width_px, int layout_height_px) {
    const double pt = mainTabsLabelFontPointSize(layout_width_px);
    const double ui = typographyHeightScale(layout_height_px);
    const int raw = static_cast<int>(std::lround(pt * ui * 1.35));
    return std::clamp(raw, 12, 36);
}

QString mainTabsAreaQss(int layout_width_px, int layout_height_px) {
    const QString pad = mainTabsTabPaddingQss(layout_width_px, layout_height_px);
    const QString fpt = mainTabsLabelFontSpt(layout_width_px);
    const int inset = mainTabsBarVerticalInsetPx(layout_height_px);
    const int r = radiusPx("RADIUS_MD", 12);
    return QString::fromUtf8(
               "QTabWidget#pipelaMainTabs::pane { border: 1px solid %1; border-radius: %2px; "
               "background: %3; margin-top: 0px; }"
               "QTabWidget#pipelaMainTabs > QWidget#pipelaTabArea { background: transparent; }"
               "QTabBar { background: %4; border-radius: %2px; padding: 4px; }"
               "QTabBar::tab { padding: %5; font-weight: 600; font-size: %6; color: %7; "
               "background: transparent; border: none; margin: 2px; }"
               "QTabBar::tab:selected { color: %8; }"
               "QTabBar { padding-top: %9px; }")
        .arg(color("BORDER_DEFAULT"))
        .arg(r)
        .arg(color("SURFACE"))
        .arg(color("PANEL_BG"))
        .arg(pad, fpt, color("FG_SECONDARY"), color("ACCENT"))
        .arg(inset);
}

QString settingsBreadcrumbChromeQss(int layout_width_px, int layout_height_px) {
    const int r = radiusPx("RADIUS_MD", 12);
    const int py = scalePxV(4, layout_height_px);
    const int px = scalePxH(12, layout_width_px);
    const int seg_py = scalePxV(2, layout_height_px);
    const int seg_px = scalePxH(4, layout_width_px);
    const QString fpt = mainTabsLabelFontSpt(layout_width_px);
    const QString fpt_cur =
        QString::number(scaledDesignPt(10.0, typographyWidthScale(layout_width_px)), 'g', 4) +
        QString::fromUtf8("pt");
    return QString::fromUtf8(
               "QPushButton#pipelaBreadcrumbSeg { color: %1; background: transparent; border: none; "
               "font-size: %2; font-weight: 500; padding: %3px %4px; text-align: center; }"
               "QPushButton#pipelaBreadcrumbSeg:hover { color: %5; }"
               "QLabel#pipelaBreadcrumbSep { color: %6; font-size: %2; font-weight: 600; padding: 0px "
               "%7px; }"
               "QLabel#pipelaBreadcrumbCurrent { color: %5; background-color: %8; "
               "border: 1px solid %9; border-left: 3px solid %5; border-radius: "
               "%10px; font-size: %11; font-weight: 700; padding: %12px %13px; }"
               "QPushButton#pipelaSettingsNavBtn { color: %1; background: transparent; border: 1px "
               "solid %14; border-radius: %15px; padding: 2px 8px; font-size: %2; text-align: center; }"
               "QPushButton#pipelaSettingsNavBtn:hover { color: %5; border-color: %5; }"
               "QPushButton#pipelaSettingsNavBtn:disabled { color: %6; border-color: %14; }")
        .arg(color("FG_SECONDARY"))
        .arg(fpt)
        .arg(seg_py)
        .arg(seg_px)
        .arg(color("ACCENT"))
        .arg(color("FG_MUTED"))
        .arg(scalePxH(2, layout_width_px))
        .arg(color("ACCENT_SOFT"), color("ACCENT_BORDER"))
        .arg(r)
        .arg(fpt_cur)
        .arg(py)
        .arg(px)
        .arg(color("BORDER_DEFAULT"))
        .arg(radiusPx("RADIUS_SM", 8));
}

}  // namespace pipela::ui::theme
