#include <catch2/catch_approx.hpp>
#include <catch2/catch_test_macros.hpp>

#include "pipela/core/registry/parse.hpp"

TEST_CASE("parse_bool parity", "[registry]") {
    using pipela::core::registry::parseBool;
    REQUIRE(parseBool("1") == true);
    REQUIRE(parseBool("true") == true);
    REQUIRE(parseBool("on") == true);
    REQUIRE(parseBool("0") == false);
    REQUIRE(parseBool("false") == false);
    REQUIRE(parseBool("") == false);
}

TEST_CASE("clamp_match_threshold", "[registry]") {
    using pipela::core::registry::clampMatchThreshold01;
    REQUIRE(clampMatchThreshold01(0.0) == Catch::Approx(0.1));
    REQUIRE(clampMatchThreshold01(0.5) == Catch::Approx(0.5));
    REQUIRE(clampMatchThreshold01(2.0) == Catch::Approx(1.0));
}
