#pragma once

#include <QMainWindow>
#include <QSystemTrayIcon>

class PipelaMainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit PipelaMainWindow(QWidget* parent = nullptr);

private:
    void setupTray();
    QSystemTrayIcon* tray_{nullptr};
};

int runQtApplication(int argc, char** argv);
