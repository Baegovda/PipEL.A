#include "dock/dock_panel_pair_resize.hpp"

#include <algorithm>
#include <string>

#include "pipela/core/registry/store.hpp"

namespace pipela::app::dock {

int clampDockPairPanelW(int w_log) {
    return std::max(kDockPairPanelWMin, std::min(kDockPairPanelWMax, w_log));
}

int resolveUnifiedSavedDockPanelW(int preset_w_log) {
    const auto values = pipela::core::registry::loadAllStringValues();
    auto parse_saved = [&](const char* key) -> int {
        const auto it = values.find(key);
        if (it == values.end()) {
            return 0;
        }
        try {
            return std::stoi(it->second);
        } catch (...) {
            return 0;
        }
    };
    const int cp = parse_saved("control_panel_w");
    if (cp > 0) {
        return clampDockPairPanelW(cp);
    }
    const int kcw = parse_saved("kill_counter_panel_w");
    if (kcw > 0) {
        return clampDockPairPanelW(kcw);
    }
    return std::max(8, preset_w_log);
}

}  // namespace pipela::app::dock
