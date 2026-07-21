#pragma once

#include <QMainWindow>
#include <QPoint>
#include <QSystemTrayIcon>
#include <QTimer>

#include <memory>
#include <optional>
#include <tuple>

#include "dock/dock_ui_phase.hpp"
#include "pipela/core/win32/foreground_monitor.hpp"

namespace pipela::native {
class DCompHud;
}
namespace pipela::ui::overlays {
class CursorHudController;
class DockChromeController;
class FlameStartBanner;
class GameOverlayWindow;
class OverlayManager;
class TemplateOverlayController;
class TitleStripWindow;
}
namespace pipela::app::input {
class InputHooksBridge;
}
namespace pipela::app::update {
class UpdateController;
}
namespace pipela::ui::widgets {
class ControlLeftResizeEdge;
}
namespace pipela::ui::shell {
class RuntimeBootstrap;
}

class ControlMainWindow;

class PipelaMainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit PipelaMainWindow(pipela::ui::shell::RuntimeBootstrap& runtime,
                              QWidget* parent = nullptr);
    ~PipelaMainWindow() override;

    ControlMainWindow* control() const { return control_; }
    pipela::ui::overlays::TemplateOverlayController* overlayController() const {
        return overlay_controller_.get();
    }

    int dockWidthLogical() const { return dock_w_log_; }
    void applyDockWidthLogical(int w_log);
    void dockToStandbyCentered(bool force = false);
    void ensureControlVisibleWithKillChrome();
    void prepareKillChromeShow();
    std::intptr_t titleStripAnchorHwnd() const;
    void setupTray();

protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;
    void changeEvent(QEvent* event) override;

private:
    void setupTitleStrip();
    void requestApplicationQuit();
    void tickGameWindowScreenCenter();
    void syncDevStandbyTitleStrip();
    void startClientDockBurst();
    void stopClientDockBurst();
    void maybeExtendClientPhaseDockBurst();
    void onClientDockBurstTick();
    void reassertTitleStripZOrder();

    pipela::ui::shell::RuntimeBootstrap& runtime_;
    QSystemTrayIcon* tray_{nullptr};
    ControlMainWindow* control_{nullptr};
    std::unique_ptr<pipela::ui::overlays::OverlayManager> overlay_mgr_;
    std::unique_ptr<pipela::ui::overlays::TemplateOverlayController> overlay_controller_;
    std::unique_ptr<pipela::ui::overlays::GameOverlayWindow> game_overlay_;
    std::unique_ptr<pipela::ui::overlays::TitleStripWindow> title_strip_;
    std::unique_ptr<pipela::ui::overlays::FlameStartBanner> flame_banner_;
    std::unique_ptr<pipela::native::DCompHud> cursor_hud_;
    std::unique_ptr<pipela::ui::overlays::CursorHudController> cursor_hud_ctrl_;
    std::unique_ptr<pipela::app::input::InputHooksBridge> input_hooks_;
    std::unique_ptr<pipela::app::update::UpdateController> update_controller_;
    std::unique_ptr<pipela::ui::overlays::DockChromeController> dock_chrome_;
    pipela::ui::widgets::ControlLeftResizeEdge* resize_edge_{nullptr};
    int dock_w_log_{420};
    std::intptr_t strip_anchor_hwnd_{0};
    std::intptr_t launcher_hwnd_cache_{0};
    bool last_target_minimized_{false};
    bool chrome_minimized_with_game_{false};
    bool user_dismissed_control_{false};
    pipela::ui::dock::UiDockPhase last_dock_phase_{pipela::ui::dock::UiDockPhase::Standby};
    QTimer* client_dock_burst_timer_{nullptr};
    QTimer* game_center_timer_{nullptr};
    int client_dock_burst_ticks_remaining_{0};
    std::intptr_t last_centered_target_hwnd_{0};
    double game_center_throttle_next_mono_{0.0};
    bool suppress_next_client_dock_burst_{false};
    bool frame_drag_active_{false};
    QPoint frame_drag_offset_;
    std::optional<std::tuple<int, int, int, int>> last_standby_sig_;
    pipela::core::win32::ForegroundWinEventMonitor foreground_monitor_;
};

int runQtApplication(int argc, char** argv);
