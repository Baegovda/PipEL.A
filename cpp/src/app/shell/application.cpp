#include "application.hpp"

#include <cmath>
#include <chrono>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <shobjidl.h>
#endif

#include <QApplication>
#include <QEvent>
#include <QFont>
#include <QGuiApplication>
#include <QMenu>
#include <QMouseEvent>
#include <QResizeEvent>
#include <QScreen>
#include <QTimer>
#include <QWindow>

#include <cstdio>

#include "control/control_main_window.hpp"
#include "dock/dock_chrome_restore.hpp"
#include "dock/dock_panel_pair_resize.hpp"
#include "dock/side_dock_layout.hpp"
#include "dock/dock_ui_phase.hpp"
#include "dock/dock_z_stack.hpp"
#include "input/hooks_bridge.hpp"
#include "overlays/cursor_hud_controller.hpp"
#include "overlays/dock_chrome_controller.hpp"
#include "overlays/flame_start_banner.hpp"
#include "overlays/game_overlay_window.hpp"
#include "overlays/overlay_manager.hpp"
#include "overlays/title_strip_geometry.hpp"
#include "overlays/title_strip_window.hpp"
#include "overlays/template_overlay_controller.hpp"
#include "panels/kill_counter_tier_table_dialog.hpp"
#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/feature_trace_log.hpp"
#include "pipela/core/version.hpp"
#include "pipela/core/win32/foreground_monitor.hpp"
#include "pipela/core/win32/window_ops.hpp"
#include "pipela/core/workers/worker_context.hpp"
#include "shell/client_transition_debug.hpp"
#include "shell/dev_ui_mode.hpp"
#include "shell/frame_timing.hpp"
#include "shell/runtime_bootstrap.hpp"
#include "shell/splash_screen.hpp"
#include "shell/qt_icons.hpp"
#include "shell/taskbar_hide_filter.hpp"
#include "theme/app_shell_styles.hpp"
#include "update/update_controller.hpp"
#include "theme/dpi_helpers.hpp"
#include "theme/theme_tokens.hpp"
#include "widgets/control_left_resize_edge.hpp"

#ifdef _WIN32
#include "pipela/native/dcomp_hud.hpp"
#endif

namespace {

std::intptr_t qtWidgetHwnd(QWidget* widget) {
    if (widget == nullptr) {
        return 0;
    }
    return static_cast<std::intptr_t>(static_cast<qintptr>(widget->winId()));
}

constexpr double kGameCenterThrottleSec = 0.72;

double nowMonoSec() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

bool stateBool(const pipela::core::state::AppState& state, const char* key, bool fallback) {
    if (auto v = state.get(key)) {
        if (const auto* b = std::get_if<bool>(&*v)) {
            return *b;
        }
    }
    return fallback;
}

}  // namespace

PipelaMainWindow::PipelaMainWindow(pipela::ui::shell::RuntimeBootstrap& runtime, QWidget* parent)
    : QMainWindow(parent), runtime_(runtime) {
    setWindowFlags(Qt::FramelessWindowHint | Qt::Window);
    setAttribute(Qt::WA_TranslucentBackground, false);
    setStyleSheet(pipela::ui::theme::controlFramelessWindowQss());
    overlay_mgr_ = std::make_unique<pipela::ui::overlays::OverlayManager>();
    overlay_controller_ = std::make_unique<pipela::ui::overlays::TemplateOverlayController>(
        this, &runtime_.state(),
        [this](const QString& capture_kind) -> std::intptr_t {
            if (capture_kind == QString::fromUtf8("start_game_launcher")) {
                launcher_hwnd_cache_ = pipela::core::win32::refreshSmartUpdaterHwndCached(
                    launcher_hwnd_cache_);
                if (!launcher_hwnd_cache_) {
                    launcher_hwnd_cache_ = pipela::core::win32::findSmartUpdaterWindow();
                }
                return launcher_hwnd_cache_;
            }
            runtime_.refreshGameHwnd();
            return runtime_.targetHwnd();
        });
    update_controller_ =
        std::make_unique<pipela::app::update::UpdateController>(nullptr, this);
    control_ = new ControlMainWindow(overlay_mgr_.get(), &runtime_.state(),
                                     overlay_controller_.get(), update_controller_.get(), this);
    overlay_controller_->setLogCallback([this](const QString& line) {
        if (control_ != nullptr) {
            control_->appendTerminalLine(line);
        }
    });
    pipela::core::workers::WorkerContext::setLoopLogCallback(
        [this](const std::string& msg) {
            if (control_ == nullptr || msg.empty()) {
                return;
            }
            const QString line = QString::fromUtf8(msg.c_str());
            QMetaObject::invokeMethod(
                control_,
                [this, line]() {
                    if (control_ != nullptr) {
                        control_->appendTerminalLine(line);
                    }
                },
                Qt::QueuedConnection);
        });
    pipela::core::featureTraceEnsureSession();
    pipela::core::featureTraceRuntimeSnapshot(runtime_.state(), "mainwindow_ready");
    if (control_ != nullptr) {
        QWidget* drag_root = control_->contentRoot();
        if (drag_root != nullptr) {
            drag_root->installEventFilter(this);
        }
    }
    setCentralWidget(control_);
    connect(control_, &ControlMainWindow::quitApplicationRequested, this,
            &PipelaMainWindow::requestApplicationQuit);
    if (update_controller_ != nullptr) {
        connect(update_controller_.get(), &pipela::app::update::UpdateController::quitForUpdate,
                this, &PipelaMainWindow::requestApplicationQuit);
        update_controller_->start();
    }
    if (QWidget* cw = centralWidget()) {
        cw->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Expanding);
    }
    setWindowTitle(QString::fromUtf8("Pipela ") +
                   QString::fromStdString(pipela::core::appVersion()));
    dock_w_log_ = pipela::app::dock::resolveUnifiedSavedDockPanelW(420);
    resize(dock_w_log_, 740);
    setFixedWidth(dock_w_log_);
    resize_edge_ = new pipela::ui::widgets::ControlLeftResizeEdge(this, this);
    resize_edge_->setGeometry(0, 0, 6, height());
    resize_edge_->raise();
    game_overlay_ = std::make_unique<pipela::ui::overlays::GameOverlayWindow>();
    title_strip_ = std::make_unique<pipela::ui::overlays::TitleStripWindow>();
    setupTitleStrip();
    flame_banner_ = std::make_unique<pipela::ui::overlays::FlameStartBanner>(&runtime_.state());
#ifdef _WIN32
    cursor_hud_ = std::make_unique<pipela::native::DCompHud>();
    input_hooks_ = std::make_unique<pipela::app::input::InputHooksBridge>(this);
    input_hooks_->bindState(&runtime_.state());
    connect(input_hooks_.get(), &pipela::app::input::InputHooksBridge::inputEventQueued,
            control_, &ControlMainWindow::appendTerminalLine);
    connect(input_hooks_.get(), &pipela::app::input::InputHooksBridge::quitRequested, qApp,
            &QApplication::quit);
    input_hooks_->setQuitCallback([]() { QApplication::quit(); });
    input_hooks_->start();
    cursor_hud_ctrl_ = std::make_unique<pipela::ui::overlays::CursorHudController>(
        cursor_hud_.get(), &runtime_.state(), this);
    input_hooks_->setCursorHudController(cursor_hud_ctrl_.get());
#endif

    dock_chrome_ = std::make_unique<pipela::ui::overlays::DockChromeController>(
        *overlay_mgr_, this);
    dock_chrome_->setAppState(&runtime_.state());
    dock_chrome_->setOverlayController(overlay_controller_.get());
    dock_chrome_->setGameHwnd(runtime_.targetHwnd());
    dock_chrome_->setDockWidthLogical(dock_w_log_);
    dock_chrome_->setKillPanelVisible(true);
    dock_chrome_->setUserDismissedChecker([this]() { return user_dismissed_control_; });
    dock_chrome_->setPrepareKillChromeShow([this]() { prepareKillChromeShow(); });
    dock_chrome_->setAfterChromeZOrderSynced([this]() {
        if (title_strip_ != nullptr && title_strip_->isVisible()) {
            title_strip_->reassertZOrder(true);
        }
    });
    dock_chrome_->setOnAnchorClientRectChanged([this]() { maybeExtendClientPhaseDockBurst(); });
    if (game_overlay_) {
        dock_chrome_->setOverlayHwnd(qtWidgetHwnd(game_overlay_.get()));
    }
    dock_chrome_->start(150);

    client_dock_burst_timer_ = new QTimer(this);
    client_dock_burst_timer_->setInterval(1000);
    connect(client_dock_burst_timer_, &QTimer::timeout, this,
            &PipelaMainWindow::onClientDockBurstTick);

    game_center_timer_ = new QTimer(this);
    game_center_timer_->setInterval(400);
    connect(game_center_timer_, &QTimer::timeout, this,
            &PipelaMainWindow::tickGameWindowScreenCenter);
    game_center_timer_->start();

    auto* dock_timer = new QTimer(this);
    connect(dock_timer, &QTimer::timeout, this, [this]() {
        runtime_.refreshGameHwnd();
        const auto hwnd = runtime_.targetHwnd();
        launcher_hwnd_cache_ = pipela::core::win32::refreshSmartUpdaterHwndCached(
            launcher_hwnd_cache_);
        if (!launcher_hwnd_cache_) {
            launcher_hwnd_cache_ = pipela::core::win32::findSmartUpdaterWindow();
        }
        const auto launcher = launcher_hwnd_cache_;
        const auto phase = pipela::ui::dock::resolveUiDockPhase(
            hwnd, launcher, [](std::intptr_t h) {
                return pipela::core::win32::isWindowMinimized(h);
            });
        const bool target_minimized =
            hwnd != 0 && pipela::core::win32::isWindow(hwnd) &&
            pipela::core::win32::isWindowMinimized(hwnd);
        const bool game_just_restored = last_target_minimized_ && !target_minimized && hwnd != 0;
        last_target_minimized_ = target_minimized;
        const bool was_dev_standby =
            pipela::ui::shell::pipelaDevUiStandbyChrome(last_dock_phase_);
        const auto prev_phase = last_dock_phase_;
        if (phase == pipela::ui::dock::UiDockPhase::Client &&
            prev_phase != pipela::ui::dock::UiDockPhase::Client) {
            const bool skip_burst = suppress_next_client_dock_burst_;
            suppress_next_client_dock_burst_ = false;
            if (!skip_burst) {
                startClientDockBurst();
            }
            if (!user_dismissed_control_) {
                ensureControlVisibleWithKillChrome();
            }
        } else if (prev_phase == pipela::ui::dock::UiDockPhase::Client &&
                   phase == pipela::ui::dock::UiDockPhase::Launcher) {
            suppress_next_client_dock_burst_ = true;
            stopClientDockBurst();
        } else if (phase == pipela::ui::dock::UiDockPhase::Launcher &&
                   prev_phase != pipela::ui::dock::UiDockPhase::Launcher &&
                   pipela::ui::shell::pipelaLauncherDebugChromeEnabled() &&
                   !user_dismissed_control_) {
            ensureControlVisibleWithKillChrome();
        } else if (phase != pipela::ui::dock::UiDockPhase::Client &&
                   prev_phase == pipela::ui::dock::UiDockPhase::Client) {
            stopClientDockBurst();
        } else if (phase != pipela::ui::dock::UiDockPhase::Client) {
            suppress_next_client_dock_burst_ = false;
            stopClientDockBurst();
        }
        last_dock_phase_ = phase;
        const bool dev_standby = pipela::ui::shell::pipelaDevUiStandbyChrome(phase);
        if (dev_standby != was_dev_standby) {
            last_standby_sig_.reset();
            if (title_strip_ != nullptr) {
                title_strip_->invalidateChromeLayout();
            }
            if (dock_chrome_ != nullptr) {
                dock_chrome_->forceResync();
            }
        }
        if (dock_chrome_) {
            dock_chrome_->setGameHwnd(hwnd);
            dock_chrome_->setLauncherHwnd(launcher);
            dock_chrome_->setUiDockPhase(phase);
        }
        if (phase == pipela::ui::dock::UiDockPhase::Client &&
            (game_just_restored || chrome_minimized_with_game_)) {
            pipela::ui::dock::DockChromeRestoreContext restore_ctx;
            restore_ctx.dock_host = this;
            restore_ctx.title_strip = title_strip_.get();
            restore_ctx.dock_chrome = dock_chrome_.get();
            if (pipela::ui::dock::restoreDockedChromeIfNeeded(
                    restore_ctx, phase, hwnd, game_just_restored, chrome_minimized_with_game_,
                    user_dismissed_control_)) {
                chrome_minimized_with_game_ = false;
                if (title_strip_ != nullptr) {
                    title_strip_->invalidateChromeLayout();
                }
            }
        }
#ifdef _WIN32
        Q_UNUSED(cursor_hud_);
#endif
        const QString phase_q = QString::fromUtf8(pipela::ui::dock::uiDockPhaseString(phase));
        if (control_ != nullptr) {
            control_->setDockPhaseText(phase_q);
            control_->setUiDockPhase(phase);
            control_->setDevStandbyChromeVisible(dev_standby);
            control_->updateResolutionChrome(hwnd, launcher, phase);
        }
        if (title_strip_ != nullptr) {
            title_strip_->setUiPhase(phase);
        }
        std::intptr_t strip_anchor = hwnd;
        if (phase == pipela::ui::dock::UiDockPhase::Launcher && launcher) {
            strip_anchor = launcher;
        }
        strip_anchor_hwnd_ = strip_anchor;
        if (dev_standby) {
            if (!user_dismissed_control_) {
                if (!isVisible()) {
                    show();
                }
                raise();
                dockToStandbyCentered(false);
            }
            syncDevStandbyTitleStrip();
            if (game_overlay_) {
                game_overlay_->hide();
            }
        } else if (strip_anchor && pipela::core::win32::isWindow(strip_anchor) &&
            phase != pipela::ui::dock::UiDockPhase::Standby) {
            const auto cr = pipela::core::win32::getClientRectScreen(strip_anchor);
            const int cl = std::get<0>(cr);
            const int ct = std::get<1>(cr);
            const int cr_r = std::get<2>(cr);
            const int cb = std::get<3>(cr);
            if (game_overlay_ && phase == pipela::ui::dock::UiDockPhase::Client && hwnd) {
                game_overlay_->syncToClientRect(hwnd, cl, ct, cr_r, cb);
            } else if (game_overlay_) {
                game_overlay_->hide();
            }
            const double scale = pipela::ui::theme::win32DpiScaleForHwnd(strip_anchor);
            const int dock_w = dock_w_log_;
            const bool launcher_debug =
                phase == pipela::ui::dock::UiDockPhase::Launcher &&
                pipela::ui::shell::pipelaLauncherDebugChromeEnabled();
            if (overlay_mgr_ &&
                (phase == pipela::ui::dock::UiDockPhase::Client || launcher_debug)) {
                overlay_mgr_->syncFromGameClient(strip_anchor, cl, ct, cr_r, cb, dock_w, scale,
                                                 true);
            }
            int kill_right = 0;
            if (overlay_mgr_ && overlay_mgr_->killFloater().visible) {
                const auto& klay = overlay_mgr_->killFloater().dock_layout;
                kill_right = klay.x_phys + klay.fw_phys;
            }
            int control_left = 0;
            if (!user_dismissed_control_ && overlay_mgr_ && overlay_mgr_->dock().visible) {
                const auto& dlay = overlay_mgr_->dock().last_layout;
                if (dlay.x_phys > 0 && dlay.x_phys < cr_r) {
                    control_left = dlay.x_phys;
                }
            }
            if (control_left == 0) {
                const std::intptr_t control_hwnd = qtWidgetHwnd(this);
                if (control_hwnd) {
                    const auto outer = pipela::core::win32::getWindowOuterRectScreen(control_hwnd);
                    const int gr_l = std::get<0>(outer);
                    const int gr_t = std::get<1>(outer);
                    const int gr_r = std::get<2>(outer);
                    const int gr_b = std::get<3>(outer);
                    if (pipela::app::dock::chromeOuterRectPlausibleForLeftDock(
                            gr_l, gr_t, gr_r, gr_b, cl, ct, cr_r, cb)) {
                        control_left = gr_l;
                    } else if (dock_w > 0 && scale > 0.0) {
                        pipela::app::dock::AnchorClientRects rects;
                        if (auto read =
                                pipela::app::dock::readAnchorClientRects(strip_anchor)) {
                            rects = *read;
                        } else {
                            const auto game_outer =
                                pipela::core::win32::getWindowOuterRectScreen(strip_anchor);
                            rects.client_left = cl;
                            rects.client_top = ct;
                            rects.client_right = cr_r;
                            rects.client_bottom = cb;
                            rects.outer_left = std::get<0>(game_outer);
                            rects.outer_top = std::get<1>(game_outer);
                            rects.outer_right = std::get<2>(game_outer);
                            rects.outer_bottom = std::get<3>(game_outer);
                        }
                        if (auto lay = pipela::app::dock::computeSideDockLayoutLeft(
                                strip_anchor, rects, dock_w, scale,
                                pipela::app::dock::DockHeightPolicy::ClientOrOuterFallback)) {
                            if (lay->x_phys > 0 && lay->x_phys < cr_r) {
                                control_left = lay->x_phys;
                            }
                        }
                    }
                }
            }
            const auto geom = pipela::ui::overlays::computeTitleStripGeometry(
                strip_anchor, phase, kill_right, control_left, dock_w, scale, launcher_debug);
            if (title_strip_ != nullptr) {
                if (geom.valid) {
                    const std::intptr_t overlay_hwnd = qtWidgetHwnd(game_overlay_.get());
                    title_strip_->setOverlayHwnd(overlay_hwnd);
                    title_strip_->syncFromGeometry(strip_anchor, geom.x_phys, geom.y_phys,
                                                   geom.w_phys, geom.h_phys);
                    title_strip_->setMainUiLeftPhys(control_left);
                    title_strip_->scheduleResolutionChrome(strip_anchor, hwnd, launcher, phase);
                } else {
                    title_strip_->hide();
                }
            }
            if (phase == pipela::ui::dock::UiDockPhase::Client && hwnd) {
                const std::intptr_t overlay_hwnd = qtWidgetHwnd(game_overlay_.get());
                if (dock_chrome_ != nullptr) {
                    dock_chrome_->setOverlayHwnd(overlay_hwnd);
                }
            }
        } else {
            if (game_overlay_) {
                game_overlay_->hide();
            }
            if (title_strip_) {
                title_strip_->hide();
            }
            last_standby_sig_.reset();
        }
        if (control_ != nullptr && overlay_mgr_) {
            control_->setDockStatusText(overlay_mgr_->statusSummary());
        }
    });
    dock_timer->start(200);
}

PipelaMainWindow::~PipelaMainWindow() {
#ifdef _WIN32
    if (input_hooks_) {
        input_hooks_->stop();
    }
    if (cursor_hud_) {
        cursor_hud_->shutdown();
    }
#endif
}

void PipelaMainWindow::requestApplicationQuit() {
    if (overlay_controller_ != nullptr) {
        overlay_controller_->closeAll();
    }
    stopClientDockBurst();
    if (game_center_timer_ != nullptr) {
        game_center_timer_->stop();
    }
    runtime_.stop();
#ifdef _WIN32
    if (input_hooks_ != nullptr) {
        input_hooks_->stop();
    }
    if (cursor_hud_ != nullptr) {
        cursor_hud_->shutdown();
    }
#endif
    if (tray_ != nullptr) {
        tray_->hide();
    }
    QApplication::quit();
}

void PipelaMainWindow::tickGameWindowScreenCenter() {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find("game_window_center_on_detect_enabled");
    bool enabled = true;
    if (it != all.end()) {
        enabled = pipela::core::registry::parseBool(it->second);
    }
    if (!enabled || stateBool(runtime_.state(), "select_mode", false)) {
        return;
    }
    runtime_.refreshGameHwnd();
    const std::intptr_t hwnd = runtime_.targetHwnd();
    if (!hwnd || !pipela::core::win32::isWindow(hwnd) ||
        pipela::core::win32::isWindowMinimized(hwnd)) {
        return;
    }
    const double now = nowMonoSec();
    if (last_centered_target_hwnd_ != hwnd) {
        last_centered_target_hwnd_ = hwnd;
    } else if (now < game_center_throttle_next_mono_) {
        return;
    }
    game_center_throttle_next_mono_ = now + kGameCenterThrottleSec;
    pipela::core::win32::centerOuterWindowOnMonitorWorkArea(hwnd);
}

void PipelaMainWindow::applyDockWidthLogical(int w_log) {
    dock_w_log_ = pipela::app::dock::clampDockPairPanelW(w_log);
    setFixedWidth(dock_w_log_);
    pipela::core::registry::saveStringValue("control_panel_w", std::to_string(dock_w_log_));
    pipela::core::registry::saveStringValue("kill_counter_panel_w", std::to_string(dock_w_log_));
    if (dock_chrome_ != nullptr) {
        dock_chrome_->setDockWidthLogical(dock_w_log_);
        dock_chrome_->forceResync();
    }
}

void PipelaMainWindow::ensureControlVisibleWithKillChrome() {
    if (user_dismissed_control_) {
        return;
    }
    if (!isHidden() && !isMinimized()) {
        return;
    }
    if (isMinimized()) {
        showNormal();
    }
    if (!isVisible()) {
        show();
    }
    raise();
    if (dock_chrome_ != nullptr) {
        dock_chrome_->forceResync();
    }
    QTimer::singleShot(0, this, [this]() {
        if (dock_chrome_ != nullptr) {
            dock_chrome_->forceResync();
        }
    });
    QTimer::singleShot(120, this, [this]() {
        if (dock_chrome_ != nullptr) {
            dock_chrome_->forceResync();
        }
    });
}

void PipelaMainWindow::prepareKillChromeShow() {
    user_dismissed_control_ = false;
    ensureControlVisibleWithKillChrome();
}

void PipelaMainWindow::dockToStandbyCentered(bool force) {
    if (user_dismissed_control_) {
        return;
    }
    QScreen* scr = QGuiApplication::primaryScreen();
    if (scr == nullptr) {
        return;
    }
    const QRect ag = scr->availableGeometry();
    int w_log = pipela::app::dock::resolveUnifiedSavedDockPanelW(dock_w_log_);
    int h_log = std::max(8, height() > 0 ? height() : 740);
    w_log = std::min(w_log, std::max(8, ag.width() - 16));
    h_log = std::min(h_log, std::max(8, ag.height() - 16));
    const int x_log = ag.left() + std::max(0, (ag.width() - w_log) / 2);
    const int y_log = ag.top() + std::max(0, (ag.height() - h_log) / 2);
    const auto sig = std::make_tuple(x_log, y_log, w_log, h_log);
    if (!force && last_standby_sig_ && *last_standby_sig_ == sig) {
        return;
    }
    last_standby_sig_ = sig;
    dock_w_log_ = w_log;
    setFixedWidth(w_log);
    setGeometry(x_log, y_log, w_log, h_log);
    if (dock_chrome_ != nullptr) {
        dock_chrome_->setDockWidthLogical(dock_w_log_);
        dock_chrome_->forceResync();
    }
}

void PipelaMainWindow::syncDevStandbyTitleStrip() {
    if (title_strip_ == nullptr || !isVisible()) {
        if (title_strip_ != nullptr) {
            title_strip_->hide();
        }
        return;
    }
    QScreen* scr = QGuiApplication::primaryScreen();
    if (scr == nullptr) {
        return;
    }
    double scale = scr->devicePixelRatio();
    if (scale <= 0.01) {
        scale = 1.0;
    }
    const QRect mg = geometry();
    int total_w = mg.width();
    if (dock_chrome_ != nullptr) {
        if (auto* kw = dock_chrome_->killWindow()) {
            if (kw->isVisible()) {
                total_w += kw->width();
            }
        }
    }
    constexpr int kBarH = 26;
    const int x_log = mg.x();
    const int y_log = mg.y() - kBarH;
    const int w_log = std::max(8, total_w);
    const int x_phys = static_cast<int>(std::lround(x_log * scale));
    const int y_phys = static_cast<int>(std::lround(y_log * scale));
    const int w_phys = static_cast<int>(std::lround(w_log * scale));
    const int h_phys = static_cast<int>(std::lround(kBarH * scale));
    const std::intptr_t anchor = qtWidgetHwnd(this);
    title_strip_->setUiPhase(pipela::ui::dock::UiDockPhase::Client);
    title_strip_->syncFromGeometry(anchor, x_phys, y_phys, w_phys, h_phys);
    title_strip_->setMainUiLeftPhys(x_phys);
}

void PipelaMainWindow::setupTitleStrip() {
    if (title_strip_ == nullptr) {
        return;
    }
    connect(title_strip_.get(), &pipela::ui::overlays::TitleStripWindow::launcherSettingsRequested,
            this, [this]() {
                if (control_ != nullptr) {
                    control_->openLauncherIntroSkipSettings();
                }
            });
    connect(title_strip_.get(),
            &pipela::ui::overlays::TitleStripWindow::launcherDebugChromeChanged, this,
            [this](bool on) {
                user_dismissed_control_ = false;
                if (dock_chrome_ != nullptr) {
                    dock_chrome_->forceResync();
                }
                if (on) {
                    ensureControlVisibleWithKillChrome();
                }
            });
    connect(title_strip_.get(), &pipela::ui::overlays::TitleStripWindow::killCounterTierRequested,
            this, []() {
                pipela::ui::panels::showKillCounterTierTableDialog(nullptr);
            });
    connect(title_strip_.get(), &pipela::ui::overlays::TitleStripWindow::anchorMovedByUser, this,
            [this]() {
                if (title_strip_ != nullptr) {
                    title_strip_->invalidateStripGeometry();
                    title_strip_->invalidateChromeLayout();
                }
                if (dock_chrome_ != nullptr) {
                    dock_chrome_->forceResync();
                }
            });
    connect(title_strip_.get(), &pipela::ui::overlays::TitleStripWindow::anchorMinimizeRequested,
            this, [this]() {
                const std::intptr_t a = titleStripAnchorHwnd();
                if (a) {
                    pipela::core::win32::windowMinimize(a);
                }
                chrome_minimized_with_game_ = true;
                hide();
            });
    connect(title_strip_.get(), &pipela::ui::overlays::TitleStripWindow::anchorMaximizeRequested,
            this, [this]() {
                const std::intptr_t a = titleStripAnchorHwnd();
                if (a) {
                    pipela::core::win32::windowMaximizeOrRestore(a);
                }
            });
    connect(title_strip_.get(), &pipela::ui::overlays::TitleStripWindow::anchorCloseRequested,
            this, [this]() {
                const std::intptr_t a = titleStripAnchorHwnd();
                if (a) {
                    pipela::core::win32::windowPostClose(a);
                }
            });
    foreground_monitor_.start([this](std::intptr_t /*fg_hwnd*/) {
        QMetaObject::invokeMethod(
            this, [this]() { reassertTitleStripZOrder(); }, Qt::QueuedConnection);
    });
}

void PipelaMainWindow::reassertTitleStripZOrder() {
    if (title_strip_ == nullptr || !title_strip_->isVisible()) {
        return;
    }
    title_strip_->reassertZOrder(true);
}

void PipelaMainWindow::changeEvent(QEvent* event) {
    if (event->type() == QEvent::ActivationChange && isActiveWindow()) {
        reassertTitleStripZOrder();
    }
    QMainWindow::changeEvent(event);
}

std::intptr_t PipelaMainWindow::titleStripAnchorHwnd() const {
    if (strip_anchor_hwnd_ && pipela::core::win32::isWindow(strip_anchor_hwnd_)) {
        return strip_anchor_hwnd_;
    }
    return runtime_.targetHwnd();
}

void PipelaMainWindow::resizeEvent(QResizeEvent* event) {
    QMainWindow::resizeEvent(event);
    if (resize_edge_ != nullptr) {
        resize_edge_->setGeometry(0, 0, 6, height());
        resize_edge_->raise();
    }
}

void PipelaMainWindow::startClientDockBurst() {
    client_dock_burst_ticks_remaining_ = 10;
    if (client_dock_burst_timer_ != nullptr) {
        client_dock_burst_timer_->start();
    }
}

void PipelaMainWindow::maybeExtendClientPhaseDockBurst() {
    if (last_dock_phase_ != pipela::ui::dock::UiDockPhase::Client) {
        return;
    }
    client_dock_burst_ticks_remaining_ =
        std::max(client_dock_burst_ticks_remaining_, 12);
    if (client_dock_burst_timer_ != nullptr) {
        client_dock_burst_timer_->start();
    }
}

void PipelaMainWindow::stopClientDockBurst() {
    client_dock_burst_ticks_remaining_ = 0;
    if (client_dock_burst_timer_ != nullptr) {
        client_dock_burst_timer_->stop();
    }
}

void PipelaMainWindow::onClientDockBurstTick() {
    if (client_dock_burst_ticks_remaining_ <= 0) {
        stopClientDockBurst();
        return;
    }
    --client_dock_burst_ticks_remaining_;
    pipela::app::shell::clientTransitionLog(
        "client_dock_burst tick remaining=" + std::to_string(client_dock_burst_ticks_remaining_));
    if (dock_chrome_) {
        dock_chrome_->forceResync();
    }
    if (client_dock_burst_ticks_remaining_ <= 0) {
        stopClientDockBurst();
    }
}

bool PipelaMainWindow::eventFilter(QObject* watched, QEvent* event) {
    QWidget* drag_root = control_ != nullptr ? control_->contentRoot() : nullptr;
    if (drag_root == nullptr || watched != drag_root) {
        return QMainWindow::eventFilter(watched, event);
    }
        if (event->type() == QEvent::MouseButtonPress) {
            auto* me = static_cast<QMouseEvent*>(event);
            if (me->button() == Qt::LeftButton && me->position().y() < 14.0) {
                frame_drag_active_ = true;
                frame_drag_offset_ = me->globalPosition().toPoint() - frameGeometry().topLeft();
                return true;
            }
        }
        if (event->type() == QEvent::MouseMove && frame_drag_active_) {
            auto* me = static_cast<QMouseEvent*>(event);
            if (me->buttons() & Qt::LeftButton) {
                move(me->globalPosition().toPoint() - frame_drag_offset_);
                return true;
            }
        }
        if (event->type() == QEvent::MouseButtonRelease && frame_drag_active_) {
            frame_drag_active_ = false;
            return true;
        }
    return QMainWindow::eventFilter(watched, event);
}

void PipelaMainWindow::setupTray() {
    if (!QSystemTrayIcon::isSystemTrayAvailable()) {
        fprintf(stderr, "[Tray] system tray unavailable\n");
        return;
    }
#ifdef _WIN32
    // AGENT: Match Python shell — stable notification-area identity on Windows 10/11.
    SetCurrentProcessExplicitAppUserModelID(L"Baegovda.Pipela");
#endif
    const QIcon app_icon = pipela::ui::shell::pipelaTrayIcon();
    tray_ = new QSystemTrayIcon(qApp);
    if (!app_icon.isNull()) {
        tray_->setIcon(app_icon);
    } else {
        fprintf(stderr, "[Tray] icon load failed — set PIPELA_DEBUG_TRAY=1 for paths\n");
    }
    tray_->setToolTip(QString::fromUtf8("Pipela"));
    tray_->showMessage(QString::fromUtf8("Pipela"),
                       QString::fromUtf8("트레이에서 실행 중입니다. (작업 표시줄 ^ 숨김 아이콘)"),
                       QSystemTrayIcon::Information, 3500);
    auto* menu = new QMenu(this);
    QObject::connect(menu, &QMenu::aboutToShow, menu, [menu]() {
        menu->setWindowFlag(Qt::WindowStaysOnTopHint, true);
        menu->raise();
        if (QWindow* wh = menu->windowHandle()) {
            wh->setFlag(Qt::WindowStaysOnTopHint, true);
            wh->raise();
        }
    });
    menu->addAction(QString::fromUtf8("제어창 표시"), this, [this]() {
        user_dismissed_control_ = false;
        show();
        raise();
        activateWindow();
        if (dock_chrome_ != nullptr) {
            dock_chrome_->forceResync();
        }
    });
    menu->addAction(QString::fromUtf8("숨기기"), this, [this]() {
        user_dismissed_control_ = true;
        hide();
    });
    menu->addSeparator();
    menu->addAction(QString::fromUtf8("종료"), this, &PipelaMainWindow::requestApplicationQuit);
    tray_->setContextMenu(menu);
    QObject::connect(tray_, &QSystemTrayIcon::activated, this, [this](QSystemTrayIcon::ActivationReason reason) {
        if (reason == QSystemTrayIcon::DoubleClick) {
            user_dismissed_control_ = false;
            show();
            raise();
            activateWindow();
            if (dock_chrome_ != nullptr) {
                dock_chrome_->forceResync();
            }
        }
    });
    tray_->setVisible(true);
    // AGENT: Shell tray host may miss the first icon paint until the event loop runs.
    QTimer::singleShot(0, tray_, [this]() {
        if (tray_ == nullptr) {
            return;
        }
        const QIcon ic = pipela::ui::shell::pipelaTrayIcon();
        if (!ic.isNull()) {
            tray_->setIcon(ic);
        }
        tray_->setVisible(true);
    });
    QObject::connect(qApp, &QApplication::aboutToQuit, this, [this]() {
        if (tray_ != nullptr) {
            tray_->hide();
        }
    });
}

int runQtApplication(int argc, char** argv) {
    QApplication* app_ptr = pipela::ui::shell::createPipelaApplication(argc, argv);
    QApplication& app = *app_ptr;
    app.setQuitOnLastWindowClosed(false);
    {
        const QIcon app_icon = pipela::ui::shell::pipelaApplicationIcon();
        if (!app_icon.isNull()) {
            app.setWindowIcon(app_icon);
        }
        int font_pt = 11;
        const auto values = pipela::core::registry::loadAllStringValues();
        const auto it = values.find("pipela_ui_font_pt");
        if (it != values.end()) {
            try {
                font_pt = std::max(8, std::min(24, std::stoi(it->second)));
            } catch (...) {
            }
        }
        QFont font = app.font();
        font.setPointSize(font_pt);
        app.setFont(font);
    }
    pipela::ui::theme::applyThemeFromResources(app);
    pipela::ui::shell::installFrameTimingProbeIfRequested();
    app.installEventFilter(new pipela::ui::shell::TaskbarHideFilter(&app));

    auto* splash = createStartupSplash(app);
    auto splash_msg = [&](const QString& text) {
        if (splash != nullptr) {
            splash->setLoadingMessage(text);
            app.processEvents();
        }
    };
    auto splash_prog = [&](double m) {
        if (splash != nullptr) {
            splash->setLoadingTarget(m);
            app.processEvents();
        }
    };

    splash_msg(QString::fromUtf8("테마 적용…"));
    splash_prog(0.12);

    splash_msg(QString::fromUtf8("게임 오버레이 초기화…"));
    splash_prog(0.32);

    splash_msg(QString::fromUtf8("커서 HUD 초기화…"));
    splash_prog(0.53);

    splash_msg(QString::fromUtf8("제어창 구성…"));
    splash_prog(0.66);

    pipela::ui::shell::RuntimeBootstrap runtime;
    runtime.start();

    PipelaMainWindow win(runtime);
    QObject::connect(&app, &QApplication::aboutToQuit, [&runtime]() { runtime.stop(); });

    splash_msg(QString::fromUtf8("트레이·백그라운드…"));
    splash_prog(0.93);
    win.setupTray();

    finishStartupSplash(app, splash, &win);
    if (pipela::ui::shell::pipelaDevUiEnabled()) {
        win.dockToStandbyCentered(true);
        win.raise();
    }
    return app.exec();
}
