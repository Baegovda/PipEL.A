#pragma once

#include <optional>
#include <string>
#include <vector>

namespace pipela::core::kill_counter {

struct TierRow {
    int num{0};
    std::string title;
    int point{0};
    std::optional<int> next_cap;
};

std::vector<TierRow> builtinRankTableRows();
int rankTierCount();

}  // namespace pipela::core::kill_counter
