#pragma once

namespace pipela::app::dock {

constexpr int kDockPairPanelWMin = 260;
constexpr int kDockPairPanelWMax = 900;

int clampDockPairPanelW(int w_log);
int resolveUnifiedSavedDockPanelW(int preset_w_log);

}  // namespace pipela::app::dock
