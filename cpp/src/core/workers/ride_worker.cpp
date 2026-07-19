#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/win32/input_synth.hpp"

#include <cmath>

namespace pipela::core::workers {

void rideWorkerLoop(WorkerContext& ctx) {
    bool image_detected = false;
#if defined(PIPELA_HAS_OPENCV)
    std::optional<vision::BgrImage> template_original;
    std::optional<vision::BgrImage> scaled_template;
    double last_ratio = 0.0;
    std::string last_path;
#endif
    int tick = 0;

    while (!ctx.stopRequested()) {
        if (++tick % 20 == 0) {
            ctx.refreshSnapshot();
        }
        if (!ctx.running() || ctx.selectMode()) {
            ctx.sleepMs(50);
            continue;
        }
        if (!ctx.registryBool("ride_feature_enabled", true)) {
            ctx.sleepMs(50);
            continue;
        }
        const auto hwnd = ctx.targetHwnd();
        if (!hwnd) {
            ctx.sleepMs(50);
            continue;
        }
        if (ctx.powerSaveActive()) {
            ctx.sleepMs(2500);
            continue;
        }

#if defined(PIPELA_HAS_OPENCV)
        const auto path = ctx.registryString("RIDE_TARGET_IMAGE_PATH");
        if (!path || path->empty()) {
            ctx.sleepMs(1000);
            continue;
        }
        if (*path != last_path) {
            template_original = ctx.loadTemplatePath(*path);
            scaled_template = template_original;
            last_path = *path;
            last_ratio = 0.0;
        }
        if (!template_original) {
            ctx.sleepMs(1000);
            continue;
        }

        auto full = vision::captureClientBgr(hwnd);
        if (!full) {
            ctx.sleepMs(50);
            continue;
        }
        const double ratio = vision::scaleRatio(full->height);
        if (std::abs(ratio - last_ratio) > 0.01) {
            scaled_template = ctx.rescaleTemplate(*template_original, ratio);
            last_ratio = ratio;
        }
        if (!scaled_template) {
            ctx.sleepMs(50);
            continue;
        }

        std::optional<std::array<double, 4>> region;
        if (auto reg_s = ctx.registryString("ride_detect_region")) {
            region = registry::parseRegionJson(*reg_s);
        }
        auto screen = region ? ctx.captureRegion(hwnd, region->data()) : full;
        if (!screen) {
            ctx.sleepMs(50);
            continue;
        }
        const double thr = ctx.registryFloat("ride_threshold", 0.6);
        const auto hit = ctx.matchTemplate(*screen, *scaled_template, thr);
        const bool detected = hit.valid;
        if (detected != image_detected) {
            image_detected = detected;
            win32::setCapsLock(detected);
        }
#else
        (void)image_detected;
#endif
        ctx.sleepMs(50);
    }
}

}  // namespace pipela::core::workers
