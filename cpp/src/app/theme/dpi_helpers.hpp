#pragma once

#include <QRect>

#include <cstdint>

namespace pipela::ui::theme {

double win32DpiScaleForHwnd(std::intptr_t hwnd);

// Win32 screen coords (physical px) -> Qt overlay setGeometry (logical DIP).
QRect win32PhysicalScreenRectToQtOverlayGeometry(std::intptr_t anchor_hwnd, int x_phys,
                                                 int y_phys, int w_phys, int h_phys);

}  // namespace pipela::ui::theme
