#include <cstdlib>
#include <sstream>
#include <string>

#include "pipela/core/workers/worker_context.hpp"
#include "pipela/core/workers/worker_loop_trace.hpp"

#include "pipela/core/feature_trace_log.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/input_synth.hpp"

#include <algorithm>
#include <chrono>
#include <random>

namespace pipela::core::workers {

namespace {

bool stateBool(const state::AppState& s, const char* key, bool fallback) {
    if (auto v = s.get(key)) {
        if (const auto* b = std::get_if<bool>(&*v)) {
            return *b;
        }
    }
    return fallback;
}

std::string hwndTag(std::intptr_t hwnd) {
    std::ostringstream oss;
    oss << "hwnd=0x" << std::hex << hwnd;
    return oss.str();
}

}  // namespace

void leftClickWorkerLoop(WorkerContext& ctx) {
    const WorkerLoopTracer trace("left_click_loop");
    std::mt19937 rng{std::random_device{}()};
    bool was_active = false;
    while (!ctx.stopRequested()) {
        ctx.refreshSnapshot();
        if (!ctx.running()) {
            trace.skip("!running");
            ctx.sleepMs(10);
            continue;
        }
        if (ctx.selectMode()) {
            trace.skip("select_mode");
            ctx.sleepMs(10);
            continue;
        }
        if (ctx.flameTriggerActive()) {
            trace.skip("flame_active");
            ctx.sleepMs(10);
            continue;
        }
        if (!ctx.registryBool("left_click_feature_enabled", true)) {
            trace.skip("feature_disabled");
            ctx.sleepMs(10);
            continue;
        }
        const bool active = stateBool(ctx.state(), "left_click_active", false);
        if (!active) {
            if (was_active) {
                trace.event("active_off worker_idle");
                was_active = false;
            }
            trace.skip("!left_click_active");
            ctx.sleepMs(10);
            continue;
        }
        if (!was_active) {
            trace.event("active_on worker_tick");
            was_active = true;
        }
        const auto hwnd = ctx.targetHwnd();
        if (!hwnd || !win32::isMouseInClientWindow(hwnd)) {
            trace.skip(!hwnd ? "no_hwnd" : "mouse_outside_client");
            ctx.sleepMs(ctx.powerSaveActive() ? 300 : 10);
            continue;
        }
        if (ctx.powerSaveActive()) {
            trace.skip("power_save");
            ctx.sleepMs(300);
            continue;
        }
        int interval_ms = ctx.registryInt("left_click_interval_ms", 100);
        if (ctx.registryBool("left_click_random_enabled", false)) {
            const double lo = ctx.registryFloat("left_click_random_min_ms", 100.0);
            const double hi = ctx.registryFloat("left_click_random_max_ms", 200.0);
            std::uniform_real_distribution<double> dist(std::min(lo, hi), std::max(lo, hi));
            interval_ms = static_cast<int>(dist(rng));
        }
        trace.action("synth_click " + hwndTag(hwnd) + " interval_ms=" + std::to_string(interval_ms));
        win32::mouseLeftClick();
        ctx.sleepMs(std::max(1, interval_ms));
    }
}

void rightHoldWorkerLoop(WorkerContext& ctx) {
    const WorkerLoopTracer trace("right_hold_loop");
    bool was_holding = false;
    while (!ctx.stopRequested()) {
        ctx.refreshSnapshot();
        if (!ctx.running() || ctx.selectMode() || ctx.flameTriggerActive()) {
            if (was_holding) {
                trace.event("release synth_right_up guard=running_select_flame");
                win32::mouseRightUp();
                was_holding = false;
            }
            trace.skip("guard_running_select_flame");
            ctx.sleepMs(10);
            continue;
        }
        if (!ctx.registryBool("right_hold_feature_enabled", true)) {
            if (was_holding) {
                trace.event("release synth_right_up guard=feature_disabled");
                win32::mouseRightUp();
                was_holding = false;
            }
            trace.skip("feature_disabled");
            ctx.sleepMs(10);
            continue;
        }
        const bool active = stateBool(ctx.state(), "right_hold_active", false);
        if (!active) {
            if (was_holding) {
                trace.event("release synth_right_up guard=!active");
                win32::mouseRightUp();
                was_holding = false;
            }
            trace.skip("!right_hold_active");
            ctx.sleepMs(10);
            continue;
        }
        const auto hwnd = ctx.targetHwnd();
        if (!hwnd || !win32::isMouseInClientWindow(hwnd)) {
            if (was_holding) {
                trace.event("release synth_right_up guard=hwnd_mouse");
                win32::mouseRightUp();
                was_holding = false;
            }
            trace.skip(!hwnd ? "no_hwnd" : "mouse_outside_client");
            ctx.sleepMs(ctx.powerSaveActive() ? 300 : 10);
            continue;
        }
        if (ctx.powerSaveActive()) {
            if (was_holding) {
                trace.event("release synth_right_up guard=power_save");
                win32::mouseRightUp();
                was_holding = false;
            }
            trace.skip("power_save");
            ctx.sleepMs(300);
            continue;
        }
        if (!was_holding) {
            trace.event("hold synth_right_down " + hwndTag(hwnd));
        }
        win32::mouseRightDown();
        was_holding = true;
        ctx.sleepMs(50);
    }
    if (was_holding) {
        trace.event("shutdown synth_right_up");
        win32::mouseRightUp();
    }
}

}  // namespace pipela::core::workers
