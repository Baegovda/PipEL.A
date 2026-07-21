#include "theme/qt_typography_refresh.hpp"

#include <algorithm>

#include <QApplication>
#include <QFont>
#include <QWidget>

namespace pipela::ui::theme {

void refreshPipelaTypography(QApplication* app, QWidget* control_root, int font_pt) {
    const int pt = std::max(8, std::min(24, font_pt));
    if (app != nullptr) {
        QFont font = app->font();
        font.setPointSize(pt);
        app->setFont(font);
    }
    if (control_root != nullptr) {
        control_root->updateGeometry();
        control_root->update();
    }
}

}  // namespace pipela::ui::theme
