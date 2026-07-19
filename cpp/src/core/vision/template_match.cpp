#include "pipela/core/vision/template_match.hpp"

#if defined(PIPELA_HAS_OPENCV)
#include <opencv2/imgproc.hpp>
#endif

namespace pipela::core::vision {

MatchResult matchTemplateCcoeffNormedMax(const unsigned char* screen_bgr,
                                         int screen_w,
                                         int screen_h,
                                         int screen_stride,
                                         const unsigned char* template_bgr,
                                         int template_w,
                                         int template_h,
                                         int template_stride) {
    MatchResult out;
    if (!screen_bgr || !template_bgr || screen_w < template_w || screen_h < template_h) {
        return out;
    }
#if defined(PIPELA_HAS_OPENCV)
    cv::Mat screen(screen_h, screen_w, CV_8UC3, const_cast<unsigned char*>(screen_bgr),
                   static_cast<size_t>(screen_stride));
    cv::Mat templ(template_h, template_w, CV_8UC3, const_cast<unsigned char*>(template_bgr),
                  static_cast<size_t>(template_stride));
    cv::Mat result;
    cv::matchTemplate(screen, templ, result, cv::TM_CCOEFF_NORMED);
    double min_val = 0.0;
    double max_val = 0.0;
    cv::Point min_loc;
    cv::Point max_loc;
    cv::minMaxLoc(result, &min_val, &max_val, &min_loc, &max_loc);
    out.score = max_val;
    out.top_left_x = max_loc.x;
    out.top_left_y = max_loc.y;
    out.valid = true;
#else
    (void)screen_stride;
    (void)template_stride;
#endif
    return out;
}

}  // namespace pipela::core::vision
