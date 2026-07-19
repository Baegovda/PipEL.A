#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/input_synth.hpp"

#include <algorithm>
#include <chrono>
#include <random>

namespace pipela::core::workers {

namespace {

double nowSeconds() {
    return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
}

int envClipHalf() {
    return 0;
}

}  // namespace

void leftClickWorkerLoop(WorkerContext& ctx) {
    std::mt19937 rng{std::random_device{}()};
    while (!ctx.stopRequested()) {
        ctx.refreshSnapshot();
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
        const auto hwnd = ctx.targetHwnd();
        if (!hwnd || !win32::isMouseInClientWindow(hwnd)) {
            ctx.sleepMs(ctx.powerSaveActive() ? 300 : 10);
            continue;
        }
        if (ctx.powerSaveActive()) {
            ctx.sleepMs(300);
            continue;
        }
        win32::mouseLeftClick();
        int interval_ms = ctx.registryInt("left_click_interval_ms", 100);
        if (ctx.registryBool("left_click_random_enabled", false)) {
            const double lo = ctx.registryFloat("left_click_random_min_ms", 100.0);
            const double hi = ctx.registryFloat("left_click_random_max_ms", 200.0);
            std::uniform_real_distribution<double> dist(std::min(lo, hi), std::max(lo, hi));
            interval_ms = static_cast<int>(dist(rng));
        }
        ctx.sleepMs(std::max(1, interval_ms));
    }
}

void rightHoldWorkerLoop(WorkerContext& ctx) {
    while (!ctx.stopRequested()) {
        ctx.refreshSnapshot();
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
        const auto hwnd = ctx.targetHwnd();
        if (!hwnd || !win32::isMouseInClientWindow(hwnd)) {
            ctx.sleepMs(ctx.powerSaveActive() ? 300 : 10);
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

}  // namespace pipela::core::workers
