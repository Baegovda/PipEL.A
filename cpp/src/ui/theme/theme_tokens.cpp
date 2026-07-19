#include "theme/theme_tokens.hpp"

#include <QApplication>
#include <QPalette>

namespace pipela::ui::theme {

void applyGlobalPalette(QApplication& app) {
    QPalette pal = app.palette();
    pal.setColor(QPalette::Window, QColor(24, 26, 32));
    pal.setColor(QPalette::WindowText, QColor(230, 232, 238));
    app.setPalette(pal);
}

const char* bodyLabelQss() { return "color: #e6e8ee; font-size: 14px;"; }

}  // namespace pipela::ui::theme
