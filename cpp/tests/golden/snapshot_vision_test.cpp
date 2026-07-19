#include <algorithm>

#include <catch2/catch_test_macros.hpp>

#include "pipela/core/registry/snapshot.hpp"
#include "pipela/core/vision/roi.hpp"

TEST_CASE("Registry snapshot builtin keys") {
    const auto keys = pipela::core::registry::RegistrySnapshot::builtinKeyNames();
    REQUIRE(keys.size() >= 80);
    REQUIRE(std::find(keys.begin(), keys.end(), "reload_active") != keys.end());
    REQUIRE(std::find(keys.begin(), keys.end(), "ride_feature_enabled") != keys.end());
}

TEST_CASE("Vision region pixels baseline scale") {
    const double ratio = pipela::core::vision::scaleRatio(1080);
    REQUIRE(ratio > 0.0);
    const double region[4] = {0.1, 0.2, 0.3, 0.4};
    const auto px = pipela::core::vision::regionPixels(1920, 1080, region);
    REQUIRE(px.has_value());
    REQUIRE((*px)[2] > 0);
    REQUIRE((*px)[3] > 0);
}

TEST_CASE("Registry snapshot typed getters") {
    pipela::core::registry::RegistrySnapshot snap;
    snap.setBool("reload_active", true);
    snap.setDouble("ride_threshold", 0.75);
    snap.setInt("reload_ammo_count", 45);
    REQUIRE(snap.snapshotBool("reload_active", false));
    REQUIRE(snap.snapshotFloat("ride_threshold", 0.0) == Approx(0.75));
    REQUIRE(snap.snapshotInt("reload_ammo_count", 0) == 45);
}
