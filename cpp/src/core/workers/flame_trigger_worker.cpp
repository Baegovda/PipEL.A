#include "pipela/core/workers/worker_context.hpp"
#include "pipela/core/workers/worker_loop_trace.hpp"

#include "pipela/core/win32/clip_cursor.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/input_synth.hpp"

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <random>

namespace pipela::core::workers {

namespace {

double nowSeconds() {
    return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
}

int envClipHalf() {
    const char* raw = std::getenv("PIPELA_FT_CLIP_HALF");
    if (raw == nullptr || raw[0] == '\0') {
        return 0;
    }
    try {
        return std::max(0, std::stoi(raw));
    } catch (...) {
        return 0;
    }
}

void releaseFlameInputs(WorkerContext& ctx, bool preserve_hud) {
    win32::mouseRightUp();
    win32::clipCursorRelease();
    ctx.state().set("flame_trigger_prev_press_timestamp", state::StateValue{0.0});
    ctx.state().set("flame_trigger_last_press_interval_sec", state::StateValue{0.0});
    if (!preserve_hud) {
        ctx.state().set("flame_trigger_hud_session_start_time", state::StateValue{0.0});
        ctx.state().set("flame_trigger_session_reload_count", state::StateValue{0});
        ctx.state().set("flame_trigger_last_reload_complete_time", state::StateValue{0.0});
        ctx.state().set("flame_trigger_last_reload_trigger_time", state::StateValue{0.0});
    }
}

}  // namespace

void flameTriggerWorkerLoop(WorkerContext& ctx) {
    const WorkerLoopTracer trace("flame_trigger_loop");
    bool executed = false;
    double last_key_time = 0.0;
    double next_key_interval_sec = 0.0;
    std::mt19937 rng{std::random_device{}()};
    const int clip_half = envClipHalf();

    while (!ctx.stopRequested()) {
        if (!ctx.running() || ctx.selectMode()) {
            if (executed) {
                const bool preserve = [&ctx]() {
                    if (auto v = ctx.state().get("flame_trigger_reload_teardown_preserve_hud")) {
                        if (const auto* b = std::get_if<bool>(&*v)) {
                            return *b;
                        }
                    }
                    return false;
                }();
                releaseFlameInputs(ctx, preserve);
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
                const bool preserve = [&ctx]() {
                    if (auto v = ctx.state().get("flame_trigger_reload_teardown_preserve_hud")) {
                        if (const auto* b = std::get_if<bool>(&*v)) {
                            return *b;
                        }
                    }
                    return false;
                }();
                releaseFlameInputs(ctx, preserve);
                executed = false;
            }
            ctx.sleepMs(10);
            continue;
        }

        if (ctx.otherAutomationSuppressesFlameTrigger()) {
            if (executed) {
                win32::mouseRightUp();
                win32::clipCursorRelease();
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
            if (right > left && bottom > top && !win32::isWindowMinimized(hwnd)) {
                const int cx = left + (right - left) / 2;
                const int cy = top + (bottom - top) / 2;
                win32::mouseMove(cx, cy);
                ctx.sleepMs(100);
                if (!ctx.flameTriggerActive()) {
                    continue;
                }
                const int h0 = clip_half;
                win32::clipCursorToScreenRect(cx - h0, cy - h0, cx + h0 + 1, cy + h0 + 1);
                win32::mouseRightDown();
                executed = true;
                trace.event("session_start center=" + std::to_string(cx) + "," + std::to_string(cy) +
                            " clip_half=" + std::to_string(clip_half));
                const double start_ts = nowSeconds();
                ctx.state().set("flame_trigger_start_time", state::StateValue{start_ts});
                int reload_count = 0;
                if (auto v = ctx.state().get("flame_trigger_session_reload_count")) {
                    if (const auto* i = std::get_if<int>(&*v)) {
                        reload_count = *i;
                    }
                }
                double last_reload_trig = 0.0;
                if (auto v = ctx.state().get("flame_trigger_last_reload_trigger_time")) {
                    if (const auto* d = std::get_if<double>(&*v)) {
                        last_reload_trig = *d;
                    }
                }
                const bool reload_hud_carry = reload_count > 0 || last_reload_trig > 0.0;
                if (!reload_hud_carry) {
                    ctx.state().set("flame_trigger_hud_session_start_time", state::StateValue{start_ts});
                    ctx.state().set("flame_trigger_session_reload_count", state::StateValue{0});
                    ctx.state().set("flame_trigger_last_reload_complete_time", state::StateValue{0.0});
                    ctx.state().set("flame_trigger_last_reload_trigger_time", state::StateValue{0.0});
                }
                ctx.state().set("flame_trigger_press_count", state::StateValue{0});
                ctx.state().set("flame_trigger_prev_press_timestamp", state::StateValue{0.0});
                ctx.state().set("flame_trigger_last_press_interval_sec", state::StateValue{0.0});
                const double lo_ms = ctx.registryFloat("merc_fire_random_min_ms", 100.0);
                const double hi_ms = ctx.registryFloat("merc_fire_random_max_ms", 200.0);
                std::uniform_real_distribution<double> dist(lo_ms, std::max(lo_ms, hi_ms));
                next_key_interval_sec = dist(rng) / 1000.0;
                last_key_time = start_ts;
                if (ctx.registryBool("merc_fire_enabled", false)) {
                    const int vk = ctx.registryInt("merc_fire_key_code", 0);
                    if (vk > 0) {
                        win32::sendVirtualKey(static_cast<unsigned short>(vk), false);
                        win32::sendVirtualKey(static_cast<unsigned short>(vk), true);
                        ctx.state().incrementInt("flame_trigger_press_count", 1);
                        ctx.state().set("flame_trigger_last_press_interval_sec", state::StateValue{0.0});
                        ctx.state().set("flame_trigger_prev_press_timestamp", state::StateValue{start_ts});
                        last_key_time = start_ts;
                    }
                }
            }
            ctx.sleepMs(16);
            continue;
        }

        if (!ctx.flameTriggerActive()) {
            ctx.sleepMs(16);
            continue;
        }

        const auto rect = win32::getClientRectScreen(hwnd);
        const int left = std::get<0>(rect);
        const int top = std::get<1>(rect);
        const int right = std::get<2>(rect);
        const int bottom = std::get<3>(rect);
        if (right <= left || bottom <= top || win32::isWindowMinimized(hwnd)) {
            trace.event("teardown invalid_rect active_off");
            releaseFlameInputs(ctx, false);
            executed = false;
            ctx.state().set("flame_trigger_active", state::StateValue{false});
            ctx.sleepMs(50);
            continue;
        }

        const int cx = left + (right - left) / 2;
        const int cy = top + (bottom - top) / 2;
        const int h = clip_half;
        const bool clip_ok =
            win32::clipCursorToScreenRect(cx - h, cy - h, cx + h + 1, cy + h + 1);
        win32::mouseMove(cx, cy);

        if (ctx.registryBool("merc_fire_enabled", false)) {
            const double now = nowSeconds();
            if ((now - last_key_time) >= next_key_interval_sec) {
                const int vk = ctx.registryInt("merc_fire_key_code", 0);
                if (vk > 0) {
                    win32::sendVirtualKey(static_cast<unsigned short>(vk), false);
                    win32::sendVirtualKey(static_cast<unsigned short>(vk), true);
                    ctx.state().incrementInt("flame_trigger_press_count", 1);
                    double prev_press = 0.0;
                    if (auto v = ctx.state().get("flame_trigger_prev_press_timestamp")) {
                        if (const auto* d = std::get_if<double>(&*v)) {
                            prev_press = *d;
                        }
                    }
                    if (prev_press > 0.0) {
                        ctx.state().set("flame_trigger_last_press_interval_sec",
                                        state::StateValue{now - prev_press});
                    }
                    ctx.state().set("flame_trigger_prev_press_timestamp", state::StateValue{now});
                    last_key_time = now;
                    const double lo_ms = ctx.registryFloat("merc_fire_random_min_ms", 100.0);
                    const double hi_ms = ctx.registryFloat("merc_fire_random_max_ms", 200.0);
                    std::uniform_real_distribution<double> dist(lo_ms, std::max(lo_ms, hi_ms));
                    next_key_interval_sec = dist(rng) / 1000.0;
                }
            }
        }

        const auto cur = win32::getScreenCursorPos();
        if (cur) {
            const double dx = static_cast<double>(cur->first - cx);
            const double dy = static_cast<double>(cur->second - cy);
            const double dist = std::sqrt(dx * dx + dy * dy);
            if ((!clip_ok && dist > 5.0) || (clip_ok && dist > 0.5)) {
                win32::mouseRightDown();
            }
        }

        (void)clip_ok;
        ctx.sleepMs(16);
    }

    if (executed) {
        releaseFlameInputs(ctx, false);
    }
}

}  // namespace pipela::core::workers
