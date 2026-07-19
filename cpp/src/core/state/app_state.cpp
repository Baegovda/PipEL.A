#include "pipela/core/state/app_state.hpp"

namespace pipela::core::state {

bool AppState::has(const std::string& key) const {
    std::lock_guard lock(mutex_);
    return values_.count(key) > 0;
}

std::optional<std::any> AppState::get(const std::string& key) const {
    std::lock_guard lock(mutex_);
    const auto it = values_.find(key);
    if (it == values_.end()) {
        return std::nullopt;
    }
    return it->second;
}

void AppState::set(const std::string& key, const std::any& value) {
    std::lock_guard lock(mutex_);
    values_[key] = value;
}

int AppState::incrementInt(const std::string& key, int delta) {
    std::lock_guard lock(mutex_);
    int cur = 0;
    const auto it = values_.find(key);
    if (it != values_.end()) {
        cur = std::any_cast<int>(it->second);
    }
    cur += delta;
    values_[key] = cur;
    return cur;
}

void AppState::seedDefaults() {
    set("running", true);
    set("left_click_feature_enabled", true);
    set("right_hold_feature_enabled", true);
    set("flame_trigger_feature_enabled", true);
    set("reload_active", true);
    set("kill_counter_enabled", true);
    set("target_hwnd", static_cast<std::intptr_t>(0));
    set("select_mode", false);
    set("reload_success_count", 0);
    set("ammo_restock_loop_count", 0);
}

}  // namespace pipela::core::state
