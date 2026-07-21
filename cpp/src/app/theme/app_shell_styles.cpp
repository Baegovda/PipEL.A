#include "theme/app_shell_styles.hpp"

#include "theme/theme_engine.hpp"
#include "theme/ui_adaptive.hpp"

namespace pipela::ui::theme {

QString controlFramelessWindowQss() {
    const int r_md = radiusPx("RADIUS_MD", 12);
    const int r_sm = radiusPx("RADIUS_SM", 8);
    return QString::fromUtf8(
               "QMainWindow { background: %1; }"
               "QWidget#pipelaControlRoot { background: %1; color: %2; }"
               "QWidget#pipelaActionBtnPanel {"
               "  background: %3; border: 1px solid %4; border-radius: %5px; }"
               "QWidget#pipelaActionsTabsSep { background: transparent; }"
               "QTabWidget::pane { border: 1px solid %4; border-radius: %6px; background: %7; }"
               "QPushButton { text-align: center; }"
               "QPushButton#pipelaQuitBtn {"
               " background: transparent; color: %8; border: 1px solid %4;"
               " border-radius: %9px; padding: 4px 12px; font-size: 11px; font-weight: 600;"
               " text-align: center; }"
               "QPushButton#pipelaQuitBtn:hover {"
               " background: %10; border-color: %11; color: %2; }"
               "QPushButton#pipelaQuitBtn:pressed { background: %12; color: %2; }")
        .arg(color("WINDOW_BG"), color("FG"), color("TRAY_BG"), color("TRAY_BORDER"))
        .arg(r_md)
        .arg(r_md)
        .arg(color("SURFACE"))
        .arg(color("FG_SECONDARY"))
        .arg(r_sm)
        .arg(color("DANGER_SOFT"))
        .arg(color("DANGER"))
        .arg(color("BTN_PRESSED"))
        + globalInteractionQss();
}

QString settingsHubEntryButtonQss() {
    const int hub_fpt = scalePx(12);
    const int pad_v = scalePxV(10, 24);
    const int pad_h = scalePxH(14, 400);
    const int radius = radiusPx("RADIUS_MD", 12);
    return QString::fromUtf8(
               "QPushButton {"
               " background: %1; color: %2; font-weight: 600; font-size: %3px;"
               " border: 1px solid %4; padding: %5px %6px; border-radius: %7px;"
               " text-align: center; }"
               "QPushButton:hover { background: %8; border-color: %9; color: %2; }"
               "QPushButton:pressed { background: %10; border-color: %4; }")
        .arg(color("SURFACE_ELEVATED"), color("FG"))
        .arg(hub_fpt)
        .arg(color("BORDER_DEFAULT"))
        .arg(pad_v)
        .arg(pad_h)
        .arg(radius)
        .arg(color("BTN_HOVER"), color("ACCENT"), color("BTN_PRESSED"));
}

QString settingsHubCategoryRowQss() {
    const int fpt = scalePx(12);
    const int pad_v = scalePxV(12, 24);
    const int pad_h = scalePxH(16, 400);
    const int radius = radiusPx("RADIUS_MD", 12);
    return QString::fromUtf8(
               "QPushButton#pipelaSettingsCategoryRow {"
               " background: %1; color: %2; font-weight: 600; font-size: %3px;"
               " border: 1px solid %4; border-radius: %7px; padding: %5px %6px; text-align: left; }"
               "QPushButton#pipelaSettingsCategoryRow:hover {"
               " background: %8; border-color: %9; color: %2; }"
               "QPushButton#pipelaSettingsCategoryRow:pressed {"
               " background: %10; border-color: %4; }")
        .arg(color("CARD_BG"), color("FG"))
        .arg(fpt)
        .arg(color("BORDER_DEFAULT"))
        .arg(pad_v)
        .arg(pad_h)
        .arg(radius)
        .arg(color("CARD_BG_HOVER"))
        .arg(color("ACCENT"))
        .arg(color("BTN_PRESSED"));
}

QString settingsHubHeaderQss(int layout_width_px, int layout_height_px) {
    const int py = scalePxV(8, layout_height_px);
    const int px = scalePxH(12, layout_width_px);
    const int radius = radiusPx("RADIUS_MD", 12);
    const QString fpt = QString::number(scalePx(12));
    const QString title_fpt = QString::number(scalePx(14));
    return QString::fromUtf8(
               "QWidget#pipelaSettingsHeader { background: %1; border: 1px solid %2;"
               " border-radius: %3px; }"
               "QLabel#pipelaSettingsHeaderTitle { color: %4; font-size: %5px; font-weight: 700; }"
               "QPushButton#pipelaSettingsNavBtn { color: %6; background: transparent;"
               " border: 1px solid %2; border-radius: %7px; min-width: 30px; max-width: 30px;"
               " min-height: 30px; max-height: 30px; font-size: %8px; font-weight: 600; padding: 0px; }"
               "QPushButton#pipelaSettingsNavBtn:hover { color: %9; border-color: %9; }"
               "QPushButton#pipelaSettingsNavBtn:disabled { color: %10; border-color: %2; }"
               "QLabel#pipelaSettingsSectionLabel { color: %6; font-size: %8px; font-weight: 600;"
               " padding: %11px %12px 4px %12px; }")
        .arg(color("SURFACE_ELEVATED"), color("BORDER_DEFAULT"))
        .arg(radius)
        .arg(color("FG"))
        .arg(title_fpt)
        .arg(color("FG_SECONDARY"))
        .arg(radiusPx("RADIUS_SM", 8))
        .arg(fpt)
        .arg(color("ACCENT"))
        .arg(color("FG_DIM"))
        .arg(py)
        .arg(px);
}

}  // namespace pipela::ui::theme
