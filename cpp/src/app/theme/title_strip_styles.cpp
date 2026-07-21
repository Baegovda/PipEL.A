#include "theme/title_strip_styles.hpp"

#include "theme/theme_engine.hpp"

namespace pipela::ui::theme {

QString gameTitleStripQss() {
    return QString::fromUtf8(
               "QWidget#pipelaGameTitleStripRoot {"
               "  background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 %1, stop:1 %2);"
               "  border: none; border-bottom: 1px solid %3;"
               "}"
               "QLabel#pipelaStripBrand { color: %4; font-size: 11px; font-weight: 700; }"
               "QLabel#pipelaStripVer { color: %5; font-size: 10px; }"
               "QLabel#pipelaStripRes { color: %5; background: transparent; font-size: 9px; }"
               "QToolButton#pipelaStripKillCounterBtn {"
               "  color: %6; background: transparent; border: none; padding: 2px 8px;"
               "  font-size: 10px; font-weight: 600; border-radius: %7px;"
               "}"
               "QToolButton#pipelaStripKillCounterBtn:hover { color: %4; background: %8; }"
               "QPushButton#pipelaStripCaptionBtn {"
               "  background: transparent; color: %6; border: none;"
               "  min-width: 24px; max-width: 24px; min-height: 20px; max-height: 20px;"
               "  padding: 0; border-radius: %7px;"
               "}"
               "QPushButton#pipelaStripCaptionBtn:hover { background: %9; color: %4; }"
               "QPushButton#pipelaStripCloseBtn {"
               "  background: transparent; color: %6; border: none;"
               "  min-width: 24px; max-width: 24px; min-height: 20px; max-height: 20px;"
               "  padding: 0; border-radius: %7px;"
               "}"
               "QPushButton#pipelaStripCloseBtn:hover { background: %10; color: %6; }"
               "QCheckBox#pipelaStripLauncherDebug { color: %6; spacing: 4px; }"
               "QCheckBox#pipelaStripLauncherDebug::indicator {"
               "  width: 14px; height: 14px; border-radius: 3px;"
               "  border: 1px solid %3; background: transparent; }"
               "QCheckBox#pipelaStripLauncherDebug::indicator:checked {"
               "  background: %8; border-color: %4; }")
        .arg(color("STRIP_BG_TOP"), color("STRIP_BG_BOTTOM"), color("BORDER_DEFAULT"),
             color("STRIP_ACCENT"), color("STRIP_FG_MUTED"), color("STRIP_FG"))
        .arg(radiusPx("RADIUS_SM", 8))
        .arg(color("ACCENT_SOFT"))
        .arg(color("BORDER_SUBTLE"))
        .arg(color("DANGER_HOVER_BG"));
}

}  // namespace pipela::ui::theme
