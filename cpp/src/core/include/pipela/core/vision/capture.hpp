#pragma once

#include <cstdint>
#include <optional>
#include <vector>

namespace pipela::core::vision {

struct BgrImage {
    int width{0};
    int height{0};
    std::vector<unsigned char> bytes;
};

std::optional<BgrImage> captureClientBgr(std::intptr_t hwnd);
std::optional<BgrImage> sliceBgr(const BgrImage& full, int x, int y, int w, int h);

#if defined(PIPELA_HAS_OPENCV)
std::optional<BgrImage> loadBgrFromPath(const std::string& path);
std::optional<BgrImage> scaleBgr(const BgrImage& src, double ratio);
#endif

}  // namespace pipela::core::vision
