#pragma once

#include <cstdint>

#include <QRect>

class QWidget;

namespace pipela::ui::overlays::capture {

// AGENT: Single HWND → Qt overlay geometry sync (drag + preview share this).
struct AnchorOverlayGeometry {
    QRect qt_geometry;
    int client_w{0};
    int client_h{0};
    double dpi_scale{1.0};
};

AnchorOverlayGeometry syncWidgetToAnchor(QWidget* widget, std::intptr_t anchor_hwnd);

}  // namespace pipela::ui::overlays::capture
