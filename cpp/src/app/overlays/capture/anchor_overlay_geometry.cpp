#include "capture/anchor_overlay_geometry.hpp"

#include <QWidget>

#include "pipela/core/win32/game_windows.hpp"
#include "theme/dpi_helpers.hpp"

namespace pipela::ui::overlays::capture {

AnchorOverlayGeometry syncWidgetToAnchor(QWidget* widget, std::intptr_t anchor_hwnd) {
    AnchorOverlayGeometry out;
    if (widget == nullptr || !anchor_hwnd || !pipela::core::win32::isWindow(anchor_hwnd)) {
        return out;
    }
    const auto cr = pipela::core::win32::getClientRectScreen(anchor_hwnd);
    const int left = std::get<0>(cr);
    const int top = std::get<1>(cr);
    const int right = std::get<2>(cr);
    const int bottom = std::get<3>(cr);
    const int phys_w = right - left;
    const int phys_h = bottom - top;
    out.qt_geometry = pipela::ui::theme::win32PhysicalScreenRectToQtOverlayGeometry(
        anchor_hwnd, left, top, phys_w, phys_h);
    out.client_w = out.qt_geometry.width();
    out.client_h = out.qt_geometry.height();
    out.dpi_scale = pipela::ui::theme::win32DpiScaleForHwnd(anchor_hwnd);
    widget->setGeometry(out.qt_geometry);
    return out;
}

}  // namespace pipela::ui::overlays::capture
