#pragma once

#include <array>
#include <optional>

namespace pipela::core::vision {

constexpr int kBaseHeight = 1440;

double scaleRatio(int client_height);
std::optional<std::array<int, 4>> regionPixels(int client_w,
                                               int client_h,
                                               const double region[4]);

}  // namespace pipela::core::vision
