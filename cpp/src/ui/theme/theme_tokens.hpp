#pragma once

class QApplication;

namespace pipela::ui::theme {

void applyGlobalPalette(QApplication& app);
const char* bodyLabelQss();

}  // namespace pipela::ui::theme
