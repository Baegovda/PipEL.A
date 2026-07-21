#pragma once

#include <QApplication>

namespace pipela::ui::theme {

void applyGlobalPalette(QApplication& app);
void applyThemeFromResources(QApplication& app);
const char* bodyLabelQss();

}  // namespace pipela::ui::theme
