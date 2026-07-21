#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace pipela::core::vision {

struct BgrImage {
    int width{0};
    int height{0};
    std::vector<unsigned char> bytes;
};

std::optional<BgrImage> captureClientBgr(std::intptr_t hwnd);
std::optional<BgrImage> sliceBgr(const BgrImage& full, int x, int y, int w, int h);
// AGENT: Map overlay drag rect (logical client_w/h) into full BGR pixels (Python crop_drag_rect parity).
std::optional<BgrImage> cropBgrFromDragRect(const BgrImage& full, int x, int y, int w, int h,
                                            int client_w, int client_h);

#if defined(PIPELA_HAS_OPENCV)
std::optional<BgrImage> loadBgrFromPath(const std::string& path);
std::optional<BgrImage> scaleBgr(const BgrImage& src, double ratio);
#endif

}  // namespace pipela::core::vision
