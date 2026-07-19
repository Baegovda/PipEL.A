#include <catch2/catch_test_macros.hpp>

#include "pipela/core/kill_counter/tier_data.hpp"
#include "pipela/core/paths.hpp"
#include "pipela/core/registry/store.hpp"

TEST_CASE("kill_counter tier row count", "[kill_counter]") {
    REQUIRE(pipela::core::kill_counter::rankTierCount() == 51);
    const auto rows = pipela::core::kill_counter::builtinRankTableRows();
    REQUIRE(rows.size() == 51u);
    REQUIRE(rows.front().point == 0);
    REQUIRE(rows.back().point == 33000000);
    REQUIRE_FALSE(rows.back().next_cap.has_value());
}

TEST_CASE("registry schema load", "[registry]") {
    const auto doc = pipela::core::registry::loadSchemaFromFile(pipela::core::registrySchemaPath());
    REQUIRE(doc.schema_version == 1);
    REQUIRE(doc.entry_count >= 100);
    REQUIRE(doc.entries.size() == static_cast<size_t>(doc.entry_count));
}
