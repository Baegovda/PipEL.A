#pragma once

#include <string>
#include <tuple>
#include <vector>

namespace pipela::core::win32 {

bool isWindow(std::intptr_t hwnd);
std::tuple<int, int, int, int> getClientRectScreen(std::intptr_t hwnd);

// BitBlt client DC → BGR bytes (row-major, 3 channels). Empty on failure.
std::vector<unsigned char> captureClientBgr(std::intptr_t hwnd, int* out_w = nullptr, int* out_h = nullptr);

}  // namespace pipela::core::win32
