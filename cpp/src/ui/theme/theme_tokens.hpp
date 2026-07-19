#pragma once

namespace pipela::ui::theme {

void applyGlobalPalette(class QApplication& app);
void applyThemeFromResources(class QApplication& app);
const char* bodyLabelQss();
int scalePx(int value, double ui_scale = 1.0);

}  // namespace pipela::ui::theme
