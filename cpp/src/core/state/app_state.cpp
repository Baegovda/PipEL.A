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
