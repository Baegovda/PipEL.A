#include "pipela/core/state/app_state.hpp"

#include <unordered_map>

namespace pipela::core::state {

namespace {

using GetterFn = StateValue (*)(const AppState&);
using SetterFn = bool (*)(AppState&, const StateValue&);

template <typename Group, typename Field>
GetterFn makeGetter(Group AppState::* group, Field Group::* field) {
    return [group, field](const AppState& s) -> StateValue { return StateValue{(s.*group).*field}; };
}

template <typename Group, typename Field>
SetterFn makeSetter(Group AppState::* group, Field Group::* field) {
    return [group, field](AppState& s, const StateValue& v) -> bool {
        if (const auto* p = std::get_if<Field>(&v)) {
            (s.*group).*field = *p;
            return true;
        }
        return false;
    };
}

struct KeyOps {
    GetterFn get;
    SetterFn set;
};

const std::unordered_map<std::string, KeyOps>& keyOps() {
    static const std::unordered_map<std::string, KeyOps> table = {
        {"left_click_feature_enabled",
         {makeGetter(&AppState::input, &InputState::left_click_feature_enabled),
          makeSetter(&AppState::input, &InputState::left_click_feature_enabled)}},
        {"left_click_active",
         {makeGetter(&AppState::input, &InputState::left_click_active),
          makeSetter(&AppState::input, &InputState::left_click_active)}},
        {"right_hold_active",
         {makeGetter(&AppState::input, &InputState::right_hold_active),
          makeSetter(&AppState::input, &InputState::right_hold_active)}},
        {"left_pressed",
         {makeGetter(&AppState::input, &InputState::left_pressed),
          makeSetter(&AppState::input, &InputState::left_pressed)}},
        {"left_click_id",
         {makeGetter(&AppState::input, &InputState::left_click_id),
          makeSetter(&AppState::input, &InputState::left_click_id)}},
        {"flame_trigger_active",
         {makeGetter(&AppState::input, &InputState::flame_trigger_active),
          makeSetter(&AppState::input, &InputState::flame_trigger_active)}},
        {"reload_active",
         {makeGetter(&AppState::input, &InputState::reload_active),
          makeSetter(&AppState::input, &InputState::reload_active)}},
        {"ammo_restock_active",
         {makeGetter(&AppState::input, &InputState::ammo_restock_active),
          makeSetter(&AppState::input, &InputState::ammo_restock_active)}},
        {"running",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::running),
          makeSetter(&AppState::worker, &WorkerRuntimeState::running)}},
        {"target_hwnd",
         {[](const AppState& s) -> StateValue {
              return StateValue{static_cast<std::int64_t>(s.worker.target_hwnd)};
          },
          [](AppState& s, const StateValue& v) -> bool {
              if (const auto* i = std::get_if<int>(&v)) {
                  s.worker.target_hwnd = *i;
                  return true;
              }
              if (const auto* l = std::get_if<std::int64_t>(&v)) {
                  s.worker.target_hwnd = static_cast<std::intptr_t>(*l);
                  return true;
              }
              return false;
          }}},
        {"select_mode",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::select_mode),
          makeSetter(&AppState::worker, &WorkerRuntimeState::select_mode)}},
        {"reload_success_count",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::reload_success_count),
          makeSetter(&AppState::worker, &WorkerRuntimeState::reload_success_count)}},
        {"ammo_restock_loop_count",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_loop_count),
          makeSetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_loop_count)}},
        {"kill_counter_enabled",
         {makeGetter(&AppState::kill_counter, &KillCounterState::kill_counter_enabled),
          makeSetter(&AppState::kill_counter, &KillCounterState::kill_counter_enabled)}},
        {"kill_counter_session_carried_kills",
         {makeGetter(&AppState::kill_counter, &KillCounterState::kill_counter_session_carried_kills),
          makeSetter(&AppState::kill_counter, &KillCounterState::kill_counter_session_carried_kills)}},
        {"flame_trigger_session_reload_count",
         {makeGetter(&AppState::input, &InputState::flame_trigger_session_reload_count),
          makeSetter(&AppState::input, &InputState::flame_trigger_session_reload_count)}},
        {"flame_trigger_reload_teardown_preserve_hud",
         {makeGetter(&AppState::input, &InputState::flame_trigger_reload_teardown_preserve_hud),
          makeSetter(&AppState::input, &InputState::flame_trigger_reload_teardown_preserve_hud)}},
        {"reload_nobullet_arm_until_mono",
         {makeGetter(&AppState::input, &InputState::reload_nobullet_arm_until_mono),
          makeSetter(&AppState::input, &InputState::reload_nobullet_arm_until_mono)}},
        {"hp_refill_detection_score",
         {makeGetter(&AppState::input, &InputState::hp_refill_detection_score),
          makeSetter(&AppState::input, &InputState::hp_refill_detection_score)}},
        {"hp_refill_trigger_total",
         {makeGetter(&AppState::input, &InputState::hp_refill_trigger_total),
          makeSetter(&AppState::input, &InputState::hp_refill_trigger_total)}},
        {"nobullet_detected",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::nobullet_detected),
          makeSetter(&AppState::worker, &WorkerRuntimeState::nobullet_detected)}},
        {"nobullet_detection_score",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::nobullet_detection_score),
          makeSetter(&AppState::worker, &WorkerRuntimeState::nobullet_detection_score)}},
        {"bullet_detection_score",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::bullet_detection_score),
          makeSetter(&AppState::worker, &WorkerRuntimeState::bullet_detection_score)}},
        {"vault_detection_score",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::vault_detection_score),
          makeSetter(&AppState::worker, &WorkerRuntimeState::vault_detection_score)}},
        {"reload_ammo_count",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::reload_ammo_count),
          makeSetter(&AppState::worker, &WorkerRuntimeState::reload_ammo_count)}},
        {"last_nobullet_time",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::last_nobullet_time),
          makeSetter(&AppState::worker, &WorkerRuntimeState::last_nobullet_time)}},
        {"ammo_restock_toggle_key_code",
         {makeGetter(&AppState::input, &InputState::ammo_restock_toggle_key_code),
          makeSetter(&AppState::input, &InputState::ammo_restock_toggle_key_code)}},
        {"flame_trigger_start_time",
         {makeGetter(&AppState::input, &InputState::flame_trigger_start_time),
          makeSetter(&AppState::input, &InputState::flame_trigger_start_time)}},
        {"flame_trigger_press_text_until",
         {makeGetter(&AppState::input, &InputState::flame_trigger_press_text_until),
          makeSetter(&AppState::input, &InputState::flame_trigger_press_text_until)}},
        {"flame_trigger_press_key_name",
         {makeGetter(&AppState::input, &InputState::flame_trigger_press_key_name),
          makeSetter(&AppState::input, &InputState::flame_trigger_press_key_name)}},
        {"flame_trigger_press_count",
         {makeGetter(&AppState::input, &InputState::flame_trigger_press_count),
          makeSetter(&AppState::input, &InputState::flame_trigger_press_count)}},
        {"flame_trigger_last_press_interval_sec",
         {makeGetter(&AppState::input, &InputState::flame_trigger_last_press_interval_sec),
          makeSetter(&AppState::input, &InputState::flame_trigger_last_press_interval_sec)}},
        {"flame_trigger_hud_session_start_time",
         {makeGetter(&AppState::input, &InputState::flame_trigger_hud_session_start_time),
          makeSetter(&AppState::input, &InputState::flame_trigger_hud_session_start_time)}},
        {"flame_trigger_last_reload_complete_time",
         {makeGetter(&AppState::input, &InputState::flame_trigger_last_reload_complete_time),
          makeSetter(&AppState::input, &InputState::flame_trigger_last_reload_complete_time)}},
        {"flame_trigger_last_reload_trigger_time",
         {makeGetter(&AppState::input, &InputState::flame_trigger_last_reload_trigger_time),
          makeSetter(&AppState::input, &InputState::flame_trigger_last_reload_trigger_time)}},
        {"ammo_restock_buybutton_score",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_buybutton_score),
          makeSetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_buybutton_score)}},
        {"ammo_restock_inven_score",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_inven_score),
          makeSetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_inven_score)}},
        {"ammo_restock_bank_score",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_bank_score),
          makeSetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_bank_score)}},
        {"kill_counter_last_progress",
         {makeGetter(&AppState::kill_counter, &KillCounterState::kill_counter_last_progress),
          makeSetter(&AppState::kill_counter, &KillCounterState::kill_counter_last_progress)}},
        {"kill_counter_last_poll_ts",
         {makeGetter(&AppState::kill_counter, &KillCounterState::kill_counter_last_poll_ts),
          makeSetter(&AppState::kill_counter, &KillCounterState::kill_counter_last_poll_ts)}},
        {"ammo_restock_sequence_busy",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_sequence_busy),
          makeSetter(&AppState::worker, &WorkerRuntimeState::ammo_restock_sequence_busy)}},
        {"call_merc_sequence_busy",
         {makeGetter(&AppState::worker, &WorkerRuntimeState::call_merc_sequence_busy),
          makeSetter(&AppState::worker, &WorkerRuntimeState::call_merc_sequence_busy)}},
    };
    return table;
}

}  // namespace

bool AppState::has(const std::string& key) const { return keyOps().count(key) > 0; }

std::optional<StateValue> AppState::get(const std::string& key) const {
    const auto it = keyOps().find(key);
    if (it == keyOps().end()) {
        return std::nullopt;
    }
    return it->second.get(*this);
}

bool AppState::set(const std::string& key, const StateValue& value) {
    const auto it = keyOps().find(key);
    if (it == keyOps().end()) {
        return false;
    }
    return it->second.set(*this, value);
}

int AppState::incrementInt(const std::string& key, int delta) {
    auto cur = get(key);
    int base = 0;
    if (cur) {
        if (const auto* i = std::get_if<int>(&*cur)) {
            base = *i;
        } else if (const auto* l = std::get_if<std::int64_t>(&*cur)) {
            base = static_cast<int>(*l);
        }
    }
    const int next = base + delta;
    set(key, StateValue{next});
    return next;
}

void AppState::seedFromDefaults() {
    input = InputState{};
    worker = WorkerRuntimeState{};
    kill_counter = KillCounterState{};
}

}  // namespace pipela::core::state
