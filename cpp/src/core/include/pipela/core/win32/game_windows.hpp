#pragma once

#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace pipela::core::win32 {

bool isWindow(std::intptr_t hwnd);
bool isWindowMinimized(std::intptr_t hwnd);
bool isForegroundWindow(std::intptr_t hwnd);
std::optional<std::pair<int, int>> getScreenCursorPos();
bool isMouseInClientWindow(std::intptr_t hwnd);

std::tuple<int, int, int, int> getClientRectScreen(std::intptr_t hwnd);

// BitBlt client DC → BGR bytes (row-major, 3 channels). Empty on failure.
std::vector<unsigned char> captureClientBgr(std::intptr_t hwnd, int* out_w = nullptr, int* out_h = nullptr);

bool eternalcityTitleMatches(const std::wstring& title);
bool smartUpdaterTitleMatches(const std::wstring& title, const std::wstring& korean_substr);

std::intptr_t findEternalcityWindow();
std::intptr_t findSmartUpdaterWindow(const std::wstring& korean_substr = L"\uc2a4\ub9c8\ud2b8\uc5c5\ub370\uc774\ud130");

std::intptr_t refreshEternalcityHwndCached(std::intptr_t prev_hwnd);
std::intptr_t refreshSmartUpdaterHwndCached(std::intptr_t prev_hwnd,
                                            const std::wstring& korean_substr = L"\uc2a4\ub9c8\ud2b8\uc5c5\ub370\uc774\ud130");

// Match center in capture-local coords → screen coords (hwnd client + optional normalized ROI).
std::optional<std::pair<int, int>> matchCenterToScreen(std::intptr_t hwnd,
                                                       const double region[4],
                                                       bool has_region,
                                                       int match_center_x,
                                                       int match_center_y);

}  // namespace pipela::core::win32
