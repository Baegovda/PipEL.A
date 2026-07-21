#pragma once

namespace pipela::core::state {
class AppState;
}

namespace pipela::core::kill_counter {

int sessionTotalKillsDisplay(const state::AppState& state);
void resetSessionKills(state::AppState& state);
bool ocrN1Plausible(const state::AppState& state, int n1);
void updateSessionFromN1(state::AppState& state, int n1);
void onOcrN1Accepted(state::AppState& state, int n1, bool allow_large_jump = false);

}  // namespace pipela::core::kill_counter
