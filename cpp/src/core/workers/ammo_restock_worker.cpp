#include "pipela/core/workers/worker_context.hpp"
#include "pipela/core/workers/worker_loop_trace.hpp"

#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/settings_sequence_scroll.hpp"
#include "pipela/core/vision/roi.hpp"
#include "pipela/core/win32/input_synth.hpp"

#include <cmath>

namespace pipela::core::workers {

namespace {

struct AmmoSequenceBusyGuard {
    explicit AmmoSequenceBusyGuard(WorkerContext& ctx) : ctx_(ctx) {
        ctx_.state().set("ammo_restock_sequence_busy", state::StateValue{true});
    }
    ~AmmoSequenceBusyGuard() {
        ctx_.state().set("ammo_restock_sequence_busy", state::StateValue{false});
    }

    WorkerContext& ctx_;
};

void clickAtClient(WorkerContext& ctx, int client_x, int client_y) {
    win32::mouseMove(client_x, client_y);
    ctx.sleepMs(80);
    win32::mouseLeftClick();
}

void sendDigitKeys(WorkerContext& ctx) {
    constexpr unsigned short kVk4 = 0x34;
    constexpr unsigned short kVk5 = 0x35;
    constexpr unsigned short kVkEnter = 0x0D;
    win32::sendVirtualKey(kVk4, false);
    win32::sendVirtualKey(kVk4, true);
    ctx.sleepMs(50);
    win32::sendVirtualKey(kVk5, false);
    win32::sendVirtualKey(kVk5, true);
    ctx.sleepMs(50);
    win32::sendVirtualKey(kVkEnter, false);
    win32::sendVirtualKey(kVkEnter, true);
}

#if defined(PIPELA_HAS_OPENCV)

struct AmmoTemplateSlot {
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

bool ensureSlotLoaded(WorkerContext& ctx, AmmoTemplateSlot& slot) {
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

void rescaleSlots(WorkerContext& ctx,
                  AmmoTemplateSlot& buy,
                  AmmoTemplateSlot& inven,
                  AmmoTemplateSlot& bank,
                  double ratio) {
    if (buy.original) {
        buy.scaled = ctx.rescaleTemplate(*buy.original, ratio);
    }
    if (inven.original) {
        inven.scaled = ctx.rescaleTemplate(*inven.original, ratio);
    }
    if (bank.original) {
        bank.scaled = ctx.rescaleTemplate(*bank.original, ratio);
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
                   const AmmoTemplateSlot& slot,
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

void ammoRestockWorkerLoop(WorkerContext& ctx) {
    const WorkerLoopTracer trace("ammo_restock_loop");
#if defined(PIPELA_HAS_OPENCV)
    AmmoTemplateSlot buy{
        "AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH",
        "ammo_restock_buybutton_image_data",
        "ammo_buybutton_match_region",
        "ammo_restock_buybutton_threshold",
        "ammo_restock_buybutton_score",
        "ammo_buybutton",
    };
    AmmoTemplateSlot inven{
        "AMMO_RESTOCK_INVEN_IMAGE_PATH",
        "ammo_restock_inven_image_data",
        "ammo_inven_match_region",
        "ammo_restock_inven_threshold",
        "ammo_restock_inven_score",
        "ammo_inven",
    };
    AmmoTemplateSlot bank{
        "AMMO_RESTOCK_BANK_IMAGE_PATH",
        "ammo_restock_bank_image_data",
        "ammo_bank_match_region",
        "ammo_restock_bank_threshold",
        "ammo_restock_bank_score",
        "ammo_bank",
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
        bool active = false;
        if (auto v = ctx.state().get("ammo_restock_active")) {
            if (const auto* b = std::get_if<bool>(&*v)) {
                active = *b;
            }
        }
        if (!active) {
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

#if defined(PIPELA_HAS_OPENCV)
        if (!ensureSlotLoaded(ctx, buy) || !ensureSlotLoaded(ctx, inven) ||
            !ensureSlotLoaded(ctx, bank)) {
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
            rescaleSlots(ctx, buy, inven, bank, ratio);
            last_ratio = ratio;
        }

        int origin_x = 0;
        int origin_y = 0;
        const auto buy_hit = matchSlot(ctx, *full, buy, origin_x, origin_y);
        ctx.state().set(buy.score_state_key, state::StateValue{buy_hit.score});
        ctx.state().set("ammo_restock_inven_score", state::StateValue{0.0});
        ctx.state().set("ammo_restock_bank_score", state::StateValue{0.0});

        if (!buy_hit.valid) {
            pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatAmmoRestock, 0);
            ctx.sleepMs(200);
            continue;
        }

        pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatAmmoRestock, 1);

        {
            AmmoSequenceBusyGuard busy(ctx);
            trace.event("sequence_start buy_score=" + std::to_string(buy_hit.score));
            clickAtClient(ctx, origin_x + buy_hit.center_x, origin_y + buy_hit.center_y);
            ctx.sleepMs(100);
            sendDigitKeys(ctx);
            ctx.state().set("ammo_restock_buybutton_score", state::StateValue{0.0});
            ctx.sleepMs(150);

            full = vision::captureClientBgr(hwnd);
            if (!full) {
                ctx.sleepMs(200);
                continue;
            }
            const auto inven_hit = matchSlot(ctx, *full, inven, origin_x, origin_y);
            ctx.state().set(inven.score_state_key, state::StateValue{inven_hit.score});
            if (!inven_hit.valid) {
                ctx.sleepMs(200);
                continue;
            }
            pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatAmmoRestock, 2);
            clickAtClient(ctx, origin_x + inven_hit.center_x, origin_y + inven_hit.center_y);
            ctx.sleepMs(150);

            full = vision::captureClientBgr(hwnd);
            if (!full) {
                ctx.sleepMs(200);
                continue;
            }
            const auto bank_hit = matchSlot(ctx, *full, bank, origin_x, origin_y);
            ctx.state().set(bank.score_state_key, state::StateValue{bank_hit.score});
            if (!bank_hit.valid) {
                ctx.sleepMs(200);
                continue;
            }
            pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatAmmoRestock, 3);
            clickAtClient(ctx, origin_x + bank_hit.center_x, origin_y + bank_hit.center_y);
            ctx.state().incrementInt("ammo_restock_loop_count", 1);
            trace.event("sequence_complete loop_count+1");
            pipela::core::settings::seqScrollSet(pipela::core::settings::kFeatAmmoRestock, 0);
            ctx.sleepMs(100);
        }
#else
        (void)tick;
        ctx.sleepMs(100);
#endif
    }
}

}  // namespace pipela::core::workers
