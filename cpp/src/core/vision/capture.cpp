#include "pipela/core/vision/capture.hpp"

#include "pipela/core/win32/game_windows.hpp"

#if defined(PIPELA_HAS_OPENCV)
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>
#endif

namespace pipela::core::vision {

std::optional<BgrImage> captureClientBgr(std::intptr_t hwnd) {
    int w = 0;
    int h = 0;
    auto bytes = win32::captureClientBgr(hwnd, &w, &h);
    if (bytes.empty() || w < 2 || h < 2) {
        return std::nullopt;
    }
    BgrImage out;
    out.width = w;
    out.height = h;
    out.bytes = std::move(bytes);
    return out;
}

std::optional<BgrImage> sliceBgr(const BgrImage& full, int x, int y, int w, int h) {
    if (full.width < 1 || full.height < 1 || w < 1 || h < 1) {
        return std::nullopt;
    }
    x = std::max(0, std::min(x, full.width - 1));
    y = std::max(0, std::min(y, full.height - 1));
    w = std::max(1, std::min(w, full.width - x));
    h = std::max(1, std::min(h, full.height - y));
    BgrImage out;
    out.width = w;
    out.height = h;
    out.bytes.resize(static_cast<size_t>(w) * static_cast<size_t>(h) * 3u);
    for (int row = 0; row < h; ++row) {
        const size_t src_off =
            (static_cast<size_t>(y + row) * static_cast<size_t>(full.width) + static_cast<size_t>(x)) * 3u;
        const size_t dst_off = static_cast<size_t>(row) * static_cast<size_t>(w) * 3u;
        std::copy_n(full.bytes.begin() + static_cast<std::ptrdiff_t>(src_off), static_cast<size_t>(w) * 3u,
                    out.bytes.begin() + static_cast<std::ptrdiff_t>(dst_off));
    }
    return out;
}

#if defined(PIPELA_HAS_OPENCV)
std::optional<BgrImage> loadBgrFromPath(const std::string& path) {
    if (path.empty()) {
        return std::nullopt;
    }
    cv::Mat img = cv::imread(path, cv::IMREAD_COLOR);
    if (img.empty()) {
        return std::nullopt;
    }
    BgrImage out;
    out.width = img.cols;
    out.height = img.rows;
    out.bytes.assign(img.data, img.data + img.total() * img.elemSize());
    return out;
}

std::optional<BgrImage> scaleBgr(const BgrImage& src, double ratio) {
    if (src.width < 1 || src.height < 1 || std::abs(ratio - 1.0) < 0.01) {
        return src;
    }
    cv::Mat in(src.height, src.width, CV_8UC3, const_cast<unsigned char*>(src.bytes.data()));
    const int nw = std::max(1, static_cast<int>(src.width * ratio));
    const int nh = std::max(1, static_cast<int>(src.height * ratio));
    cv::Mat out;
    cv::resize(in, out, cv::Size(nw, nh), 0, 0, cv::INTER_AREA);
    BgrImage result;
    result.width = out.cols;
    result.height = out.rows;
    result.bytes.assign(out.data, out.data + out.total() * out.elemSize());
    return result;
}
#endif

}  // namespace pipela::core::vision
