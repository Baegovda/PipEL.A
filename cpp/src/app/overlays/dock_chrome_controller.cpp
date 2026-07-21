#include "dock_chrome_controller.hpp"

#include <cstdlib>
#include <iostream>
#include <string>

#include <QTimer>

#include "dock/dock_chrome_apply.hpp"
#include "dock/dock_z_stack.hpp"
#include "dock/side_dock_layout.hpp"
#include "kill_counter_window.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/window_ops.hpp"
#include "shell/dev_ui_mode.hpp"
#include "theme/dpi_helpers.hpp"

#include <QGuiApplication>
#include <QScreen>

namespace pipela::ui::overlays {

namespace {

bool debugKillDockEnabled() {
    const char* raw = std::getenv("PIPELA_DEBUG_KILL_DOCK");
    if (raw == nullptr || raw[0] == '\0') {
        return false;
    }
    const std::string v(raw);
    return v == "1" || v == "true" || v == "yes" || v == "on";
}

void kcDockDebug(const char* msg) {
    if (!debugKillDockEnabled()) {
        return;
    }
    std::cerr << "[KillDock][debug] " << msg << std::endl;
}

std::intptr_t qtWidgetHwnd(QWidget* w) {
    if (w == nullptr) {
        return 0;
    }
    return static_cast<std::intptr_t>(w->winId());
}

bool killCounterEnabledFromState(pipela::core::state::AppState* state) {
    if (state != nullptr) {
        const auto v = state->get("kill_counter_enabled");
        if (v && std::holds_alternative<bool>(*v)) {
            return std::get<bool>(*v);
        }
    }
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find("kill_counter_enabled");
    if (it == all.end()) {
        return true;
    }
    return it->second == "true" || it->second == "1";
}

bool userDismissed(const std::function<bool()>& checker) {
    return checker && checker();
}

constexpr int kLauncherDebugPanelHeightLog = 740;
constexpr int kClientRectDeadbandPhys = 2;

bool clientRectMeaningfullyChanged(const std::tuple<int, int, int, int>& prev,
                                   const std::tuple<int, int, int, int>& curr) {
    return std::abs(std::get<0>(prev) - std::get<0>(curr)) > kClientRectDeadbandPhys ||
           std::abs(std::get<1>(prev) - std::get<1>(curr)) > kClientRectDeadbandPhys ||
           std::abs(std::get<2>(prev) - std::get<2>(curr)) > kClientRectDeadbandPhys ||
           std::abs(std::get<3>(prev) - std::get<3>(curr)) > kClientRectDeadbandPhys;
}

}  // namespace

DockChromeController::DockChromeController(OverlayManager& manager, QWidget* dock_host,
                                           QObject* parent)
    : QObject(parent), manager_(manager), dock_host_(dock_host) {
    kill_window_ = new KillCounterWindow();
    timer_ = new QTimer(this);
    connect(timer_, &QTimer::timeout, this, &DockChromeController::tick);
}

void DockChromeController::setGameHwnd(std::intptr_t hwnd) { game_hwnd_ = hwnd; }

void DockChromeController::setLauncherHwnd(std::intptr_t hwnd) { launcher_hwnd_ = hwnd; }

void DockChromeController::setOverlayHwnd(std::intptr_t hwnd) { overlay_hwnd_ = hwnd; }

void DockChromeController::setKillPanelVisible(bool visible) { kill_visible_ = visible; }

void DockChromeController::setDockWidthLogical(int w_log) { dock_w_log_ = w_log; }

void DockChromeController::setAppState(pipela::core::state::AppState* state) {
    state_ = state;
    if (kill_window_ != nullptr) {
        kill_window_->setAppState(state_);
    }
}

void DockChromeController::setOverlayController(TemplateOverlayController* controller) {
    overlay_controller_ = controller;
    if (kill_window_ != nullptr) {
        kill_window_->setOverlayController(overlay_controller_);
    }
}

void DockChromeController::setUiDockPhase(pipela::ui::dock::UiDockPhase phase) {
    ui_phase_ = phase;
}

void DockChromeController::setOnAnchorClientRectChanged(std::function<void()> callback) {
    on_anchor_cr_changed_ = std::move(callback);
}

void DockChromeController::setUserDismissedChecker(std::function<bool()> checker) {
    user_dismissed_checker_ = std::move(checker);
}

void DockChromeController::setPrepareKillChromeShow(std::function<void()> callback) {
    prepare_kill_chrome_show_ = std::move(callback);
}

void DockChromeController::setAfterChromeZOrderSynced(std::function<void()> callback) {
    after_chrome_z_order_synced_ = std::move(callback);
}

void DockChromeController::start(int interval_ms) {
    timer_->start(interval_ms);
    tick();
}

void DockChromeController::forceResync() {
    last_kill_dedupe_sig_ = 0;
    last_control_dedupe_sig_ = 0;
    last_anchor_cr_sig_.reset();
    last_control_z_anchor_ = 0;
    last_kc_z_anchor_ = 0;
    kc_dock_retry_left_ = 0;
    tick();
}

void DockChromeController::applyControlDockGeometry(
    const pipela::app::dock::SideDockLayout& layout) {
    if (dock_host_ == nullptr || !layout.valid()) {
        return;
    }
    std::intptr_t anchor = game_hwnd_;
    if (!anchor || !pipela::core::win32::isWindow(anchor)) {
        anchor = launcher_hwnd_;
    }
    pipela::app::dock::applySideDockLayoutToWidget(dock_host_, layout, anchor);
}

void DockChromeController::syncControlChromeZOrder(std::intptr_t anchor_hwnd) {
    if (dock_host_ == nullptr || !anchor_hwnd) {
        return;
    }
    if (userDismissed(user_dismissed_checker_)) {
        return;
    }
    if (ui_phase_ == pipela::ui::dock::UiDockPhase::Client ||
        (ui_phase_ == pipela::ui::dock::UiDockPhase::Launcher &&
         pipela::ui::shell::pipelaLauncherDebugChromeEnabled())) {
        if (dock_host_->isMinimized()) {
            dock_host_->showNormal();
        }
        if (!dock_host_->isVisible()) {
            dock_host_->show();
            dock_host_->raise();
        }
    }
    const std::intptr_t dock_hwnd = qtWidgetHwnd(dock_host_);
    if (!dock_hwnd) {
        return;
    }
    const bool anchor_changed = last_control_z_anchor_ != anchor_hwnd;
    pipela::ui::dock::syncDockedChromeZOrder(dock_hwnd, anchor_hwnd, overlay_hwnd_,
                                             anchor_changed, anchor_changed);
    last_control_z_anchor_ = anchor_hwnd;
}

void DockChromeController::tick() {
    if (ui_phase_ == pipela::ui::dock::UiDockPhase::Launcher) {
        if (!pipela::ui::shell::pipelaLauncherDebugChromeEnabled()) {
            if (dock_host_ != nullptr) {
                dock_host_->hide();
            }
            if (kill_window_ != nullptr) {
                kill_window_->hide();
            }
            return;
        }
        std::intptr_t hwnd = launcher_hwnd_;
        if (!hwnd || !pipela::core::win32::isWindow(hwnd)) {
            hwnd = pipela::core::win32::findSmartUpdaterWindow();
            launcher_hwnd_ = hwnd;
        }
        if (!hwnd || !pipela::core::win32::isWindow(hwnd)) {
            kcDockDebug("tick: launcher debug — no anchor hwnd");
            return;
        }
        tickDockedToAnchor(hwnd, kLauncherDebugPanelHeightLog);
        return;
    }
    if (pipela::ui::shell::pipelaDevUiStandbyChrome(ui_phase_)) {
        tickDevStandbyPair();
        return;
    }
    if (ui_phase_ == pipela::ui::dock::UiDockPhase::Standby) {
        if (kill_window_ != nullptr) {
            kill_window_->hide();
        }
        return;
    }

    std::intptr_t hwnd = game_hwnd_;
    if (!hwnd || !pipela::core::win32::isWindow(hwnd)) {
        hwnd = pipela::core::win32::findEternalcityWindow();
        game_hwnd_ = hwnd;
    }
    if (!hwnd || !pipela::core::win32::isWindow(hwnd)) {
        kcDockDebug("tick: no anchor hwnd");
        return;
    }
    tickDockedToAnchor(hwnd);
}

void DockChromeController::tickDockedToAnchor(std::intptr_t hwnd, int panel_height_log_override) {
    scale_ = pipela::ui::theme::win32DpiScaleForHwnd(hwnd);

    const auto cr = pipela::core::win32::getClientRectScreen(hwnd);
    const int cl = std::get<0>(cr);
    const int ct = std::get<1>(cr);
    const int cright = std::get<2>(cr);
    const int cbottom = std::get<3>(cr);

    const std::tuple<int, int, int, int> cr_sig{cl, ct, cright, cbottom};
    if (!last_anchor_cr_sig_ || clientRectMeaningfullyChanged(*last_anchor_cr_sig_, cr_sig)) {
        last_anchor_cr_sig_ = cr_sig;
        last_kill_dedupe_sig_ = 0;
        last_control_dedupe_sig_ = 0;
        last_control_z_anchor_ = 0;
        last_kc_z_anchor_ = 0;
        kcDockDebug("anchor client rect changed → invalidate dedupe");
        if (on_anchor_cr_changed_) {
            on_anchor_cr_changed_();
        }
    }

    manager_.syncFromGameClient(hwnd, cl, ct, cright, cbottom, dock_w_log_, scale_,
                                kill_visible_, panel_height_log_override);

    if (!userDismissed(user_dismissed_checker_)) {
        const auto& ctrl_lay = manager_.dock().last_layout;
        if (ctrl_lay.dedupe_sig != last_control_dedupe_sig_) {
            last_control_dedupe_sig_ = ctrl_lay.dedupe_sig;
            applyControlDockGeometry(ctrl_lay);
        }
        syncControlChromeZOrder(hwnd);
    }

    const bool kc_wanted =
        kill_window_ != nullptr && kill_visible_ && killCounterEnabledFromState(state_);
    if (kc_wanted) {
        if (prepare_kill_chrome_show_) {
            prepare_kill_chrome_show_();
        }
        const auto& klay = manager_.killFloater().dock_layout;
        if (klay.w_log <= 0 || klay.h_log <= 0 || !klay.valid()) {
            kcDockDebug("kill layout invalid — schedule retry");
            if (kc_dock_retry_left_ < kKcDockRetryMax) {
                ++kc_dock_retry_left_;
                const int delay_ms = std::max(48, std::min(320, 40 + kc_dock_retry_left_ * 12));
                QTimer::singleShot(delay_ms, this, &DockChromeController::tick);
            }
        } else {
            kc_dock_retry_left_ = 0;
            if (klay.dedupe_sig != last_kill_dedupe_sig_) {
                last_kill_dedupe_sig_ = klay.dedupe_sig;
                kill_window_->applyDockLayout(klay, panel_height_log_override, hwnd);
            } else if (!kill_window_->isVisible()) {
                kill_window_->show();
            }
            const std::intptr_t kc_hwnd = qtWidgetHwnd(kill_window_);
            if (kc_hwnd && pipela::core::win32::isWindow(hwnd)) {
                const bool set_owner = last_kc_z_anchor_ != hwnd;
                pipela::ui::dock::syncDockedChromeZOrder(kc_hwnd, hwnd, overlay_hwnd_, set_owner,
                                                         set_owner);
                last_kc_z_anchor_ = hwnd;
            }
        }
    } else if (kill_window_ != nullptr) {
        kill_window_->hide();
    }
    if (after_chrome_z_order_synced_) {
        after_chrome_z_order_synced_();
    }
}

void DockChromeController::tickDevStandbyPair() {
    if (dock_host_ == nullptr) {
        return;
    }
    if (!userDismissed(user_dismissed_checker_)) {
        if (!dock_host_->isVisible()) {
            dock_host_->show();
            dock_host_->raise();
        }
    }
    scale_ = 1.0;
    if (QScreen* scr = QGuiApplication::primaryScreen()) {
        const qreal dpr = scr->devicePixelRatio();
        if (dpr > 0.01) {
            scale_ = dpr;
        }
    }
    const QRect mg = dock_host_->geometry();
    const int w_log = dock_w_log_;
    if (kill_window_ != nullptr && kill_visible_ && killCounterEnabledFromState(state_)) {
        if (prepare_kill_chrome_show_) {
            prepare_kill_chrome_show_();
        }
        const int x_log = mg.x() + mg.width();
        const int y_log = mg.y();
        const int h_log = std::max(8, mg.height());
        pipela::app::dock::SideDockLayout lay;
        lay.x_log = x_log;
        lay.y_log = y_log;
        lay.w_log = w_log;
        lay.h_log = h_log;
        lay.x_phys = static_cast<int>(std::lround(x_log * scale_));
        lay.y_phys = static_cast<int>(std::lround(y_log * scale_));
        lay.fw_phys = static_cast<int>(std::lround(w_log * scale_));
        lay.fh_phys = static_cast<int>(std::lround(h_log * scale_));
        lay.scale = scale_;
        lay.dedupe_sig = pipela::app::dock::sideDockDedupeSig(
            x_log, 0, 0, 0, 0, lay.x_phys, lay.y_phys, lay.fw_phys, lay.fh_phys, true);
        if (lay.dedupe_sig != last_kill_dedupe_sig_) {
            last_kill_dedupe_sig_ = lay.dedupe_sig;
            kill_window_->applyDockLayout(lay, h_log, 0);
        } else if (!kill_window_->isVisible()) {
            kill_window_->show();
        }
    } else if (kill_window_ != nullptr) {
        kill_window_->hide();
    }
}

}  // namespace pipela::ui::overlays
