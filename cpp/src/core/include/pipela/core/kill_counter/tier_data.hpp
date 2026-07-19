#pragma once

#include <string>
#include <vector>

namespace pipela::core::kill_counter {

struct TierRow {
    std::string honorific;
    int monster_kills{0};
};

std::vector<TierRow> builtinRankTableRows();

}  // namespace pipela::core::kill_counter
