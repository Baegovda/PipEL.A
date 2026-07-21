#include "theme/dpi_helpers.hpp"

#include <algorithm>
#include <cmath>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include "pipela/core/win32/game_windows.hpp"

namespace pipela::ui::theme {

double win32DpiScaleForHwnd(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!hwnd || !pipela::core::win32::isWindow(hwnd)) {
        return 1.0;
    }
    const HWND wh = reinterpret_cast<HWND>(hwnd);
    const UINT dpi = GetDpiForWindow(wh);
    if (dpi == 0) {
        return 1.0;
    }
    return std::max(0.01, static_cast<double>(dpi) / 96.0);
#else
    (void)hwnd;
    return 1.0;
#endif
}

QRect win32PhysicalScreenRectToQtOverlayGeometry(std::intptr_t anchor_hwnd, int x_phys,
                                                 int y_phys, int w_phys, int h_phys) {
    w_phys = std::max(1, w_phys);
    h_phys = std::max(1, h_phys);
    if (!anchor_hwnd) {
        return QRect(x_phys, y_phys, w_phys, h_phys);
    }
    const double sc = win32DpiScaleForHwnd(anchor_hwnd);
    if (sc <= 0.01) {
        return QRect(x_phys, y_phys, w_phys, h_phys);
    }
    const int x_l = static_cast<int>(std::lround(static_cast<double>(x_phys) / sc));
    const int y_l = static_cast<int>(std::lround(static_cast<double>(y_phys) / sc));
    const int right_l =
        static_cast<int>(std::lround(static_cast<double>(x_phys + w_phys) / sc));
    const int bottom_l =
        static_cast<int>(std::lround(static_cast<double>(y_phys + h_phys) / sc));
    return QRect(x_l, y_l, std::max(1, right_l - x_l), std::max(1, bottom_l - y_l));
}

}  // namespace pipela::ui::theme
