#include <catch2/catch_test_macros.hpp>

#include "dock/side_dock_layout.hpp"
#include "pipela/core/win32/dock_layout.hpp"

TEST_CASE("clamp_dock_logical_geometry", "[dock]") {
    auto [x, y, w, h] = pipela::core::win32::clampDockLogicalGeometry(0, 0, 4, 4);
    REQUIRE(w == 8);
    REQUIRE(h == 8);
    REQUIRE(x == 0);
    REQUIRE(y == 0);
}

TEST_CASE("compute_side_dock_layout_right", "[dock]") {
    pipela::app::dock::AnchorClientRects rects;
    rects.client_left = 100;
    rects.client_top = 50;
    rects.client_right = 900;
    rects.client_bottom = 650;
    rects.outer_left = rects.client_left;
    rects.outer_top = rects.client_top;
    rects.outer_right = rects.client_right;
    rects.outer_bottom = rects.client_bottom;
    const auto layout = pipela::app::dock::computeSideDockLayoutRight(
        0, rects, 320, 1.25, pipela::app::dock::DockHeightPolicy::ClientOrOuterFallback);
    REQUIRE(layout.has_value());
    REQUIRE(layout->x_phys == 900);
    REQUIRE(layout->y_phys == 50);
    REQUIRE(layout->fh_phys == 600);
    REQUIRE(layout->w_log == 320);
}

TEST_CASE("kill_counter_height_never_exceeds_client_inner", "[dock]") {
    pipela::app::dock::AnchorClientRects rects;
    rects.client_left = 100;
    rects.client_top = 50;
    rects.client_right = 900;
    rects.client_bottom = 650;
    rects.outer_left = 80;
    rects.outer_top = 20;
    rects.outer_right = 920;
    rects.outer_bottom = 680;
    const auto layout = pipela::app::dock::computeSideDockLayoutRight(
        0, rects, 320, 1.25, pipela::app::dock::DockHeightPolicy::ClientInnerOnly);
    REQUIRE(layout.has_value());
    REQUIRE(layout->y_phys == 50);
    REQUIRE(layout->fh_phys == 600);
    REQUIRE(layout->fh_phys <= rects.client_bottom - rects.client_top);
}
