#include "application.hpp"

#include <QApplication>
#include <QLabel>
#include <QMenu>
#include <QVBoxLayout>
#include <QWidget>

#include "pipela/core/version.hpp"
#include "theme/theme_tokens.hpp"

#ifdef _WIN32
#include "pipela/native/dcomp_hud.hpp"
#endif

PipelaMainWindow::PipelaMainWindow(QWidget* parent) : QMainWindow(parent) {
    setWindowTitle(QString::fromUtf8("Pipela ") +
                   QString::fromStdString(pipela::core::appVersion()));
    resize(1024, 720);
    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    auto* label = new QLabel(QString::fromUtf8("Pipela Qt6 C++ (Phase 4 shell)"), central);
    label->setStyleSheet(pipela::ui::theme::bodyLabelQss());
    layout->addWidget(label);
    setCentralWidget(central);
    setupTray();
}

void PipelaMainWindow::setupTray() {
    tray_ = new QSystemTrayIcon(this);
    tray_->setToolTip(QString::fromUtf8("Pipela"));
    auto* menu = new QMenu(this);
    menu->addAction(QString::fromUtf8("종료"), qApp, &QApplication::quit);
    tray_->setContextMenu(menu);
    tray_->show();
}

int runQtApplication(int argc, char** argv) {
    QApplication app(argc, argv);
    pipela::ui::theme::applyThemeFromResources(app);
#ifdef _WIN32
    pipela::native::DCompHud hud;
    (void)hud;
#endif
    PipelaMainWindow win;
    win.show();
    return app.exec();
}
