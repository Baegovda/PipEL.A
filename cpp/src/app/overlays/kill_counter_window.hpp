#pragma once

#include <QWidget>

#include <cstdint>

#include "dock/side_dock_layout.hpp"

namespace pipela::core::state {
class AppState;
}
namespace pipela::ui::overlays {
class TemplateOverlayController;
}
namespace pipela::ui::panels {
class KillCounterPanel;
}

namespace pipela::ui::overlays {

class KillCounterWindow : public QWidget {
    Q_OBJECT
public:
    explicit KillCounterWindow(QWidget* parent = nullptr);

    void applyDockLayout(const pipela::app::dock::SideDockLayout& layout,
                         int inner_height_log,
                         std::intptr_t anchor_hwnd);
    void setAppState(pipela::core::state::AppState* state);
    void setOverlayController(TemplateOverlayController* controller);

private:
    pipela::ui::panels::KillCounterPanel* panel_{nullptr};
};

}  // namespace pipela::ui::overlays
