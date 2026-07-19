#include "control_main_window.hpp"

#include <QLabel>
#include <QTabWidget>
#include <QVBoxLayout>

ControlMainWindow::ControlMainWindow(QWidget* parent) : QMainWindow(parent) {
    setWindowTitle(QString::fromUtf8("Pipela 제어"));
    auto* central = new QWidget(this);
    auto* layout = new QVBoxLayout(central);
    auto* tabs = new QTabWidget(central);
    tabs->addTab(new QLabel(QString::fromUtf8("메인")), QString::fromUtf8("메인"));
    tabs->addTab(new QLabel(QString::fromUtf8("설정")), QString::fromUtf8("설정"));
    layout->addWidget(tabs);
    setCentralWidget(central);
}
