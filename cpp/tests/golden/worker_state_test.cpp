#include <catch2/catch_test_macros.hpp>

#include "pipela/core/state/app_state.hpp"
#include "pipela/core/win32/game_windows.hpp"

TEST_CASE("AppState start_game and kill_counter keys") {
    pipela::core::state::AppState state;
    state.seedFromDefaults();
    REQUIRE(state.has("start_game_launcher_score"));
    REQUIRE(state.has("kill_counter_last_poll_phase"));
    REQUIRE(state.set("start_game_launcher_loop_count", pipela::core::state::StateValue{3}));
    const auto v = state.get("start_game_launcher_loop_count");
    REQUIRE(v.has_value());
    if (const auto* i = std::get_if<int>(&*v)) {
        REQUIRE(*i == 3);
    }
}

TEST_CASE("Smart updater title matcher") {
    REQUIRE(pipela::core::win32::smartUpdaterTitleMatches(L"Smart Updater", L"\uc2a4\ub9c8\ud2b8"));
    REQUIRE(pipela::core::win32::eternalcityTitleMatches(L"EternalCity Client"));
}
