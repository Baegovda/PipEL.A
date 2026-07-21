#pragma once

#include <QPushButton>

class QTimer;

namespace pipela::ui::widgets {

// AGENT: Flame trigger glass prism highlight when emitting (pipela_qt/flame_trigger_glass_button.py).
class FlameTriggerGlassButton : public QPushButton {
    Q_OBJECT
public:
    explicit FlameTriggerGlassButton(QWidget* parent = nullptr);

    void setEmitting(bool emitting);

protected:
    void paintEvent(QPaintEvent* event) override;

private slots:
    void tickPrism();

private:
    bool emitting_{false};
    double phase_{0.0};
    QTimer* anim_timer_{nullptr};
};

}  // namespace pipela::ui::widgets
