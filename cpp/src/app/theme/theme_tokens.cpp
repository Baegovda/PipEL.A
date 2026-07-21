#include "theme/theme_tokens.hpp"

#include <QApplication>

#include "theme/theme_engine.hpp"

namespace pipela::ui::theme {

void applyGlobalPalette(QApplication& app) { applyFullTheme(app); }

void applyThemeFromResources(QApplication& app) { applyFullTheme(app); }

const char* bodyLabelQss() { return "color: #f2f6f4; font-size: 14px;"; }

}  // namespace pipela::ui::theme
