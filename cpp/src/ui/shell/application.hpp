#pragma once

#include <QMainWindow>

class PipelaMainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit PipelaMainWindow(QWidget* parent = nullptr);
};

int runQtApplication(int argc, char** argv);
