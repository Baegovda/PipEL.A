#pragma once

#include <string_view>
#include <vector>

namespace pipela::ui::panels {

// AGENT: Hub grid order mirrors pipela_qt/main_window.py HUB_MAIN_ENTRIES + HUB_FOOTER_ENTRIES.
struct SettingsHubEntry {
    const char* panel_id;
    const char* title_ko;
};

inline const std::vector<SettingsHubEntry>& hubMainEntries() {
    static const std::vector<SettingsHubEntry> kEntries = {
        {"left_click", "LeftClick 설정"},
        {"flame_trigger", "Flame Trigger 설정"},
        {"reload", "Reload 설정"},
        {"ride", "Ride 설정"},
        {"hp_refill", "HP Refill 설정"},
        {"ammo_restock", "Ammo Restock 설정"},
        {"call_merc", "Call Merc 설정"},
        {"start_game", "Intro Skip 설정"},
        {"interface", "인터페이스"},
        {"console", "터미널"},
    };
    return kEntries;
}

inline const std::vector<SettingsHubEntry>& hubFooterEntries() {
    static const std::vector<SettingsHubEntry> kEntries = {
        {"update", "업데이트"},
        {"tesseract", "테서렉트 설치법"},
    };
    return kEntries;
}

inline bool isHubPanelId(std::string_view panel_id) {
    for (const auto& e : hubMainEntries()) {
        if (panel_id == e.panel_id) {
            return true;
        }
    }
    for (const auto& e : hubFooterEntries()) {
        if (panel_id == e.panel_id) {
            return true;
        }
    }
    return false;
}

}  // namespace pipela::ui::panels
