#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/win32/input_synth.hpp"

#include <algorithm>

namespace pipela::core::workers {

void leftClickWorkerLoop(WorkerContext& ctx) {
    while (!ctx.stopRequested()) {
        if (!ctx.running() || ctx.selectMode() || ctx.flameTriggerActive()) {
            ctx.sleepMs(10);
            continue;
        }
        if (!ctx.registryBool("left_click_feature_enabled", true)) {
            ctx.sleepMs(10);
            continue;
        }
        bool active = false;
        if (auto v = ctx.state().get("left_click_active")) {
            if (const auto* b = std::get_if<bool>(&*v)) {
                active = *b;
            }
        }
        if (!active) {
            ctx.sleepMs(10);
            continue;
        }
        if (ctx.powerSaveActive()) {
            ctx.sleepMs(300);
            continue;
        }
        const int interval_ms = ctx.registryInt("left_click_interval_ms", 100);
        win32::mouseLeftClick();
        ctx.sleepMs(std::max(10, interval_ms));
    }
}

void rightHoldWorkerLoop(WorkerContext& ctx) {
    while (!ctx.stopRequested()) {
        if (!ctx.running() || ctx.selectMode() || ctx.flameTriggerActive()) {
            ctx.sleepMs(10);
            continue;
        }
        if (!ctx.registryBool("right_hold_feature_enabled", true)) {
            ctx.sleepMs(10);
            continue;
        }
        bool active = false;
        if (auto v = ctx.state().get("right_hold_active")) {
            if (const auto* b = std::get_if<bool>(&*v)) {
                active = *b;
            }
        }
        if (!active) {
            ctx.sleepMs(10);
            continue;
        }
        if (ctx.powerSaveActive()) {
            ctx.sleepMs(300);
            continue;
        }
        win32::mouseRightDown();
        ctx.sleepMs(50);
    }
}

void killCounterWorkerLoop(WorkerContext& ctx) {
    while (!ctx.stopRequested()) {
        if (!ctx.running() || ctx.selectMode()) {
            ctx.sleepMs(70);
            continue;
        }
        if (!ctx.registryBool("kill_counter_enabled", true)) {
            ctx.sleepMs(70);
            continue;
        }
        if (ctx.powerSaveActive()) {
            ctx.sleepMs(2500);
            continue;
        }
        ctx.state().set("kill_counter_last_poll_ts", state::StateValue{0.0});
        ctx.sleepMs(70);
    }
}

void startGameLauncherWorkerLoop(WorkerContext& ctx) {
    while (!ctx.stopRequested()) {
        if (!ctx.running()) {
            ctx.sleepMs(60);
            continue;
        }
        if (!ctx.registryBool("start_game_launcher_enabled", true)) {
            ctx.sleepMs(60);
            continue;
        }
        ctx.sleepMs(60);
    }
}

}  // namespace pipela::core::workers
