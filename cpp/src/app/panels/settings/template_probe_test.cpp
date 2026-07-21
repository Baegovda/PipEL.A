#include "panels/settings/template_probe_test.hpp"

#include "pipela/core/template/last_match_cache.hpp"
#include "pipela/core/template/path_resolve.hpp"
#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/vision/capture.hpp"
#include "pipela/core/vision/roi.hpp"
#include "pipela/core/vision/template_match.hpp"
#include "pipela/core/win32/game_windows.hpp"

namespace pipela::app::panels::settings {

namespace {

std::string regStr(const std::string& key) {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(key);
    if (it == all.end()) {
        return {};
    }
    return it->second;
}

std::optional<std::string> lookupReg(const std::string& key) {
    const std::string v = regStr(key);
    if (v.empty()) {
        return std::nullopt;
    }
    return v;
}

}  // namespace

std::optional<double> runTemplateProbeTest(std::intptr_t game_hwnd,
                                           const TemplateProbeKeys& keys) {
    if (!game_hwnd || !pipela::core::win32::isWindow(game_hwnd)) {
        game_hwnd = pipela::core::win32::findEternalcityWindow();
    }
    if (!game_hwnd || !pipela::core::win32::isWindow(game_hwnd)) {
        return std::nullopt;
    }
#if defined(PIPELA_HAS_OPENCV)
    const auto path = pipela::core::template_meta::resolveExistingTemplateImagePath(
        keys.capture_kind, keys.image_path_key, lookupReg);
    if (!path) {
        return std::nullopt;
    }
    std::optional<pipela::core::vision::BgrImage> templ =
        pipela::core::vision::loadBgrFromPath(*path);
    if (!templ) {
        return std::nullopt;
    }
    auto full = pipela::core::vision::captureClientBgr(game_hwnd);
    if (!full) {
        return std::nullopt;
    }
    const double ratio = pipela::core::vision::scaleRatio(full->height);
    auto scaled = pipela::core::vision::scaleBgr(*templ, ratio);
    if (!scaled) {
        return std::nullopt;
    }
    pipela::core::vision::BgrImage screen = *full;
    const std::string region_json = regStr(keys.region_key);
    if (!region_json.empty()) {
        if (auto region = pipela::core::registry::parseRegionJson(region_json)) {
            if (auto px = pipela::core::vision::regionPixels(full->width, full->height,
                                                               region->data())) {
                if (auto cropped = pipela::core::vision::sliceBgr(
                        *full, (*px)[0], (*px)[1], (*px)[2], (*px)[3])) {
                    screen = *cropped;
                }
            }
        }
    }
    const int sstride = screen.width * 3;
    const int tstride = scaled->width * 3;
    const auto result = pipela::core::vision::matchTemplateCcoeffNormedMax(
        screen.bytes.data(), screen.width, screen.height, sstride, scaled->bytes.data(),
        scaled->width, scaled->height, tstride);
    if (!keys.capture_kind.empty() && result.valid) {
        if (auto patch = pipela::core::vision::sliceBgr(
                screen, result.top_left_x, result.top_left_y, scaled->width, scaled->height)) {
            pipela::core::template_meta::storeLastMatch(keys.capture_kind, *patch, result.score);
        }
    }
    return result.score;
#else
    (void)keys;
    return std::nullopt;
#endif
}

}  // namespace pipela::app::panels::settings
