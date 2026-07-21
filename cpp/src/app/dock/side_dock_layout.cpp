#include "dock/side_dock_layout.hpp"

#include <algorithm>
#include <cmath>

#include <QGuiApplication>
#include <QScreen>

#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/window_ops.hpp"

#include "dock/dock_panel_pair_resize.hpp"

namespace pipela::app::dock {

namespace {

void syncLogicalFromPhysical(SideDockLayout& out) {
    const double scale = out.scale > 0.01 ? out.scale : 1.0;
    out.fw_phys = std::max(8, out.fw_phys);
    out.fh_phys = std::max(8, out.fh_phys);
    out.w_log = std::max(8, static_cast<int>(std::lround(static_cast<double>(out.fw_phys) / scale)));
    out.h_log = std::max(8, static_cast<int>(std::lround(static_cast<double>(out.fh_phys) / scale)));
    out.x_log = static_cast<int>(std::lround(static_cast<double>(out.x_phys) / scale));
    out.y_log = static_cast<int>(std::lround(static_cast<double>(out.y_phys) / scale));
}

int resolveClientInnerHeightPhys(const AnchorClientRects& rects, DockHeightPolicy policy) {
    if (rects.clientValid()) {
        return rects.clientInnerHeightPhys();
    }
    if (policy == DockHeightPolicy::ClientOrOuterFallback) {
        return std::max(8, rects.outer_bottom - rects.outer_top);
    }
    return 0;
}

}  // namespace

std::pair<int, int> clampToClientInnerPhys(int y_phys, int fh_phys, const AnchorClientRects& rects) {
    if (!rects.clientValid()) {
        return {y_phys, fh_phys};
    }
    const int y = rects.client_top;
    int h = std::min(std::max(8, fh_phys), rects.clientInnerHeightPhys());
    h = std::min(h, std::max(8, rects.client_bottom - y));
    return {y, h};
}

namespace {

int clampHeightToClientInner(int y_phys, int fh_phys, const AnchorClientRects& rects) {
    return clampToClientInnerPhys(y_phys, fh_phys, rects).second;
}

}  // namespace

std::tuple<int, int, int, int> clampDockLogicalGeometry(int x, int y, int w, int h) {
    w = std::clamp(w, 8, 8192);
    h = std::clamp(h, 8, 16384);
    try {
        if (QScreen* scr = QGuiApplication::primaryScreen()) {
            const QRect ag = scr->availableGeometry();
            constexpr int kMargin = 32000;
            const int xa = ag.x() - kMargin;
            const int ya = ag.y() - kMargin;
            const int xr = ag.x() + ag.width() + kMargin;
            const int yr = ag.y() + ag.height() + kMargin;
            x = std::max(xa, std::min(x, xr - w));
            y = std::max(ya, std::min(y, yr - h));
        }
    } catch (...) {
    }
    x = std::clamp(x, -65535, 65535);
    y = std::clamp(y, -65535, 65535);
    return {x, y, w, h};
}

bool chromeOuterRectPlausibleForLeftDock(int chrome_left,
                                         int chrome_top,
                                         int chrome_right,
                                         int chrome_bottom,
                                         int client_left,
                                         int client_top,
                                         int client_right,
                                         int client_bottom,
                                         int tol_phys) {
    (void)chrome_left;
    (void)chrome_top;
    (void)chrome_bottom;
    (void)client_top;
    (void)client_right;
    (void)client_bottom;
    return std::abs(chrome_right - client_left) <= tol_phys;
}

std::uint64_t sideDockDedupeSig(int snap,
                                int ol,
                                int ot,
                                int o_right,
                                int ob,
                                int x_phys,
                                int y_phys,
                                int fw_phys,
                                int fh_phys,
                                bool right_side) {
    std::uint64_t sig = static_cast<std::uint64_t>(snap & 0xffff);
    sig ^= static_cast<std::uint64_t>(ol & 0xffff) << 16;
    sig ^= static_cast<std::uint64_t>(ot & 0xffff) << 32;
    sig ^= static_cast<std::uint64_t>(o_right & 0xffff) << 48;
    sig ^= static_cast<std::uint64_t>(ob & 0xff) << 8;
    sig ^= static_cast<std::uint64_t>(x_phys & 0xffff) * 1315423911u;
    sig ^= static_cast<std::uint64_t>(y_phys & 0xffff) * 2654435761u;
    sig ^= static_cast<std::uint64_t>(fw_phys & 0xffff) * 2246822519u;
    sig ^= static_cast<std::uint64_t>(fh_phys & 0xffff) * 3266489917u;
    if (right_side) {
        sig ^= 0x9e3779b97f4a7c15ULL;
    }
    return sig;
}

std::optional<AnchorClientRects> readAnchorClientRects(std::intptr_t anchor_hwnd) {
    if (!anchor_hwnd || !pipela::core::win32::isWindow(anchor_hwnd)) {
        return std::nullopt;
    }
    AnchorClientRects rects;
    const auto cr = pipela::core::win32::getClientRectScreen(anchor_hwnd);
    rects.client_left = std::get<0>(cr);
    rects.client_top = std::get<1>(cr);
    rects.client_right = std::get<2>(cr);
    rects.client_bottom = std::get<3>(cr);
    const auto gr = pipela::core::win32::getWindowOuterRectScreen(anchor_hwnd);
    rects.outer_left = std::get<0>(gr);
    rects.outer_top = std::get<1>(gr);
    rects.outer_right = std::get<2>(gr);
    rects.outer_bottom = std::get<3>(gr);
    if (!rects.clientValid()) {
        rects.client_left = rects.outer_left;
        rects.client_top = rects.outer_top;
        rects.client_right = rects.outer_right;
        rects.client_bottom = rects.outer_bottom;
    }
    return rects;
}

std::optional<int> anchorClientInnerHeightLogical(std::intptr_t anchor_hwnd, double scale) {
    const auto rects = readAnchorClientRects(anchor_hwnd);
    if (!rects || !rects->clientValid()) {
        return std::nullopt;
    }
    if (scale <= 0.01) {
        scale = 1.0;
    }
    return std::max(8, static_cast<int>(
                            std::lround(static_cast<double>(rects->clientInnerHeightPhys()) / scale)));
}

std::optional<int> computeDockPairFillWLog(std::intptr_t anchor_hwnd, double scale) {
    const auto rects = readAnchorClientRects(anchor_hwnd);
    if (!rects || !rects->clientValid()) {
        return std::nullopt;
    }
    const auto work = pipela::core::win32::getMonitorWorkRectPhys(anchor_hwnd);
    if (!work) {
        return std::nullopt;
    }
    const int wl = std::get<0>(*work);
    const int wr = std::get<2>(*work);
    const int space_left = rects->client_left - wl;
    const int space_right = wr - rects->client_right;
    const int w_phys = std::min(std::max(8, space_left), std::max(8, space_right));
    if (w_phys < 8) {
        return std::nullopt;
    }
    if (scale <= 0.01) {
        scale = 1.0;
    }
    const int w_log = static_cast<int>(std::lround(static_cast<double>(w_phys) / scale));
    return std::max(kDockPairPanelWMin, std::min(w_log, 8192));
}

std::optional<SideDockLayout> computeSideDockLayoutLeft(std::intptr_t anchor_hwnd,
                                                        const AnchorClientRects& rects,
                                                        int dock_w_log,
                                                        double scale,
                                                        DockHeightPolicy height_policy) {
    if (scale <= 0.01) {
        scale = 1.0;
    }
    dock_w_log = std::max(8, dock_w_log);
    const int fh_target = resolveClientInnerHeightPhys(rects, height_policy);
    if (fh_target < 8) {
        return std::nullopt;
    }
    SideDockLayout out;
    out.scale = scale;
    int fh_phys = fh_target;
    int y_phys = rects.clientValid() ? rects.client_top : rects.outer_top;
    std::tie(y_phys, fh_phys) = clampToClientInnerPhys(y_phys, fh_phys, rects);
    int fw_phys = std::max(8, static_cast<int>(std::lround(dock_w_log * scale)));
    const int snap = rects.clientValid() ? rects.client_left : rects.outer_left;
    int x_phys = snap - fw_phys;
    if (anchor_hwnd && pipela::core::win32::isWindow(anchor_hwnd)) {
        const auto touched = pipela::core::win32::dockOuterRectTouchClientLeft(
            anchor_hwnd, snap, y_phys, fw_phys, fh_phys);
        x_phys = std::get<0>(touched);
        y_phys = std::get<1>(touched);
        fw_phys = std::get<2>(touched);
        fh_phys = std::get<3>(touched);
    }
    std::tie(y_phys, fh_phys) = clampToClientInnerPhys(y_phys, fh_phys, rects);
    out.x_phys = x_phys;
    out.y_phys = y_phys;
    out.fw_phys = fw_phys;
    out.fh_phys = fh_phys;
    syncLogicalFromPhysical(out);
    out.dedupe_sig = sideDockDedupeSig(snap, rects.outer_left, rects.outer_top, rects.outer_right,
                                       rects.outer_bottom, out.x_phys, out.y_phys, out.fw_phys,
                                       out.fh_phys, false);
    return out;
}

std::optional<SideDockLayout> computeSideDockLayoutRight(std::intptr_t anchor_hwnd,
                                                         const AnchorClientRects& rects,
                                                         int dock_w_log,
                                                         double scale,
                                                         DockHeightPolicy height_policy) {
    if (scale <= 0.01) {
        scale = 1.0;
    }
    dock_w_log = std::max(8, dock_w_log);
    const int fh_target = resolveClientInnerHeightPhys(rects, height_policy);
    if (fh_target < 8) {
        return std::nullopt;
    }
    SideDockLayout out;
    out.scale = scale;
    int fh_phys = fh_target;
    int y_phys = rects.clientValid() ? rects.client_top : rects.outer_top;
    std::tie(y_phys, fh_phys) = clampToClientInnerPhys(y_phys, fh_phys, rects);
    int fw_phys = std::max(8, static_cast<int>(std::lround(dock_w_log * scale)));
    const int snap = rects.clientValid() ? rects.client_right : rects.outer_right;
    int x_phys = snap;
    if (anchor_hwnd && pipela::core::win32::isWindow(anchor_hwnd)) {
        const auto touched = pipela::core::win32::dockOuterRectTouchClientRight(
            anchor_hwnd, snap, y_phys, fw_phys, fh_phys);
        x_phys = std::get<0>(touched);
        y_phys = std::get<1>(touched);
        fw_phys = std::get<2>(touched);
        fh_phys = std::get<3>(touched);
    }
    std::tie(y_phys, fh_phys) = clampToClientInnerPhys(y_phys, fh_phys, rects);
    out.x_phys = x_phys;
    out.y_phys = y_phys;
    out.fw_phys = fw_phys;
    out.fh_phys = fh_phys;
    syncLogicalFromPhysical(out);
    out.dedupe_sig = sideDockDedupeSig(snap, rects.outer_left, rects.outer_top, rects.outer_right,
                                       rects.outer_bottom, out.x_phys, out.y_phys, out.fw_phys,
                                       out.fh_phys, true);
    return out;
}

SideDockLayout computeSideDockLayoutLeft(int client_left,
                                         int client_top,
                                         int client_right,
                                         int client_bottom,
                                         int dock_w_log,
                                         double scale) {
    AnchorClientRects rects;
    rects.client_left = client_left;
    rects.client_top = client_top;
    rects.client_right = client_right;
    rects.client_bottom = client_bottom;
    rects.outer_left = client_left;
    rects.outer_top = client_top;
    rects.outer_right = client_right;
    rects.outer_bottom = client_bottom;
    if (auto lay = computeSideDockLayoutLeft(0, rects, dock_w_log, scale,
                                             DockHeightPolicy::ClientOrOuterFallback)) {
        return *lay;
    }
    return SideDockLayout{};
}

SideDockLayout computeSideDockLayoutRight(int client_left,
                                          int client_top,
                                          int client_right,
                                          int client_bottom,
                                          int dock_w_log,
                                          double scale) {
    AnchorClientRects rects;
    rects.client_left = client_left;
    rects.client_top = client_top;
    rects.client_right = client_right;
    rects.client_bottom = client_bottom;
    rects.outer_left = client_left;
    rects.outer_top = client_top;
    rects.outer_right = client_right;
    rects.outer_bottom = client_bottom;
    if (auto lay = computeSideDockLayoutRight(0, rects, dock_w_log, scale,
                                              DockHeightPolicy::ClientOrOuterFallback)) {
        return *lay;
    }
    return SideDockLayout{};
}

}  // namespace pipela::app::dock
