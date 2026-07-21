#pragma once

#include <algorithm>
#include <tuple>

namespace pipela::core {

inline constexpr int kConsoleLogRetentionMinMin = 0;
inline constexpr int kConsoleLogRetentionMaxMin = 10080;
inline constexpr int kConsoleLogRetentionMaxSeconds = 59;
inline constexpr int kConsoleLogRetentionMinTotalSec = 1;
inline constexpr int kConsoleLogRetentionMaxTotalSec = kConsoleLogRetentionMaxMin * 60;
inline constexpr int kConsoleLogRetentionUiMaxClockMinute = 59;
inline constexpr int kConsoleLogRetentionUiMaxHours =
    kConsoleLogRetentionMaxTotalSec / 3600;

// AGENT: Terminal row cap — memory + fading + archive (performance guard for QLabel rows).
inline constexpr int kConsoleLogMaxLinesDefault = 500;
inline constexpr int kConsoleLogMaxLinesMin = 100;
inline constexpr int kConsoleLogMaxLinesMax = 5000;

inline int clampConsoleLogMaxLines(int value) {
    return std::clamp(value, kConsoleLogMaxLinesMin, kConsoleLogMaxLinesMax);
}

inline int consoleLogRetentionTotalSec(int minutes, int seconds) {
    const int total = minutes * 60 + seconds;
    if (total < kConsoleLogRetentionMinTotalSec) {
        return kConsoleLogRetentionMinTotalSec;
    }
    if (total > kConsoleLogRetentionMaxTotalSec) {
        return kConsoleLogRetentionMaxTotalSec;
    }
    return total;
}

inline int consoleLogRetentionTotalSecFromHms(int hours, int clock_minutes, int seconds) {
    const int total = hours * 3600 + clock_minutes * 60 + seconds;
    if (total < kConsoleLogRetentionMinTotalSec) {
        return kConsoleLogRetentionMinTotalSec;
    }
    if (total > kConsoleLogRetentionMaxTotalSec) {
        return kConsoleLogRetentionMaxTotalSec;
    }
    return total;
}

inline std::tuple<int, int> consoleLogRetentionSplitTotal(int total_sec) {
    int t = total_sec;
    if (t < kConsoleLogRetentionMinTotalSec) {
        t = kConsoleLogRetentionMinTotalSec;
    }
    if (t > kConsoleLogRetentionMaxTotalSec) {
        t = kConsoleLogRetentionMaxTotalSec;
    }
    return {t / 60, t % 60};
}

inline std::tuple<int, int, int> consoleLogRetentionSplitTotalToHms(int total_sec) {
    int t = total_sec;
    if (t < kConsoleLogRetentionMinTotalSec) {
        t = kConsoleLogRetentionMinTotalSec;
    }
    if (t > kConsoleLogRetentionMaxTotalSec) {
        t = kConsoleLogRetentionMaxTotalSec;
    }
    const int h = t / 3600;
    const int rem = t % 3600;
    const int m = rem / 60;
    const int s = rem % 60;
    return {h, m, s};
}

}  // namespace pipela::core
