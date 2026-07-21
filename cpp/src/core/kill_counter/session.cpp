#include "pipela/core/kill_counter/session.hpp"

#include <algorithm>

#include "pipela/core/kill_counter/goal_display.hpp"
#include "pipela/core/kill_counter/stats_store.hpp"
#include "pipela/core/kill_counter/tier_data.hpp"
#include "pipela/core/state/app_state.hpp"

namespace pipela::core::kill_counter {

namespace {

constexpr int kOcrMaxDeltaPerPoll = 3500;
constexpr int kOcrMaxUnanchoredN1 = 500000;

int stateInt(const state::AppState& state, const char* key, int fallback) {
    const auto v = state.get(key);
    if (!v || !std::holds_alternative<int>(*v)) {
        return fallback;
    }
    return std::get<int>(*v);
}

void setInt(state::AppState& state, const char* key, int value) {
    state.set(key, state::StateValue{value});
}

}  // namespace

int sessionTotalKillsDisplay(const state::AppState& state) {
    const int baseline = stateInt(state, "kill_counter_session_baseline_n1", -1);
    if (baseline < 0) {
        return 0;
    }
    const int last = stateInt(state, "kill_counter_session_last_n1", baseline);
    const int carried = stateInt(state, "kill_counter_session_carried_kills", 0);
    return carried + std::max(0, last - baseline);
}

void resetSessionKills(state::AppState& state) {
    setInt(state, "kill_counter_session_baseline_n1", -1);
    setInt(state, "kill_counter_session_last_n1", -1);
    setInt(state, "kill_counter_session_carried_kills", 0);
}

bool ocrN1Plausible(const state::AppState& state, int n1) {
    if (n1 < 0) {
        return false;
    }
    const auto rows = builtinRankTableRows();
    if (!rows.empty() && n1 > rows.back().point * 2) {
        return false;
    }
    int prev = stateInt(state, "kill_counter_session_last_n1", -1);
    if (prev < 0) {
        prev = stateInt(state, "kill_counter_session_baseline_n1", -1);
    }
    if (prev < 0) {
        return n1 <= kOcrMaxUnanchoredN1;
    }
    if (n1 == prev) {
        return true;
    }
    if (n1 < prev) {
        return (prev - n1) <= kOcrMaxDeltaPerPoll;
    }
    return (n1 - prev) <= kOcrMaxDeltaPerPoll;
}

void updateSessionFromN1(state::AppState& state, int n1) {
    int baseline = stateInt(state, "kill_counter_session_baseline_n1", -1);
    int last = stateInt(state, "kill_counter_session_last_n1", -1);
    int carried = stateInt(state, "kill_counter_session_carried_kills", 0);

    if (baseline < 0) {
        setInt(state, "kill_counter_session_baseline_n1", n1);
        setInt(state, "kill_counter_session_last_n1", n1);
        return;
    }
    if (last < 0) {
        setInt(state, "kill_counter_session_last_n1", n1);
        return;
    }
    if (n1 < last && (last - n1) >= 2) {
        carried += std::max(0, last - baseline);
        setInt(state, "kill_counter_session_carried_kills", carried);
        setInt(state, "kill_counter_session_baseline_n1", n1);
        setInt(state, "kill_counter_session_last_n1", n1);
        return;
    }
    if (n1 < baseline && last >= baseline) {
        carried += std::max(0, last - baseline);
        setInt(state, "kill_counter_session_carried_kills", carried);
        setInt(state, "kill_counter_session_baseline_n1", n1);
        setInt(state, "kill_counter_session_last_n1", n1);
        return;
    }
    if (n1 < last && (last - n1) == 1) {
        return;
    }
    setInt(state, "kill_counter_session_last_n1", n1);
}

void onOcrN1Accepted(state::AppState& state, int n1, bool allow_large_jump) {
    const int before = sessionTotalKillsDisplay(state);
    updateSessionFromN1(state, n1);
    const int after = sessionTotalKillsDisplay(state);
    if (after > before) {
        statsRecordDelta(after - before, allow_large_jump);
    }
    statsReconcileWithN1(n1);
}

}  // namespace pipela::core::kill_counter
