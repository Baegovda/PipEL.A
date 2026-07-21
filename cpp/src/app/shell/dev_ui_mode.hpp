#pragma once

#include "dock/dock_ui_phase.hpp"

namespace pipela::ui::shell {

// AGENT: Dev UI — docked chrome without game/launcher anchor (Python dev_ui_mode.py).
bool pipelaDevUiEnabled();
bool pipelaDevUiNoAnchor(pipela::ui::dock::UiDockPhase phase);
bool pipelaDevUiStandbyChrome(pipela::ui::dock::UiDockPhase phase);

// AGENT: Title-strip checkbox — dock control + kill panel beside launcher (owner debug).
bool pipelaLauncherDebugChromeEnabled();
void setPipelaLauncherDebugChromeEnabled(bool enabled);

}  // namespace pipela::ui::shell
