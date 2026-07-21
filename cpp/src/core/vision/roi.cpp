#include "pipela/core/vision/roi.hpp"

#include <algorithm>

namespace pipela::core::vision {

double scaleRatio(int client_height) {
    return static_cast<double>(std::max(client_height, 1)) / static_cast<double>(kBaseHeight);
}

std::optional<std::array<int, 4>> regionPixels(int client_w,
                                               int client_h,
                                               const double region[4]) {
    if (!region || client_w < 1 || client_h < 1) {
        return std::nullopt;
    }
    const int rx = static_cast<int>(region[0] * client_w);
    const int ry = static_cast<int>(region[1] * client_h);
    const int rw = static_cast<int>(region[2] * client_w);
    const int rh = static_cast<int>(region[3] * client_h);
    if (rw < 10 || rh < 10) {
        return std::nullopt;
    }
    return std::array<int, 4>{rx, ry, rw, rh};
}

std::array<double, 4> normalizedRoiFromDragRect(int x, int y, int w, int h, int client_w,
                                                int client_h) {
    const double fw = static_cast<double>(std::max(client_w, 1));
    const double fh = static_cast<double>(std::max(client_h, 1));
    return {static_cast<double>(x) / fw, static_cast<double>(y) / fh,
            static_cast<double>(w) / fw, static_cast<double>(h) / fh};
}

bool dragRectExceedsMinSize(int w, int h, int min_edge_px) {
    return w > min_edge_px && h > min_edge_px;
}

}  // namespace pipela::core::vision
