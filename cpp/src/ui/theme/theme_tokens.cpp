#include "theme/theme_tokens.hpp"

#include <QApplication>
#include <QColor>
#include <QFile>
#include <QPalette>
#include <QJsonDocument>
#include <QJsonObject>

namespace pipela::ui::theme {

void applyGlobalPalette(QApplication& app) {
    QPalette pal = app.palette();
    pal.setColor(QPalette::Window, QColor(24, 26, 32));
    pal.setColor(QPalette::WindowText, QColor(230, 232, 238));
    app.setPalette(pal);
}

void applyThemeFromResources(QApplication& app) {
    applyGlobalPalette(app);
    QFile f(":/theme/pipela_theme.json");
    if (!f.open(QIODevice::ReadOnly)) {
        return;
    }
    const auto doc = QJsonDocument::fromJson(f.readAll());
    if (!doc.isObject()) {
        return;
    }
    const QJsonObject obj = doc.object();
    const QString window_bg = obj.value("WINDOW_BG").toString("#121417");
    QPalette pal = app.palette();
    pal.setColor(QPalette::Window, QColor(window_bg));
    app.setPalette(pal);
}

const char* bodyLabelQss() { return "color: #e6e8ee; font-size: 14px;"; }

int scalePx(int value, double ui_scale) {
    if (ui_scale <= 0.01) {
        ui_scale = 1.0;
    }
    return static_cast<int>(value * ui_scale + 0.5);
}

}  // namespace pipela::ui::theme
