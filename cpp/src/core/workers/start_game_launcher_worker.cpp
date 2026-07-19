#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/win32/game_windows.hpp"

#include <chrono>
#include <cmath>

namespace pipela::core::workers {

namespace {

constexpr double kLauncherRetryCooldownSec = 1.0;
constexpr double kLauncherDisappearWaitSec = 5.0;
constexpr double kIntroSkipArmTimeoutSec = 180.0;
constexpr double kAcceptArmTimeoutSec = 180.0;

double nowMono() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

#if defined(PIPELA_HAS_OPENCV)

struct TemplateSlot {
    const char* path_key;
    const char* data_key;
    const char* region_key;
    const char* threshold_key;
    const char* score_state_key;

    std::optional<vision::BgrImage> original;
    std::optional<vision::BgrImage> scaled;
    std::string last_path;
};

bool ensureTemplate(WorkerContext& ctx, TemplateSlot& slot) {
    const auto path = ctx.registryString(slot.path_key);
    if (!path || path->empty()) {
        return false;
    }
    if (*path != slot.last_path) {
        slot.original = ctx.loadTemplate(*path, slot.data_key);
        slot.scaled = slot.original;
        slot.last_path = *path;
    }
    return static_cast<bool>(slot.original);
}

std::optional<std::array<double, 4>> regionFromRegistry(WorkerContext& ctx, const char* key) {
    if (auto s = ctx.registryString(key)) {
        return registry::parseRegionJson(*s);
    }
    return std::nullopt;
}

MatchHit matchBestOnWindow(WorkerContext& ctx,
                           std::intptr_t hwnd,
                           const vision::BgrImage& tpl_original,
                           const std::optional<vision::BgrImage>& tpl_scaled,
                           const std::optional<std::array<double, 4>>& region,
                           double threshold) {
    MatchHit miss;
    auto full = vision::captureClientBgr(hwnd);
    if (!full) {
        return miss;
    }
    const double ratio = vision::scaleRatio(full->height);
    std::optional<vision::BgrImage> scaled = tpl_scaled;
    if (!scaled || std::abs(ratio - vision::scaleRatio(full->height)) > 0.01) {
        scaled = ctx.rescaleTemplate(tpl_original, ratio);
    }
    if (!scaled) {
        return miss;
    }
    auto screen = region ? ctx.captureRegion(hwnd, region->data()) : full;
    if (!screen) {
        return miss;
    }
    MatchHit best = ctx.matchTemplate(*screen, *scaled, threshold);
    if (!best.valid) {
        const auto raw = ctx.matchTemplate(*screen, tpl_original, threshold);
        if (raw.valid && raw.score > best.score) {
            best = raw;
        }
    }
    return best;
}

#endif

}  // namespace

void startGameLauncherWorkerLoop(WorkerContext& ctx) {
    double last_launcher_click_mono = 0.0;
    bool intro_skip_armed = false;
    double intro_skip_arm_until_mono = 0.0;
    bool accept_armed = false;
    double accept_arm_until_mono = 0.0;
#if defined(PIPELA_HAS_OPENCV)
    TemplateSlot launcher{
        "START_GAME_IMAGE_PATH", "start_game_launcher_image_data", "start_game_launcher_match_region",
        "start_game_launcher_threshold", "start_game_launcher_score"};
    TemplateSlot intro{
        "START_GAME_INTRO_SKIP_IMAGE_PATH", "start_game_intro_skip_image_data",
        "start_game_intro_skip_match_region", "start_game_intro_skip_threshold",
        "start_game_intro_skip_score"};
    TemplateSlot accept{
        "START_GAME_ACCEPT_IMAGE_PATH", "start_game_accept_image_data", "start_game_accept_match_region",
        "start_game_accept_threshold", "start_game_accept_score"};
#endif
    int tick = 0;

    while (!ctx.stopRequested()) {
        if (++tick % 10 == 0) {
            ctx.refreshSnapshot();
        }
        if (!ctx.running()) {
            ctx.sleepMs(60);
            continue;
        }
        if (!ctx.registryBool("start_game_launcher_enabled", true)) {
            ctx.sleepMs(60);
            continue;
        }

        const double mono_now = nowMono();

        if (!ctx.isStartGameLauncherEffective()) {
            intro_skip_armed = false;
            intro_skip_arm_until_mono = 0.0;
            accept_armed = false;
            accept_arm_until_mono = 0.0;
            ctx.state().set("start_game_launcher_score", state::StateValue{0.0});
            ctx.state().set("start_game_intro_skip_score", state::StateValue{0.0});
            ctx.state().set("start_game_accept_score", state::StateValue{0.0});
            ctx.sleepMs(220);
            continue;
        }
        if (ctx.selectMode()) {
            ctx.sleepMs(120);
            continue;
        }

#if defined(PIPELA_HAS_OPENCV)
        if (!ensureTemplate(ctx, launcher) || !ensureTemplate(ctx, intro) || !ensureTemplate(ctx, accept)) {
            ctx.sleepMs(550);
            continue;
        }

        if (accept_armed) {
            if (mono_now > accept_arm_until_mono) {
                accept_armed = false;
                accept_arm_until_mono = 0.0;
                ctx.state().set("start_game_accept_score", state::StateValue{0.0});
                ctx.sleepMs(120);
                continue;
            }
            const auto hwnd = ctx.refreshTargetHwnd();
            if (!hwnd) {
                ctx.state().set("start_game_accept_score", state::StateValue{0.0});
                ctx.sleepMs(250);
                continue;
            }
            const auto region = regionFromRegistry(ctx, accept.region_key);
            const double thr = ctx.registryFloat(accept.threshold_key, 0.6);
            const auto hit = matchBestOnWindow(ctx, hwnd, *accept.original, accept.scaled, region, thr);
            ctx.state().set(accept.score_state_key, state::StateValue{hit.score});
            if (!hit.valid) {
                ctx.sleepMs(70);
                continue;
            }
            const bool has_region = region.has_value();
            const auto pt = ctx.matchCenterToScreen(hwnd, has_region ? region->data() : nullptr,
                                                    has_region, hit.center_x, hit.center_y);
            if (!pt) {
                ctx.sleepMs(200);
                continue;
            }
            ctx.clickScreen(pt->first, pt->second);
            accept_armed = false;
            accept_arm_until_mono = 0.0;
            ctx.state().set("start_game_accept_score", state::StateValue{0.0});
            ctx.sleepMs(350);
            continue;
        }

        if (intro_skip_armed) {
            if (mono_now > intro_skip_arm_until_mono) {
                intro_skip_armed = false;
                intro_skip_arm_until_mono = 0.0;
                ctx.state().set("start_game_intro_skip_score", state::StateValue{0.0});
                ctx.sleepMs(120);
                continue;
            }
            const auto hwnd = ctx.refreshTargetHwnd();
            if (!hwnd) {
                ctx.state().set("start_game_intro_skip_score", state::StateValue{0.0});
                ctx.sleepMs(250);
                continue;
            }
            const auto region = regionFromRegistry(ctx, intro.region_key);
            const double thr = ctx.registryFloat(intro.threshold_key, 0.6);
            const auto hit = matchBestOnWindow(ctx, hwnd, *intro.original, intro.scaled, region, thr);
            ctx.state().set(intro.score_state_key, state::StateValue{hit.score});
            if (!hit.valid) {
                ctx.sleepMs(70);
                continue;
            }
            const bool has_region = region.has_value();
            const auto pt = ctx.matchCenterToScreen(hwnd, has_region ? region->data() : nullptr,
                                                    has_region, hit.center_x, hit.center_y);
            if (!pt) {
                ctx.sleepMs(200);
                continue;
            }
            ctx.clickScreen(pt->first, pt->second);
            intro_skip_armed = false;
            intro_skip_arm_until_mono = 0.0;
            ctx.state().set("start_game_intro_skip_score", state::StateValue{0.0});
            accept_armed = true;
            accept_arm_until_mono = mono_now + kAcceptArmTimeoutSec;
            ctx.sleepMs(350);
            continue;
        }

        ctx.state().set("start_game_intro_skip_score", state::StateValue{0.0});
        ctx.state().set("start_game_accept_score", state::StateValue{0.0});

        const auto uh = ctx.refreshSmartUpdaterHwnd();
        if (!uh) {
            ctx.state().set("start_game_launcher_score", state::StateValue{0.0});
            ctx.sleepMs(350);
            continue;
        }

        const auto region = regionFromRegistry(ctx, launcher.region_key);
        const double thr = ctx.registryFloat(launcher.threshold_key, 0.6);
        const auto hit = matchBestOnWindow(ctx, uh, *launcher.original, launcher.scaled, region, thr);
        ctx.state().set(launcher.score_state_key, state::StateValue{hit.score});
        if (!hit.valid) {
            ctx.sleepMs(120);
            continue;
        }
        if (mono_now - last_launcher_click_mono < kLauncherRetryCooldownSec) {
            ctx.sleepMs(100);
            continue;
        }
        const bool has_region = region.has_value();
        const auto pt = ctx.matchCenterToScreen(uh, has_region ? region->data() : nullptr, has_region,
                                                hit.center_x, hit.center_y);
        if (!pt) {
            ctx.sleepMs(200);
            continue;
        }
        ctx.clickScreen(pt->first, pt->second);
        last_launcher_click_mono = nowMono();
        ctx.invalidateSmartUpdaterHwndCache();

        const double deadline = last_launcher_click_mono + kLauncherDisappearWaitSec;
        bool launcher_gone = false;
        while (!ctx.stopRequested() && ctx.running() && !ctx.selectMode() && nowMono() < deadline) {
            ctx.sleepMs(80);
            if (!ctx.isStartGameLauncherEffective()) {
                break;
            }
            if (!ctx.refreshSmartUpdaterHwnd()) {
                launcher_gone = true;
                break;
            }
        }

        if (launcher_gone || !ctx.refreshSmartUpdaterHwnd()) {
            intro_skip_armed = true;
            intro_skip_arm_until_mono = nowMono() + kIntroSkipArmTimeoutSec;
            ctx.sleepMs(350);
            continue;
        }

        // Second click retry when launcher still visible after wait.
        const auto uh2 = ctx.refreshSmartUpdaterHwnd();
        if (!uh2) {
            intro_skip_armed = true;
            intro_skip_arm_until_mono = nowMono() + kIntroSkipArmTimeoutSec;
            ctx.sleepMs(350);
            continue;
        }
        const auto hit2 = matchBestOnWindow(ctx, uh2, *launcher.original, launcher.scaled, region, thr);
        ctx.state().set(launcher.score_state_key, state::StateValue{hit2.score});
        if (hit2.valid) {
            const auto pt2 = ctx.matchCenterToScreen(uh2, has_region ? region->data() : nullptr, has_region,
                                                     hit2.center_x, hit2.center_y);
            if (pt2) {
                ctx.clickScreen(pt2->first, pt2->second);
                last_launcher_click_mono = nowMono();
                ctx.invalidateSmartUpdaterHwndCache();
                const double deadline2 = last_launcher_click_mono + kLauncherDisappearWaitSec;
                while (!ctx.stopRequested() && ctx.running() && !ctx.selectMode() &&
                       nowMono() < deadline2) {
                    ctx.sleepMs(80);
                    if (!ctx.isStartGameLauncherEffective()) {
                        break;
                    }
                    if (!ctx.refreshSmartUpdaterHwnd()) {
                        launcher_gone = true;
                        break;
                    }
                }
            }
        }
        intro_skip_armed = true;
        intro_skip_arm_until_mono = nowMono() + kIntroSkipArmTimeoutSec;
        ctx.state().incrementInt("start_game_launcher_loop_count", 1);
        ctx.sleepMs(350);
#else
        ctx.sleepMs(60);
#endif
    }
}

}  // namespace pipela::core::workers
