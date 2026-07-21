#pragma once

#include <QWidget>

class QLabel;

namespace pipela::ui::overlays {

class GameOverlayWindow : public QWidget {
    Q_OBJECT
public:
    explicit GameOverlayWindow(QWidget* parent = nullptr);

    void syncToClientRect(std::intptr_t anchor_hwnd, int left, int top, int right, int bottom);
    void setRegionPreviewActive(bool active);

private:
    QLabel* hint_{nullptr};
};

}  // namespace pipela::ui::overlays
