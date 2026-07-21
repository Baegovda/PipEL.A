#include "kill_counter_window.hpp"

#include <QVBoxLayout>

#include "dock/dock_chrome_apply.hpp"
#include "panels/kill_counter_panel.hpp"
#include "theme/theme_engine.hpp"
#include "theme/ui_adaptive.hpp"

namespace pipela::ui::overlays {

KillCounterWindow::KillCounterWindow(QWidget* parent) : QWidget(parent) {
    setWindowFlags(Qt::Window | Qt::FramelessWindowHint);
    setStyleSheet(pipela::ui::theme::killCounterWindowChromeQss());

    auto* layout = new QVBoxLayout(this);
    const int ml = pipela::ui::theme::scalePxH(10, 420);
    const int mt = pipela::ui::theme::scalePxV(8, 720);
    layout->setContentsMargins(ml, mt, ml, mt);
    layout->setSpacing(pipela::ui::theme::scalePxV(6, 720));
    panel_ = new pipela::ui::panels::KillCounterPanel(this);
    layout->addWidget(panel_, 1);
}

void KillCounterWindow::setAppState(pipela::core::state::AppState* state) {
    if (panel_ != nullptr) {
        panel_->setAppState(state);
    }
}

void KillCounterWindow::setOverlayController(TemplateOverlayController* controller) {
    if (panel_ != nullptr) {
        panel_->setOverlayController(controller);
    }
}

void KillCounterWindow::applyDockLayout(const pipela::app::dock::SideDockLayout& layout,
                                        int max_inner_height_log,
                                        std::intptr_t anchor_hwnd) {
    if (!layout.valid()) {
        hide();
        return;
    }
    pipela::app::dock::applySideDockLayoutWithHeightCap(this, layout, anchor_hwnd,
                                                        max_inner_height_log);
}

}  // namespace pipela::ui::overlays
