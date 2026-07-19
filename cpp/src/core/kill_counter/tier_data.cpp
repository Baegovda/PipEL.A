#include "pipela/core/kill_counter/tier_data.hpp"

#include "tier_data.generated.hpp"

namespace pipela::core::kill_counter {

std::vector<TierRow> builtinRankTableRows() {
    std::vector<TierRow> rows;
    rows.reserve(static_cast<size_t>(kRankTierCount));
    for (int i = 0; i < kRankTierCount; ++i) {
        TierRow row;
        row.num = i;
        row.title = kRankTitles[i];
        row.point = kRankPoints[i];
        row.next_cap = (i + 1 < kRankTierCount) ? std::optional<int>(kRankPoints[i + 1]) : std::nullopt;
        rows.push_back(std::move(row));
    }
    return rows;
}

int rankTierCount() { return kRankTierCount; }

}  // namespace pipela::core::kill_counter
