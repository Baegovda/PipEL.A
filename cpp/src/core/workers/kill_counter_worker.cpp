#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/registry/json_region.hpp"

#include <chrono>

namespace pipela::core::workers {

void killCounterWorkerLoop(WorkerContext& ctx) {
    int tick = 0;
    while (!ctx.stopRequested()) {
        if (++tick % 10 == 0) {
            ctx.refreshSnapshot();
        }
        if (!ctx.running() || ctx.selectMode()) {
            ctx.sleepMs(70);
            continue;
        }
        if (!ctx.registryBool("kill_counter_enabled", true)) {
            ctx.sleepMs(70);
            continue;
        }
        const auto hwnd = ctx.targetHwnd();
        if (!hwnd) {
            ctx.sleepMs(70);
            continue;
        }
        if (ctx.powerSaveActive()) {
            ctx.sleepMs(2500);
            continue;
        }

        std::optional<std::array<double, 4>> region;
        if (auto reg_s = ctx.registryString("kill_counter_detect_region")) {
            region = registry::parseRegionJson(*reg_s);
        }
        if (!region) {
            ctx.sleepMs(70);
            continue;
        }

        auto screen = ctx.captureRegion(hwnd, region->data());
        if (!screen || screen->bytes.empty()) {
            ctx.sleepMs(70);
            continue;
        }

        const auto now_ts = std::chrono::duration<double>(
                                std::chrono::system_clock::now().time_since_epoch())
                                .count();
        ctx.state().set("kill_counter_last_poll_ts", state::StateValue{now_ts});

        if (auto ocr = ctx.runKillCounterOcr(*screen)) {
            if (!ocr->last_progress.empty()) {
                ctx.state().set("kill_counter_last_progress",
                                state::StateValue{ocr->last_progress});
            } else if (!ocr->prog_txt.empty()) {
                ctx.state().set("kill_counter_last_progress", state::StateValue{ocr->prog_txt});
            }
            if (!ocr->poll_phase.empty()) {
                ctx.state().set("kill_counter_last_poll_phase", state::StateValue{ocr->poll_phase});
            }
            if (!ocr->poll_detail.empty()) {
                ctx.state().set("kill_counter_last_poll_detail", state::StateValue{ocr->poll_detail});
            }
        }
        ctx.state().incrementInt("kill_counter_loop_count", 1);
        ctx.sleepMs(70);
    }
}

}  // namespace pipela::core::workers
