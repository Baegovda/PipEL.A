#pragma once

#include <cstdint>

#include <QWidget>

#include "dock/dock_ui_phase.hpp"

namespace pipela::ui::overlays {
class DockChromeController;
}

namespace pipela::ui::dock {

struct DockChromeRestoreContext {
    QWidget* dock_host{nullptr};
    QWidget* title_strip{nullptr};
    pipela::ui::overlays::DockChromeController* dock_chrome{nullptr};
};

// AGENT: pipela_qt/dock_chrome_restore.restore_pipela_docked_chrome_if_needed MVP.
bool restoreDockedChromeIfNeeded(DockChromeRestoreContext& ctx,
                                 pipela::ui::dock::UiDockPhase phase,
                                 std::intptr_t target_hwnd,
                                 bool game_just_restored,
                                 bool chrome_minimized_with_game,
                                 bool user_dismissed_control);

}  // namespace pipela::ui::dock
