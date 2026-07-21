#include <catch2/catch_test_macros.hpp>

#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"

TEST_CASE("registry bool round-trip", "[golden][registry]") {
    REQUIRE(pipela::core::registry::saveBoolValue("cpp_golden_test_flag", true));
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find("cpp_golden_test_flag");
    REQUIRE(it != all.end());
    REQUIRE(it->second == "true");
    REQUIRE(pipela::core::registry::parseBool(it->second));
    REQUIRE(pipela::core::registry::saveBoolValue("cpp_golden_test_flag", false));
    const auto all2 = pipela::core::registry::loadAllStringValues();
    const auto it2 = all2.find("cpp_golden_test_flag");
    REQUIRE(it2 != all2.end());
    REQUIRE(it2->second == "false");
}
