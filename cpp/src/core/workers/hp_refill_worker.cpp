#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/win32/input_synth.hpp"

#include <chrono>
#include <cmath>

namespace pipela::core::workers {

void hpRefillWorkerLoop(WorkerContext& ctx) {
    double last_key_time = -1.0;
    constexpr double kCooldownSec = 0.5;
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
        if (!ctx.registryBool("hp_refill_feature_enabled", true)) {
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
        const auto path = ctx.registryString("HP_REFILL_ZKEY_IMAGE_PATH");
        if (!path || path->empty()) {
            ctx.sleepMs(1000);
            continue;
        }
        if (*path != last_path) {
            template_original = ctx.loadTemplate(*path, "hp_refill_zkey_image_data");
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
        if (auto reg_s = ctx.registryString("hp_refill_detect_region")) {
            region = registry::parseRegionJson(*reg_s);
        }
        auto screen = region ? ctx.captureRegion(hwnd, region->data()) : full;
        if (!screen) {
            ctx.sleepMs(50);
            continue;
        }
        const double thr = ctx.registryFloat("hp_refill_threshold", 0.6);
        const auto hit = ctx.matchTemplate(*screen, *scaled_template, thr);
        ctx.state().set("hp_refill_detection_score", state::StateValue{hit.score});
        if (hit.valid) {
            const auto now = std::chrono::duration<double>(
                                std::chrono::steady_clock::now().time_since_epoch())
                                .count();
            if (last_key_time < 0.0 || (now - last_key_time) >= kCooldownSec) {
                const int vk = ctx.registryInt("hp_refill_key_code", 0x5A);
                win32::sendVirtualKey(static_cast<unsigned short>(vk), false);
                win32::sendVirtualKey(static_cast<unsigned short>(vk), true);
                last_key_time = now;
                ctx.state().incrementInt("hp_refill_trigger_total", 1);
            }
        }
#else
        (void)last_key_time;
#endif
        ctx.sleepMs(50);
    }
}

}  // namespace pipela::core::workers
