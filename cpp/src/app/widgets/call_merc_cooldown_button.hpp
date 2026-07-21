#pragma once

#include <QPushButton>

class QTimer;

namespace pipela::ui::widgets {

// AGENT: Call Merc / Reload cooldown gauge + end flash (pipela_qt/control_main.py).
class CallMercCooldownButton : public QPushButton {
    Q_OBJECT
public:
    explicit CallMercCooldownButton(QWidget* parent = nullptr);

    void setCooldownFill(double v);

protected:
    void paintEvent(QPaintEvent* event) override;

private slots:
    void tickCooldownFlash();

private:
    void stopCooldownDoneFlash();
    void startCooldownDoneFlash();

    double cd_fill_{0.0};
    bool cd_gauge_armed_{false};
    double flash_start_mono_{0.0};
    QTimer* flash_timer_{nullptr};
    static constexpr double kFlashDurSec = 0.55;
};

}  // namespace pipela::ui::widgets
