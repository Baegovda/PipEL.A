#pragma once

namespace pipela::ui::theme {

double typographyWidthScale(int layout_width_px);
double typographyHeightScale(int layout_height_px);
int scalePx(int value, double ui_scale = 1.0);
int scalePxH(int value, int layout_width_px);
int scalePxV(int value, int layout_height_px);
double scaledDesignPt(double design_pt, double ui_scale = 1.0);

}  // namespace pipela::ui::theme
