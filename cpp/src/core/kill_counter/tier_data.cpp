#include "pipela/core/kill_counter/tier_data.hpp"

namespace pipela::core::kill_counter {

std::vector<TierRow> builtinRankTableRows() {
    // AGENT: subset seed — full table ported from kill_counter_tier_data.py in Phase 1 follow-up.
    return {
        {"견습", 0},
        {"초보", 100},
        {"숙련", 500},
        {"베테랑", 2000},
        {"달인", 5000},
    };
}

}  // namespace pipela::core::kill_counter
