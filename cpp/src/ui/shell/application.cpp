#include "application.hpp"

#include <QApplication>
#include <QLabel>
#include <QVBoxLayout>
#include <QWidget>

#include "pipela/core/version.hpp"
#include "theme/theme_tokens.hpp"

PipelaMainWindow::PipelaMainWindow(QWidget* parent) : QMainWindow(parent) {
    setWindowTitle(QString::fromUtf8("Pipela ") +
                   QString::fromStdString(pipela::core::appVersion()));
    resize(960, 640);
    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    auto* label = new QLabel(QString::fromUtf8("Pipela Qt6 C++ shell (migration scaffold)"), central);
    label->setStyleSheet(pipela::ui::theme::bodyLabelQss());
    layout->addWidget(label);
    setCentralWidget(central);
}

int runQtApplication(int argc, char** argv) {
    QApplication app(argc, argv);
    pipela::ui::theme::applyGlobalPalette(app);
    PipelaMainWindow win;
    win.show();
    return app.exec();
}
