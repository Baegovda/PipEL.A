#pragma once

#include <QObject>
#include <QTimer>
#include <QWidget>

#include <cstdint>
#include <functional>
#include <optional>
#include <tuple>

#include "dock/dock_ui_phase.hpp"
#include "overlay_manager.hpp"
#include "kill_counter_window.hpp"

namespace pipela::core::state {
class AppState;
}

namespace pipela::ui::overlays {

class KillCounterWindow;
class TemplateOverlayController;

// AGENT: Dock chrome — polls game HWND and positions overlay windows.
class DockChromeController : public QObject {
    Q_OBJECT
public:
    DockChromeController(OverlayManager& manager, QWidget* dock_host, QObject* parent = nullptr);

    void setGameHwnd(std::intptr_t hwnd);
    void setLauncherHwnd(std::intptr_t hwnd);
    void setOverlayHwnd(std::intptr_t hwnd);
    void setKillPanelVisible(bool visible);
    void setDockWidthLogical(int w_log);
    void setAppState(pipela::core::state::AppState* state);
    void setOverlayController(TemplateOverlayController* controller);
    void setUiDockPhase(pipela::ui::dock::UiDockPhase phase);
    void setOnAnchorClientRectChanged(std::function<void()> callback);
    void setUserDismissedChecker(std::function<bool()> checker);
    void setPrepareKillChromeShow(std::function<void()> callback);
    void setAfterChromeZOrderSynced(std::function<void()> callback);
    void start(int interval_ms = 120);
    void forceResync();

    OverlayManager& manager() { return manager_; }
    int dockWidthLogical() const { return dock_w_log_; }
    KillCounterWindow* killWindow() const { return kill_window_; }

private:
    void tick();
    void tickDockedToAnchor(std::intptr_t hwnd, int panel_height_log_override = 0);
    void tickDevStandbyPair();
    void applyControlDockGeometry(const pipela::app::dock::SideDockLayout& layout);
    void syncControlChromeZOrder(std::intptr_t anchor_hwnd);

    OverlayManager& manager_;
    QWidget* dock_host_{nullptr};
    KillCounterWindow* kill_window_{nullptr};
    QTimer* timer_{nullptr};
    pipela::core::state::AppState* state_{nullptr};
    TemplateOverlayController* overlay_controller_{nullptr};
    std::intptr_t game_hwnd_{0};
    std::intptr_t launcher_hwnd_{0};
    std::intptr_t overlay_hwnd_{0};
    bool kill_visible_{true};
    int dock_w_log_{420};
    double scale_{1.0};
    pipela::ui::dock::UiDockPhase ui_phase_{pipela::ui::dock::UiDockPhase::Standby};
    std::optional<std::tuple<int, int, int, int>> last_anchor_cr_sig_;
    std::uint64_t last_kill_dedupe_sig_{0};
    std::uint64_t last_control_dedupe_sig_{0};
    int kc_dock_retry_left_{0};
    std::intptr_t last_kc_z_anchor_{0};
    std::intptr_t last_control_z_anchor_{0};
    std::function<void()> on_anchor_cr_changed_;
    std::function<bool()> user_dismissed_checker_;
    std::function<void()> prepare_kill_chrome_show_;
    std::function<void()> after_chrome_z_order_synced_;
    static constexpr int kKcDockRetryMax = 12;
};

}  // namespace pipela::ui::overlays
