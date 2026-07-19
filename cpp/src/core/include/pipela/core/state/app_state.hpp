#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <variant>

namespace pipela::core::state {

struct InputState {
    bool left_click_feature_enabled{true};
    bool left_click_active{false};
    bool left_pressed{false};
    bool right_hold_active{false};
    int left_click_id{0};
    bool flame_trigger_active{false};
    bool reload_active{true};
    bool ammo_restock_active{false};
    double reload_nobullet_arm_until_mono{0.0};
    int ammo_restock_toggle_key_code{0};
    double flame_trigger_start_time{0.0};
    double flame_trigger_press_text_until{0.0};
    std::string flame_trigger_press_key_name;
    int flame_trigger_press_count{0};
    double flame_trigger_last_press_interval_sec{0.0};
    double flame_trigger_hud_session_start_time{0.0};
    int flame_trigger_session_reload_count{0};
    double flame_trigger_last_reload_complete_time{0.0};
    double flame_trigger_last_reload_trigger_time{0.0};
    bool flame_trigger_reload_teardown_preserve_hud{false};
    double hp_refill_detection_score{0.0};
    int hp_refill_trigger_total{0};
};

struct WorkerRuntimeState {
    bool running{true};
    std::intptr_t target_hwnd{0};
    bool select_mode{false};
    bool nobullet_detected{false};
    double last_nobullet_time{0.0};
    double nobullet_detection_score{0.0};
    double bullet_detection_score{0.0};
    double vault_detection_score{0.0};
    int reload_success_count{0};
    int reload_ammo_count{0};
    int ammo_restock_loop_count{0};
    double ammo_restock_buybutton_score{0.0};
    double ammo_restock_inven_score{0.0};
    double ammo_restock_bank_score{0.0};
    bool ammo_restock_sequence_busy{false};
    bool call_merc_sequence_busy{false};
};

struct KillCounterState {
    bool kill_counter_enabled{true};
    std::string kill_counter_last_progress;
    double kill_counter_last_poll_ts{0.0};
    int kill_counter_session_carried_kills{0};
};

using StateValue = std::variant<std::monostate, bool, int, std::int64_t, double, std::string>;

class AppState {
public:
    InputState input;
    WorkerRuntimeState worker;
    KillCounterState kill_counter;

    bool has(const std::string& key) const;
    std::optional<StateValue> get(const std::string& key) const;
    bool set(const std::string& key, const StateValue& value);
    int incrementInt(const std::string& key, int delta = 1);

    void seedFromDefaults();
};

}  // namespace pipela::core::state
