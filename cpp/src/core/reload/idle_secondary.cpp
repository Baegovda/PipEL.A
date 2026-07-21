#include "pipela/core/reload/idle_secondary.hpp"

#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/workers/worker_context.hpp"

namespace pipela::core::reload {

void refreshIdleBulletVaultScores(workers::WorkerContext& ctx, std::intptr_t hwnd) {
#if defined(PIPELA_HAS_OPENCV)
    if (auto bu_path = ctx.resolveTemplatePath("RELOAD_BULLET_IMAGE_PATH")) {
        auto bullet = ctx.loadTemplate(*bu_path, "reload_bullet_image_data");
        if (bullet) {
            std::optional<std::array<double, 4>> roi_bu;
            if (auto s = ctx.registryString("reload_bullet_match_region")) {
                roi_bu = registry::parseRegionJson(*s);
            }
            if (roi_bu) {
                if (auto scr = ctx.captureRegion(hwnd, roi_bu->data())) {
                    const auto hit = ctx.matchTemplate(
                        *scr, *bullet, ctx.registryFloat("reload_bullet_threshold", 0.6));
                    ctx.state().set("bullet_detection_score", state::StateValue{hit.score});
                }
            }
        }
    }
    std::optional<std::array<double, 4>> roi_vault;
    if (auto s = ctx.registryString("reload_vault_match_region")) {
        roi_vault = registry::parseRegionJson(*s);
    }
    if (roi_vault) {
        if (auto scr = ctx.captureRegion(hwnd, roi_vault->data())) {
            if (auto vpath = ctx.resolveTemplatePath("RELOAD_VAULT_IMAGE_PATH")) {
                auto vault = ctx.loadTemplate(*vpath, "reload_vault_image_data");
                if (vault) {
                    const auto hit = ctx.matchTemplate(
                        *scr, *vault, ctx.registryFloat("reload_vault_threshold", 0.6));
                    ctx.state().set("vault_detection_score", state::StateValue{hit.score});
                }
            }
        }
    }
#else
    (void)ctx;
    (void)hwnd;
#endif
}

}  // namespace pipela::core::reload
