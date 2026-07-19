#pragma once

#include <utility>

namespace pipela::core::vision {

struct MatchResult {
    double score{0.0};
    int top_left_x{0};
    int top_left_y{0};
    bool valid{false};
};

// TM_CCOEFF_NORMED parity with pipela_core.template_matching (OpenCV when enabled).
MatchResult matchTemplateCcoeffNormedMax(const unsigned char* screen_bgr,
                                         int screen_w,
                                         int screen_h,
                                         int screen_stride,
                                         const unsigned char* template_bgr,
                                         int template_w,
                                         int template_h,
                                         int template_stride);

}  // namespace pipela::core::vision
