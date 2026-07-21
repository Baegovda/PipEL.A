#pragma once

#include <QWidget>

namespace pipela::core::state {
class AppState;
}

namespace pipela::ui::overlays {

// AGENT: Game-client centered banner when FT session starts — subset of QtFlameStartBanner.
class FlameStartBanner : public QWidget {
    Q_OBJECT
public:
    explicit FlameStartBanner(pipela::core::state::AppState* state, QWidget* parent = nullptr);

    void tick();

protected:
    void paintEvent(QPaintEvent* event) override;

private:
    void parkHidden();
    std::intptr_t targetHwnd() const;

    pipela::core::state::AppState* state_{nullptr};
    QString banner_text_;
    double hold_end_wall_{0.0};
    bool was_active_{false};
};

}  // namespace pipela::ui::overlays
