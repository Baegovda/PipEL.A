#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/reload/sequence.hpp"
#include "pipela/core/win32/input_synth.hpp"

#include <chrono>

namespace pipela::core::workers {

namespace {

constexpr double kReloadRearmCooldownSec = 10.0;

void disableFlameTrigger(WorkerContext& ctx) {
    if (ctx.flameTriggerActive()) {
        ctx.state().set("flame_trigger_active", state::StateValue{false});
        win32::mouseRightUp();
    }
}

}  // namespace

void reloadWorkerLoop(WorkerContext& ctx) {
    enum class Phase { Idle, NobulletLatched, BulletMatched };
    Phase phase = Phase::Idle;
#if defined(PIPELA_HAS_OPENCV)
    std::optional<vision::BgrImage> nobullet_template;
    std::optional<vision::BgrImage> bullet_template;
    std::optional<vision::BgrImage> scaled_nobullet;
    std::optional<vision::BgrImage> scaled_bullet;
    double last_ratio = 0.0;
    std::string last_nb_path;
    std::string last_bu_path;
#endif
    int path_check = 0;
    int tick = 0;
    bool reload_had_ft = false;

    while (!ctx.stopRequested()) {
        if (++tick % 10 == 0) {
            ctx.refreshSnapshot();
        }
        if (!ctx.running() || ctx.selectMode()) {
            ctx.sleepMs(100);
            continue;
        }
        if (!ctx.registryBool("reload_active", true)) {
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
        if (++path_check >= 5) {
            path_check = 0;
            const auto nb_path = ctx.registryString("RELOAD_NOBULLET_IMAGE_PATH");
            const auto bu_path = ctx.registryString("RELOAD_BULLET_IMAGE_PATH");
            if (nb_path && *nb_path != last_nb_path) {
                nobullet_template = ctx.loadTemplate(*nb_path, "reload_nobullet_image_data");
                scaled_nobullet = nobullet_template;
                last_nb_path = *nb_path;
                last_ratio = 0.0;
            }
            if (bu_path && *bu_path != last_bu_path) {
                bullet_template = ctx.loadTemplate(*bu_path, "reload_bullet_image_data");
                scaled_bullet = bullet_template;
                last_bu_path = *bu_path;
                last_ratio = 0.0;
            }
        }
        if (!nobullet_template || !bullet_template) {
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
            scaled_nobullet = ctx.rescaleTemplate(*nobullet_template, ratio);
            scaled_bullet = ctx.rescaleTemplate(*bullet_template, ratio);
            last_ratio = ratio;
        }
        if (!scaled_nobullet || !scaled_bullet) {
            ctx.sleepMs(500);
            continue;
        }

        const double thr_nb = ctx.registryFloat("reload_nobullet_threshold", 0.6);
        const double thr_bu = ctx.registryFloat("reload_bullet_threshold", 0.6);
        const int ammo_raw = ctx.registryInt("reload_ammo_count", 45);
        const auto [ammo_n, ammo_digits] = reload::clampAmmoCount(ammo_raw);

        if (phase == Phase::Idle) {
            std::optional<std::array<double, 4>> roi_nb;
            if (auto s = ctx.registryString("reload_nobullet_match_region")) {
                roi_nb = registry::parseRegionJson(*s);
            }
            auto screen = roi_nb ? ctx.captureRegion(hwnd, roi_nb->data()) : full;
            if (!screen) {
                ctx.sleepMs(1000);
                continue;
            }
            const auto hit = ctx.matchTemplate(*screen, *scaled_nobullet, thr_nb);
            ctx.state().set("nobullet_detection_score", state::StateValue{hit.score});
            ctx.state().set("bullet_detection_score", state::StateValue{0.0});
            ctx.state().set("vault_detection_score", state::StateValue{0.0});
            if (hit.valid) {
                ctx.state().set("nobullet_detected", state::StateValue{true});
                reload_had_ft = ctx.flameTriggerActive();
                if (reload_had_ft) {
                    ctx.state().set("flame_trigger_reload_teardown_preserve_hud", state::StateValue{true});
                }
                disableFlameTrigger(ctx);
                const auto now_mono = std::chrono::duration<double>(
                                          std::chrono::steady_clock::now().time_since_epoch())
                                          .count();
                ctx.state().set("reload_nobullet_arm_until_mono",
                                state::StateValue{now_mono + kReloadRearmCooldownSec});
                phase = Phase::NobulletLatched;
            }
            ctx.sleepMs(1000);
            continue;
        }

        if (phase == Phase::NobulletLatched) {
            std::optional<std::array<double, 4>> roi_bu;
            if (auto s = ctx.registryString("reload_bullet_match_region")) {
                roi_bu = registry::parseRegionJson(*s);
            }
            auto screen = roi_bu ? ctx.captureRegion(hwnd, roi_bu->data()) : full;
            if (!screen) {
                ctx.sleepMs(200);
                continue;
            }
            const auto hit = ctx.matchTemplate(*screen, *scaled_bullet, thr_bu);
            ctx.state().set("bullet_detection_score", state::StateValue{hit.score});
            if (hit.valid) {
                win32::mouseMove(hit.center_x, hit.center_y);
                win32::mouseLeftDoubleClick();
                for (char ch : ammo_digits) {
                    if (ch >= '0' && ch <= '9') {
                        const unsigned short vk =
                            static_cast<unsigned short>(0x30 + (ch - '0'));
                        win32::sendVirtualKey(vk, false);
                        win32::sendVirtualKey(vk, true);
                    }
                }
                win32::sendVirtualKey(0x0D, false);
                win32::sendVirtualKey(0x0D, true);
                ctx.state().incrementInt("reload_success_count", 1);
                ctx.state().set("nobullet_detected", state::StateValue{false});
                if (reload_had_ft && ctx.registryBool("flame_trigger_feature_enabled", true)) {
                    ctx.state().set("flame_trigger_active", state::StateValue{true});
                }
                reload_had_ft = false;
                phase = Phase::Idle;
            }
            ctx.sleepMs(200);
            continue;
        }
#else
        (void)phase;
        (void)path_check;
        (void)reload_had_ft;
        ctx.sleepMs(100);
#endif
    }
}

}  // namespace pipela::core::workers
