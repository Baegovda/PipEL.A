#include <catch2/catch_test_macros.hpp>

#include "pipela/core/win32/dock_layout.hpp"

TEST_CASE("clamp_dock_logical_geometry", "[dock]") {
    auto [x, y, w, h] = pipela::core::win32::clampDockLogicalGeometry(0, 0, 4, 4);
    REQUIRE(w == 8);
    REQUIRE(h == 8);
    REQUIRE(x == 0);
    REQUIRE(y == 0);
}

TEST_CASE("compute_side_dock_layout_right", "[dock]") {
    auto layout = pipela::core::win32::computeSideDockLayoutRight(100, 50, 900, 650, 320, 1.25);
    REQUIRE(layout.x_phys == 900);
    REQUIRE(layout.y_phys == 50);
    REQUIRE(layout.fh_phys == 600);
    REQUIRE(layout.w_log == 320);
}
