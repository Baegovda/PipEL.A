#include "dock/dock_chrome_apply.hpp"

#include <algorithm>
#include <cmath>
#include <unordered_map>

#include <QWidget>

#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/window_ops.hpp"

namespace pipela::app::dock {

namespace {

constexpr int kGeomDeadbandPx = 1;

struct AppliedDockGeometry {
    int x_log{0};
    int y_log{0};
    int w_log{0};
    int h_log{0};
    int x_phys{0};
    int y_phys{0};
    int fw_phys{0};
    int fh_phys{0};
};

std::unordered_map<const QWidget*, AppliedDockGeometry> g_last_applied;

bool withinDeadband(int a, int b) { return std::abs(a - b) <= kGeomDeadbandPx; }

bool sameAppliedGeometry(const AppliedDockGeometry& a, const AppliedDockGeometry& b) {
    return withinDeadband(a.x_log, b.x_log) && withinDeadband(a.y_log, b.y_log) &&
           withinDeadband(a.w_log, b.w_log) && withinDeadband(a.h_log, b.h_log) &&
           withinDeadband(a.x_phys, b.x_phys) && withinDeadband(a.y_phys, b.y_phys) &&
           withinDeadband(a.fw_phys, b.fw_phys) && withinDeadband(a.fh_phys, b.fh_phys);
}

void pinLogicalToClientInner(int& y_log, int& h_log, const AnchorClientRects& rects, double scale) {
    if (!rects.clientValid()) {
        return;
    }
    const double sc = scale > 0.01 ? scale : 1.0;
    y_log = static_cast<int>(std::lround(static_cast<double>(rects.client_top) / sc));
    const int cap_log =
        std::max(8, static_cast<int>(std::lround(static_cast<double>(rects.clientInnerHeightPhys()) / sc)));
    h_log = std::min(h_log, cap_log);
}

bool applyDockGeometry(QWidget* widget,
                       int x_log,
                       int y_log,
                       int w_log,
                       int h_log,
                       int x_phys,
                       int y_phys,
                       int fw_phys,
                       int fh_phys,
                       std::intptr_t anchor_hwnd) {
    if (widget == nullptr || w_log < 8 || h_log < 8 || fw_phys < 8 || fh_phys < 8) {
        return false;
    }

    std::tie(x_log, y_log, w_log, h_log) = clampDockLogicalGeometry(x_log, y_log, w_log, h_log);

    const AppliedDockGeometry next{x_log, y_log, w_log, h_log, x_phys, y_phys, fw_phys, fh_phys};
    const auto it = g_last_applied.find(widget);
    if (it != g_last_applied.end() && sameAppliedGeometry(it->second, next)) {
        if (!widget->isVisible()) {
            widget->show();
        }
        return true;
    }

    widget->setFixedWidth(w_log);
    widget->setFixedHeight(h_log);
    widget->setGeometry(x_log, y_log, w_log, h_log);
    if (!widget->isVisible()) {
        widget->show();
    }

    const std::intptr_t hwnd = static_cast<std::intptr_t>(widget->winId());
    if (hwnd && pipela::core::win32::isWindow(hwnd)) {
        pipela::core::win32::setWindowOuterRect(hwnd, x_phys, y_phys, fw_phys, fh_phys);
        if (anchor_hwnd && pipela::core::win32::isWindow(anchor_hwnd)) {
            pipela::core::win32::setWindowOwner(hwnd, anchor_hwnd);
        }
    }

    g_last_applied[widget] = next;
    return true;
}

}  // namespace

bool applySideDockLayoutToWidget(QWidget* widget,
                                   const SideDockLayout& layout,
                                   std::intptr_t anchor_hwnd) {
    return applySideDockLayoutWithHeightCap(widget, layout, anchor_hwnd, 0);
}

bool applySideDockLayoutWithHeightCap(QWidget* widget,
                                      const SideDockLayout& layout,
                                      std::intptr_t anchor_hwnd,
                                      int max_inner_height_log) {
    if (widget == nullptr || !layout.valid()) {
        return false;
    }

    int x_log = layout.x_log;
    int y_log = layout.y_log;
    int w_log = layout.w_log;
    int h_log = layout.h_log;
    int x_phys = layout.x_phys;
    int y_phys = layout.y_phys;
    int fw_phys = layout.fw_phys;
    int fh_phys = layout.fh_phys;
    const double scale = layout.scale > 0.01 ? layout.scale : 1.0;

    if (max_inner_height_log > 0) {
        h_log = std::min(h_log, max_inner_height_log);
        const int cap_phys = std::max(8, static_cast<int>(std::lround(max_inner_height_log * scale)));
        fh_phys = std::min(fh_phys, cap_phys);
    }

    if (anchor_hwnd && pipela::core::win32::isWindow(anchor_hwnd)) {
        if (const auto rects = readAnchorClientRects(anchor_hwnd)) {
            pinLogicalToClientInner(y_log, h_log, *rects, scale);
            std::tie(y_phys, fh_phys) = clampToClientInnerPhys(y_phys, fh_phys, *rects);
            h_log = std::min(
                h_log, std::max(8, static_cast<int>(std::lround(static_cast<double>(fh_phys) / scale))));
            y_log = static_cast<int>(std::lround(static_cast<double>(y_phys) / scale));
        }
    }

    return applyDockGeometry(widget, x_log, y_log, w_log, h_log, x_phys, y_phys, fw_phys, fh_phys,
                             anchor_hwnd);
}

}  // namespace pipela::app::dock
