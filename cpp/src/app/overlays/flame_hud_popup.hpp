#pragma once

#include <QWidget>

class QLabel;

namespace pipela::ui::overlays {

// AGENT: Flame Trigger 3-line HUD near cursor — subset of pipela_qt/cursor_hud.py _CursorHudFlamePopup.
class FlameHudPopup : public QWidget {
    Q_OBJECT
public:
    explicit FlameHudPopup(QWidget* parent = nullptr);

    void setFlameLines(const QString& line1, const QString& line2, const QString& line3);
    void placeAtCursorHotspot(int cur_x_phys, int cur_y_phys);
    void parkHidden();

private:
    QLabel* line1_{nullptr};
    QLabel* line2_{nullptr};
    QLabel* line3_{nullptr};
};

}  // namespace pipela::ui::overlays
