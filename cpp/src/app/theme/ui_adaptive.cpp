#include "theme/ui_adaptive.hpp"

#include <algorithm>
#include <cmath>

namespace pipela::ui::theme {

namespace {
constexpr int kRefWidth = 420;
constexpr int kRefHeight = 720;
}  // namespace

double typographyWidthScale(int layout_width_px) {
    if (layout_width_px <= 0) {
        return 1.0;
    }
    return std::clamp(static_cast<double>(layout_width_px) / kRefWidth, 0.75, 1.35);
}

double typographyHeightScale(int layout_height_px) {
    if (layout_height_px <= 0) {
        return 1.0;
    }
    return std::clamp(static_cast<double>(layout_height_px) / kRefHeight, 0.75, 1.35);
}

int scalePx(int value, double ui_scale) {
    if (ui_scale <= 0.01) {
        ui_scale = 1.0;
    }
    return static_cast<int>(std::lround(value * ui_scale));
}

int scalePxH(int value, int layout_width_px) {
    return scalePx(value, typographyWidthScale(layout_width_px));
}

int scalePxV(int value, int layout_height_px) {
    return scalePx(value, typographyHeightScale(layout_height_px));
}

double scaledDesignPt(double design_pt, double ui_scale) {
    if (ui_scale <= 0.01) {
        ui_scale = 1.0;
    }
    return design_pt * ui_scale;
}

}  // namespace pipela::ui::theme
