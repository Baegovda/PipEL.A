#include "dock/dock_chrome_restore.hpp"

#include <QTimer>

#include "overlays/dock_chrome_controller.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/window_ops.hpp"

namespace pipela::ui::dock {

namespace {

bool needsChromeRestore(const DockChromeRestoreContext& ctx,
                        std::intptr_t target_hwnd,
                        bool chrome_minimized_with_game,
                        bool user_dismissed_control) {
    if (chrome_minimized_with_game) {
        return true;
    }
    if (ctx.dock_host != nullptr) {
        if (ctx.dock_host->isMinimized()) {
            return true;
        }
        if (ctx.dock_host->isHidden() && !user_dismissed_control) {
            return true;
        }
    }
    if (!target_hwnd || pipela::core::win32::isWindowMinimized(target_hwnd)) {
        return false;
    }
    return false;
}

}  // namespace

bool restoreDockedChromeIfNeeded(DockChromeRestoreContext& ctx,
                                 pipela::ui::dock::UiDockPhase phase,
                                 std::intptr_t target_hwnd,
                                 bool game_just_restored,
                                 bool chrome_minimized_with_game,
                                 bool user_dismissed_control) {
    if (phase == UiDockPhase::Launcher || phase == UiDockPhase::Standby) {
        return false;
    }
    if (user_dismissed_control) {
        return false;
    }
    if (!game_just_restored &&
        !needsChromeRestore(ctx, target_hwnd, chrome_minimized_with_game, user_dismissed_control)) {
        return false;
    }
    if (ctx.dock_host != nullptr) {
#ifdef _WIN32
        const std::intptr_t hwnd =
            static_cast<std::intptr_t>(static_cast<qintptr>(ctx.dock_host->winId()));
        pipela::core::win32::windowRestoreNormal(hwnd);
#endif
        if (ctx.dock_host->isMinimized()) {
            ctx.dock_host->showNormal();
        }
        ctx.dock_host->show();
        ctx.dock_host->raise();
        ctx.dock_host->activateWindow();
    }
    if (ctx.title_strip != nullptr) {
        ctx.title_strip->show();
        ctx.title_strip->raise();
    }
    if (ctx.dock_chrome != nullptr) {
        ctx.dock_chrome->forceResync();
        auto* dc = ctx.dock_chrome;
        QTimer::singleShot(120, dc, [dc]() {
            if (dc != nullptr) {
                dc->forceResync();
            }
        });
    }
    return true;
}

}  // namespace pipela::ui::dock
