#include "pipela/core/workers/worker_context.hpp"
#include "pipela/core/workers/worker_loop_trace.hpp"

#include "pipela/core/kill_counter/goal_display.hpp"
#include "pipela/core/kill_counter/screen_probe.hpp"
#include "pipela/core/kill_counter/session.hpp"
#include "pipela/core/registry/json_region.hpp"

#include <chrono>

namespace pipela::core::workers {

void killCounterWorkerLoop(WorkerContext& ctx) {
    const WorkerLoopTracer trace("kill_counter_loop");
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

        if (pipela::core::kill_counter::shouldSkipOcrSameScreen(ctx.state(), *screen)) {
            ctx.sleepMs(70);
            continue;
        }
        pipela::core::kill_counter::rememberOcrScreenProbe(*screen);

        const auto now_ts = std::chrono::duration<double>(
                                std::chrono::system_clock::now().time_since_epoch())
                                .count();
        ctx.state().set("kill_counter_last_poll_ts", state::StateValue{now_ts});

        if (auto ocr = ctx.runKillCounterOcr(*screen)) {
            if (ocr->skip) {
                ctx.sleepMs(70);
                continue;
            }
            const std::string& progress =
                !ocr->last_progress.empty() ? ocr->last_progress : ocr->prog_txt;
            if (!progress.empty()) {
                ctx.state().set("kill_counter_last_progress",
                                state::StateValue{progress});
            }
            if (!ocr->poll_phase.empty()) {
                ctx.state().set("kill_counter_last_poll_phase", state::StateValue{ocr->poll_phase});
            }
            if (!ocr->poll_detail.empty()) {
                ctx.state().set("kill_counter_last_poll_detail", state::StateValue{ocr->poll_detail});
            }
            if (!progress.empty()) {
                trace.action("ocr phase=" + ocr->poll_phase + " progress=" + progress +
                             " detail=" + ocr->poll_detail);
            }
            if (auto n1 = pipela::core::kill_counter::progressN1FromOcr(progress)) {
                if (pipela::core::kill_counter::ocrN1Plausible(ctx.state(), *n1)) {
                    pipela::core::kill_counter::onOcrN1Accepted(ctx.state(), *n1, false);
                    ctx.state().set("kill_counter_last_poll_phase", state::StateValue{std::string{"ok"}});
                    ctx.state().set("kill_counter_last_poll_detail", state::StateValue{std::string{}});
                }
            }
        }
        ctx.state().incrementInt("kill_counter_loop_count", 1);
        ctx.sleepMs(70);
    }
}

}  // namespace pipela::core::workers
