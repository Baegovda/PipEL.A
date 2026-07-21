#include "panels/settings_panel_defs.hpp"

namespace pipela::ui::panels {

const std::vector<SettingsPanelDef>& allSettingsPanelDefs() {
    static const std::vector<SettingsPanelDef> kPanels = {
        {"ride", "Ride 설정", "ride_"},
        {"hp_refill", "HP Refill 설정", "hp_refill_"},
        {"reload", "Reload 설정", "reload_"},
        {"ammo_restock", "Ammo Restock 설정", "ammo_restock_"},
        {"call_merc", "Call Merc 설정", "call_merc_"},
        {"flame_trigger", "Flame Trigger 설정", "flame_trigger_"},
        {"left_click", "Left Click 설정", "left_click_"},
        {"right_hold", "Right Hold 설정", "right_hold_"},
        {"kill_counter", "Kill Counter 설정", "kill_counter_"},
        {"start_game", "Start Game 설정", "start_game_"},
        {"console", "콘솔 설정", "console_"},
        {"interface", "인터페이스 설정", "interface_"},
        {"update", "업데이트 설정", "update_"},
        {"tesseract", "Tesseract 설정", "tesseract_"},
        {"template_thumb", "템플릿 미리보기", ""},
        {"image_preview", "이미지 미리보기", ""},
        {"settings_chrome", "설정 크롬", ""},
        {"kc_tier_table", "킬카운터 등급표", ""},
        {"kc_daily_calendar", "킬카운터 캘린더", ""},
    };
    return kPanels;
}

}  // namespace pipela::ui::panels
