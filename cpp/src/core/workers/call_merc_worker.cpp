#include "pipela/core/workers/worker_context.hpp"
#include "pipela/core/workers/worker_loop_trace.hpp"

#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/settings_sequence_scroll.hpp"
#include "pipela/core/vision/roi.hpp"
#include "pipela/core/win32/input_synth.hpp"

#include <chrono>
#include <cmath>

namespace pipela::core::workers {

namespace {

constexpr double kArmCooldownSec = 10.0;
constexpr double kStuckTimeoutSec = 5.0;

double nowMono() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

void clickAtClient(WorkerContext& ctx, int client_x, int client_y, bool double_click) {
    win32::mouseMove(client_x, client_y);
    ctx.sleepMs(80);
    if (double_click) {
        win32::mouseLeftDoubleClick();
    } else {
        win32::mouseLeftClick();
    }
}

void disableFlameTrigger(WorkerContext& ctx) {
    if (ctx.flameTriggerActive()) {
        ctx.state().set("flame_trigger_active", state::StateValue{false});
        win32::mouseRightUp();
    }
}

#if defined(PIPELA_HAS_OPENCV)

struct MercTemplateSlot {
    const char* path_snapshot_key;
    const char* registry_data_key;
    const char* roi_snapshot_key;
    const char* threshold_snapshot_key;
    const char* score_state_key;
    const char* last_hit_kind;

    std::optional<vision::BgrImage> original;
    std::optional<vision::BgrImage> scaled;
    std::string last_path;
};

bool ensureSlotLoaded(WorkerContext& ctx, MercTemplateSlot& slot) {
    const auto path = ctx.resolveTemplatePath(slot.path_snapshot_key);
    if (!path || path->empty()) {
        return false;
    }
    if (*path != slot.last_path) {
        slot.original = ctx.loadTemplate(*path, slot.registry_data_key);
        slot.scaled = slot.original;
        slot.last_path = *path;
    }
    return static_cast<bool>(slot.original);
}

void rescaleSlots(WorkerContext& ctx, MercTemplateSlot* slots, int count, double ratio) {
    for (int i = 0; i < count; ++i) {
        if (slots[i].original) {
            slots[i].scaled = ctx.rescaleTemplate(*slots[i].original, ratio);
        }
    }
}

std::optional<vision::BgrImage> captureRoiFromRegistry(WorkerContext& ctx,
                                                       const vision::BgrImage& full,
                                                       const char* roi_snapshot_key,
                                                       int& origin_x,
                                                       int& origin_y) {
    origin_x = 0;
    origin_y = 0;
    if (auto reg_s = ctx.registryString(roi_snapshot_key)) {
        if (auto region = registry::parseRegionJson(*reg_s)) {
            if (auto px = vision::regionPixels(full.width, full.height, region->data())) {
                origin_x = (*px)[0];
                origin_y = (*px)[1];
                return vision::sliceBgr(full, (*px)[0], (*px)[1], (*px)[2], (*px)[3]);
            }
        }
    }
    return full;
}

MatchHit matchSlot(WorkerContext& ctx,
                   const vision::BgrImage& full,
                   const MercTemplateSlot& slot,
                   int& origin_x,
                   int& origin_y) {
    MatchHit miss;
    if (!slot.scaled) {
        return miss;
    }
    auto screen = captureRoiFromRegistry(ctx, full, slot.roi_snapshot_key, origin_x, origin_y);
    if (!screen) {
        return miss;
    }
    const double thr = ctx.registryFloat(slot.threshold_snapshot_key, 0.6);
    return ctx.matchTemplate(*screen, *slot.scaled, thr, slot.last_hit_kind);
}

#endif

}  // namespace

void callMercWorkerLoop(WorkerContext& ctx) {
    const WorkerLoopTracer trace("call_merc_loop");
    enum class Phase { WatchTrigger = 0, Contract = 1, Call = 2, Close = 3 };
    Phase phase = Phase::WatchTrigger;
    double arm_until_mono = 0.0;
    double phase_started_mono = 0.0;
    bool restore_ft_after_cycle = false;
#if defined(PIPELA_HAS_OPENCV)
    MercTemplateSlot slots[4] = {
        {"CALL_MERC_1_IMAGE_PATH", "call_merc_1_image_data", "call_merc_1_match_region",
         "call_merc_1_threshold", "call_merc_1_score", "call_merc_1"},
        {"CALL_MERC_2_IMAGE_PATH", "call_merc_2_image_data", "call_merc_2_match_region",
         "call_merc_2_threshold", "call_merc_2_score", "call_merc_2"},
        {"CALL_MERC_3_IMAGE_PATH", "call_merc_3_image_data", "call_merc_3_match_region",
         "call_merc_3_threshold", "call_merc_3_score", "call_merc_3"},
        {"CALL_MERC_4_IMAGE_PATH", "call_merc_4_image_data", "call_merc_4_match_region",
         "call_merc_4_threshold", "call_merc_4_score", "call_merc_4"},
    };
    double last_ratio = 0.0;
    int tick = 0;
#endif

    while (!ctx.stopRequested()) {
        if (++tick % 10 == 0) {
            ctx.refreshSnapshot();
        }
        if (!ctx.running() || ctx.selectMode()) {
            ctx.sleepMs(100);
            continue;
        }
        if (!ctx.registryBool("call_merc_active", true)) {
            phase = Phase::WatchTrigger;
            pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatCallMerc, 0);
            ctx.state().set("call_merc_sequence_busy", state::StateValue{false});
            restore_ft_after_cycle = false;
            arm_until_mono = 0.0;
            ctx.sleepMs(100);
            continue;
        }
        const auto hwnd = ctx.targetHwnd();
        if (!hwnd) {
            ctx.sleepMs(100);
            continue;
        }
        if (ctx.powerSaveActive()) {
            ctx.sleepMs(2500);
            continue;
        }

        ctx.state().set("call_merc_sequence_busy", state::StateValue{phase != Phase::WatchTrigger});

#if defined(PIPELA_HAS_OPENCV)
        bool templates_ok = true;
        for (auto& slot : slots) {
            if (!ensureSlotLoaded(ctx, slot)) {
                templates_ok = false;
                break;
            }
        }
        if (!templates_ok) {
            ctx.sleepMs(1000);
            continue;
        }

        auto full = vision::captureClientBgr(hwnd);
        if (!full) {
            ctx.sleepMs(500);
            continue;
        }
        const double ratio = vision::scaleRatio(full->height);
        if (std::abs(ratio - last_ratio) > 0.01) {
            rescaleSlots(ctx, slots, 4, ratio);
            last_ratio = ratio;
        }

        const auto now = nowMono();
        if (phase != Phase::WatchTrigger && phase_started_mono > 0.0 &&
            (now - phase_started_mono) > kStuckTimeoutSec) {
            phase = Phase::WatchTrigger;
            ctx.state().set("call_merc_sequence_busy", state::StateValue{false});
            restore_ft_after_cycle = false;
            ctx.sleepMs(100);
            continue;
        }

        int origin_x = 0;
        int origin_y = 0;

        if (phase == Phase::WatchTrigger) {
            if (now < arm_until_mono) {
                ctx.sleepMs(60);
                continue;
            }
            const auto hit = matchSlot(ctx, *full, slots[0], origin_x, origin_y);
            ctx.state().set(slots[0].score_state_key, state::StateValue{hit.score});
            if (!hit.valid) {
                ctx.sleepMs(120);
                continue;
            }
            restore_ft_after_cycle = ctx.flameTriggerActive();
            disableFlameTrigger(ctx);
            phase = Phase::Contract;
            trace.event("phase WatchTrigger->Contract score=" + std::to_string(hit.score));
            pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatCallMerc, 1);
            phase_started_mono = now;
            ctx.sleepMs(120);
            continue;
        }

        if (phase == Phase::Contract) {
            const auto hit = matchSlot(ctx, *full, slots[1], origin_x, origin_y);
            ctx.state().set(slots[1].score_state_key, state::StateValue{hit.score});
            if (!hit.valid) {
                ctx.sleepMs(80);
                continue;
            }
            clickAtClient(ctx, origin_x + hit.center_x, origin_y + hit.center_y, true);
            phase = Phase::Call;
            trace.event("phase Contract->Call");
            pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatCallMerc, 2);
            phase_started_mono = now;
            ctx.sleepMs(120);
            continue;
        }

        if (phase == Phase::Call) {
            full = vision::captureClientBgr(hwnd);
            if (!full) {
                ctx.sleepMs(200);
                continue;
            }
            const auto hit = matchSlot(ctx, *full, slots[2], origin_x, origin_y);
            ctx.state().set(slots[2].score_state_key, state::StateValue{hit.score});
            if (!hit.valid) {
                ctx.sleepMs(80);
                continue;
            }
            clickAtClient(ctx, origin_x + hit.center_x, origin_y + hit.center_y, false);
            phase = Phase::Close;
            trace.event("phase Call->Close");
            pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatCallMerc, 3);
            phase_started_mono = now;
            ctx.sleepMs(120);
            continue;
        }

        if (phase == Phase::Close) {
            full = vision::captureClientBgr(hwnd);
            if (!full) {
                ctx.sleepMs(200);
                continue;
            }
            const auto hit = matchSlot(ctx, *full, slots[3], origin_x, origin_y);
            ctx.state().set(slots[3].score_state_key, state::StateValue{hit.score});
            if (!hit.valid) {
                ctx.sleepMs(80);
                continue;
            }
            clickAtClient(ctx, origin_x + hit.center_x, origin_y + hit.center_y, false);
            ctx.state().incrementInt("call_merc_loop_count", 1);
            trace.event("cycle_complete loop_count+1 restore_ft=" +
                        std::string(restore_ft_after_cycle ? "1" : "0"));
            if (restore_ft_after_cycle && ctx.registryBool("flame_trigger_feature_enabled", true)) {
                ctx.state().set("flame_trigger_active", state::StateValue{true});
            }
            restore_ft_after_cycle = false;
            arm_until_mono = now + kArmCooldownSec;
            phase = Phase::WatchTrigger;
            pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatCallMerc, 0);
            phase_started_mono = 0.0;
            ctx.state().set("call_merc_sequence_busy", state::StateValue{false});
            ctx.sleepMs(150);
            continue;
        }
#else
        (void)phase;
        (void)arm_until_mono;
        (void)phase_started_mono;
        (void)restore_ft_after_cycle;
        ctx.sleepMs(100);
#endif
    }
}

}  // namespace pipela::core::workers
