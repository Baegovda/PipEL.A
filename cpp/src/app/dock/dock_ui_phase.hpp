#pragma once

#include <QString>

namespace pipela::ui::dock {

enum class UiDockPhase { Standby, Launcher, Client };

// AGENT: Mirrors pipela_qt/dock_ui_phase.py phase strings.
const char* uiDockPhaseString(UiDockPhase phase);

UiDockPhase resolveUiDockPhase(std::intptr_t target_hwnd, std::intptr_t launcher_hwnd,
                               bool (*is_minimized)(std::intptr_t));

}  // namespace pipela::ui::dock
