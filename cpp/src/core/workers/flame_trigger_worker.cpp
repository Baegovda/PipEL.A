#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/input_synth.hpp"

#include <chrono>
#include <cmath>
#include <random>

namespace pipela::core::workers {

namespace {

double nowSeconds() {
    return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
}

void releaseFlameInputs(WorkerContext& ctx) {
    win32::mouseRightUp();
}

}  // namespace

void flameTriggerWorkerLoop(WorkerContext& ctx) {
    bool executed = false;
    double last_key_time = 0.0;
    double next_key_interval_sec = 0.0;
    std::mt19937 rng{std::random_device{}()};

    while (!ctx.stopRequested()) {
        if (!ctx.running() || ctx.selectMode()) {
            if (executed) {
                releaseFlameInputs(ctx);
                executed = false;
            }
            ctx.sleepMs(10);
            continue;
        }

        if (!ctx.registryBool("flame_trigger_feature_enabled", true)) {
            if (ctx.flameTriggerActive()) {
                ctx.state().set("flame_trigger_active", state::StateValue{false});
            }
        }

        if (!ctx.flameTriggerActive()) {
            if (executed) {
                releaseFlameInputs(ctx);
                executed = false;
                ctx.state().set("flame_trigger_last_press_interval_sec", state::StateValue{0.0});
            }
            ctx.sleepMs(10);
            continue;
        }

        if (ctx.otherAutomationSuppressesFlameTrigger()) {
            if (executed) {
                releaseFlameInputs(ctx);
                executed = false;
            }
            ctx.sleepMs(20);
            continue;
        }

        const auto hwnd = ctx.targetHwnd();
        if (!hwnd || ctx.powerSaveActive()) {
            ctx.sleepMs(50);
            continue;
        }

        if (!executed) {
            const auto rect = win32::getClientRectScreen(hwnd);
            const int left = std::get<0>(rect);
            const int top = std::get<1>(rect);
            const int right = std::get<2>(rect);
            const int bottom = std::get<3>(rect);
            if (right > left && bottom > top) {
                const int cx = left + (right - left) / 2;
                const int cy = top + (bottom - top) / 2;
                win32::mouseMove(cx, cy);
                ctx.sleepMs(100);
                if (!ctx.flameTriggerActive()) {
                    continue;
                }
                win32::mouseRightDown();
                executed = true;
                ctx.state().set("flame_trigger_start_time", state::StateValue{nowSeconds()});
                ctx.state().set("flame_trigger_press_count", state::StateValue{0});
                last_key_time = nowSeconds();
                const double lo_ms = ctx.registryFloat("merc_fire_random_min_ms", 100.0);
                const double hi_ms = ctx.registryFloat("merc_fire_random_max_ms", 200.0);
                std::uniform_real_distribution<double> dist(lo_ms, std::max(lo_ms, hi_ms));
                next_key_interval_sec = dist(rng) / 1000.0;
                if (ctx.registryBool("merc_fire_enabled", false)) {
                    const int vk = ctx.registryInt("merc_fire_key_code", 0);
                    if (vk > 0) {
                        win32::sendVirtualKey(static_cast<unsigned short>(vk), false);
                        win32::sendVirtualKey(static_cast<unsigned short>(vk), true);
                        ctx.state().incrementInt("flame_trigger_press_count", 1);
                    }
                }
            }
            ctx.sleepMs(16);
            continue;
        }

        if (ctx.registryBool("merc_fire_enabled", false)) {
            const double now = nowSeconds();
            if ((now - last_key_time) >= next_key_interval_sec) {
                const int vk = ctx.registryInt("merc_fire_key_code", 0);
                if (vk > 0) {
                    win32::sendVirtualKey(static_cast<unsigned short>(vk), false);
                    win32::sendVirtualKey(static_cast<unsigned short>(vk), true);
                    ctx.state().incrementInt("flame_trigger_press_count", 1);
                }
                last_key_time = now;
                const double lo_ms = ctx.registryFloat("merc_fire_random_min_ms", 100.0);
                const double hi_ms = ctx.registryFloat("merc_fire_random_max_ms", 200.0);
                std::uniform_real_distribution<double> dist(lo_ms, std::max(lo_ms, hi_ms));
                next_key_interval_sec = dist(rng) / 1000.0;
            }
        }

        ctx.sleepMs(16);
    }

    if (executed) {
        releaseFlameInputs(ctx);
    }
}

}  // namespace pipela::core::workers
