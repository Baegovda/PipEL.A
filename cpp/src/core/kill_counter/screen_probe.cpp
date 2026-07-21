#include "pipela/core/kill_counter/screen_probe.hpp"

#include <algorithm>
#include <cmath>
#include <variant>

namespace pipela::core::kill_counter {

namespace {

constexpr double kMeanAbsThresh = 1.15;
vision::BgrImage g_last_probe_bgr;

std::string stateString(const state::AppState& state, const char* key) {
    const auto v = state.get(key);
    if (!v || !std::holds_alternative<std::string>(*v)) {
        return {};
    }
    return std::get<std::string>(*v);
}

double captureMeanAbsDiff(const vision::BgrImage& prev, const vision::BgrImage& cur) {
    if (prev.width <= 0 || prev.height <= 0 || cur.width <= 0 || cur.height <= 0) {
        return 1.0e9;
    }
    if (prev.bytes.empty() || cur.bytes.empty()) {
        return 1.0e9;
    }
    const int tw = std::max(8, std::min(prev.width, cur.width) / 4);
    const int th = std::max(8, std::min(prev.height, cur.height) / 4);
    if (tw <= 0 || th <= 0) {
        return 1.0e9;
    }
    double sum = 0.0;
    int count = 0;
    double max_d = 0.0;
    for (int y = 0; y < th; ++y) {
        const int sy_p = y * prev.height / th;
        const int sy_c = y * cur.height / th;
        for (int x = 0; x < tw; ++x) {
            const int sx_p = x * prev.width / tw;
            const int sx_c = x * cur.width / tw;
            const int i_p = (sy_p * prev.width + sx_p) * 3;
            const int i_c = (sy_c * cur.width + sx_c) * 3;
            if (i_p + 2 >= static_cast<int>(prev.bytes.size()) ||
                i_c + 2 >= static_cast<int>(cur.bytes.size())) {
                continue;
            }
            const double gp = 0.114 * prev.bytes[i_p] + 0.587 * prev.bytes[i_p + 1] +
                              0.299 * prev.bytes[i_p + 2];
            const double gc = 0.114 * cur.bytes[i_c] + 0.587 * cur.bytes[i_c + 1] +
                              0.299 * cur.bytes[i_c + 2];
            const double d = std::abs(gp - gc);
            max_d = std::max(max_d, d);
            sum += d;
            ++count;
        }
    }
    if (count <= 0) {
        return 1.0e9;
    }
    const double mean_d = sum / static_cast<double>(count);
    if (max_d >= 6.0) {
        return std::max(mean_d, kMeanAbsThresh + 0.01);
    }
    return mean_d;
}

}  // namespace

bool shouldSkipOcrSameScreen(const state::AppState& state, const vision::BgrImage& cur_bgr) {
    if (cur_bgr.width <= 0 || cur_bgr.height <= 0 || cur_bgr.bytes.empty()) {
        return false;
    }
    const std::string phase = stateString(state, "kill_counter_last_poll_phase");
    if (phase.empty()) {
        return false;
    }
    if (phase == "unstable" || phase == "no_pair" || phase == "empty" || phase == "error") {
        return false;
    }
    if (g_last_probe_bgr.bytes.empty()) {
        return false;
    }
    return captureMeanAbsDiff(g_last_probe_bgr, cur_bgr) < kMeanAbsThresh;
}

void rememberOcrScreenProbe(const vision::BgrImage& cur_bgr) {
    g_last_probe_bgr = cur_bgr;
}

}  // namespace pipela::core::kill_counter
