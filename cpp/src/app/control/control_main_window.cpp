#include "control_main_window.hpp"

#include <chrono>
#include <algorithm>

#include <QApplication>
#include <QDoubleSpinBox>
#include <QEvent>
#include <QFileInfo>
#include <QFont>
#include <QIcon>
#include <QResizeEvent>
#include <QSplitter>
#include <QMenu>
#include <QPushButton>
#include <QHBoxLayout>
#include <QLabel>
#include <QScrollArea>
#include <QSizePolicy>
#include <QTabBar>
#include <QTabWidget>
#include <QTimer>
#include <QVBoxLayout>

#include "overlays/overlay_manager.hpp"
#include "panels/settings_hub.hpp"
#include "panels/settings/panel_context.hpp"
#include "pipela/core/console_log_retention.hpp"
#include "pipela/core/feature_trace_log.hpp"
#include "pipela/core/paths.hpp"
#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/version.hpp"
#include "theme/control_tab_chrome.hpp"
#include "theme/resolution_chrome.hpp"
#include "theme/ui_adaptive.hpp"
#include "theme/qt_typography_refresh.hpp"
#include "shell/dev_ui_mode.hpp"
#include "widgets/action_grid_widget.hpp"
#include "widgets/paired_control_tab_bar.hpp"
#include "widgets/paired_control_tab_widget.hpp"
#include "widgets/terminal_log_widget.hpp"
#include "update/update_controller.hpp"
#include "widgets/card_popup_shell.hpp"

namespace {

double nowWallSec() {
    using clock = std::chrono::system_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

double nowMonoSec() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

int registryInt(const char* key, int fallback) {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(key);
    if (it == all.end()) {
        return fallback;
    }
    try {
        return std::stoi(it->second);
    } catch (...) {
        return fallback;
    }
}

const char* panelIdForFeatureKey(const QString& registry_key) {
    static const std::pair<const char*, const char*> kMap[] = {
        {"ride_feature_enabled", "ride"},
        {"hp_refill_feature_enabled", "hp_refill"},
        {"reload_active", "reload"},
        {"ammo_restock_active", "ammo_restock"},
        {"call_merc_active", "call_merc"},
        {"flame_trigger_feature_enabled", "flame_trigger"},
        {"left_click_feature_enabled", "left_click"},
        {"start_game_launcher_active", "start_game"},
    };
    const std::string key = registry_key.toStdString();
    for (const auto& row : kMap) {
        if (key == row.first) {
            return row.second;
        }
    }
    return nullptr;
}

QString assetIconPath(const char* filename) {
    const QString path =
        QString::fromStdString(pipela::core::assetsDir()) + QLatin1Char('/') +
        QString::fromUtf8(filename);
    if (QFileInfo::exists(path)) {
        return QFileInfo(path).absoluteFilePath();
    }
    return {};
}

}  // namespace

ControlMainWindow::ControlMainWindow(pipela::ui::overlays::OverlayManager* overlay_mgr,
                                     pipela::core::state::AppState* app_state,
                                     pipela::ui::overlays::TemplateOverlayController* overlay_controller,
                                     pipela::app::update::UpdateController* update_controller,
                                     QWidget* parent)
    : QWidget(parent), overlay_mgr_(overlay_mgr), app_state_(app_state),
      update_controller_(update_controller) {
    setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Expanding);
    auto* shell = new QVBoxLayout(this);
    shell->setContentsMargins(0, 0, 0, 0);
    shell->setSpacing(0);

    content_root_ = new QWidget(this);
    content_root_->setObjectName(QString::fromUtf8("pipelaControlRoot"));
    content_root_->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Expanding);
    shell->addWidget(content_root_, 1);

    const int pad = pipela::ui::theme::scalePxH(12, width() > 0 ? width() : 420);
    auto* layout = new QVBoxLayout(content_root_);
    layout->setContentsMargins(pad, pad, pad, pad);
    layout->setSpacing(pipela::ui::theme::scalePxV(8, 740));

    standby_hint_ = new QLabel(QString::fromUtf8("게임 미연결 — dev UI"), content_root_);
    standby_hint_->setAlignment(Qt::AlignHCenter | Qt::AlignVCenter);
    standby_hint_->setStyleSheet(
        "color: #8ec8ff; font-size: 12px; font-weight: 600; background: transparent;");
    standby_hint_->hide();
    layout->addWidget(standby_hint_);

    action_grid_ = new pipela::ui::widgets::ActionGridWidget(app_state_, content_root_);
    connect(action_grid_, &pipela::ui::widgets::ActionGridWidget::actionToggled, this,
            [this](const QString& key, const QString& registry_key, bool checked) {
                if (key.startsWith(QString::fromUtf8("__open__:"))) {
                    openSettingsPanel(key.mid(9).toUtf8().constData(), true);
                    return;
                }
                if (!registry_key.isEmpty()) {
                    onFeatureToggled(registry_key, checked);
                } else {
                    appendTerminalLine(QString::fromUtf8("[%1] 토글").arg(key));
                }
            });

    feature_top_dock_ = new QWidget(content_root_);
    feature_top_dock_->setObjectName(QString::fromUtf8("pipelaFeatureDock"));
    auto* feature_lay = new QVBoxLayout(feature_top_dock_);
    feature_lay->setContentsMargins(0, 0, 0, 0);
    feature_lay->setSpacing(pipela::ui::theme::scalePxV(8, 740));
    feature_lay->addWidget(action_grid_, 0);

    auto* sep_wrap = new QWidget(feature_top_dock_);
    sep_wrap->setObjectName(QString::fromUtf8("pipelaActionsTabsSep"));
    actions_tabs_sep_ = sep_wrap;
    auto* sep_lay = new QVBoxLayout(sep_wrap);
    sep_lay->setContentsMargins(0, pipela::ui::theme::scalePxV(10, 740), 0,
                                pipela::ui::theme::scalePxV(14, 740));
    auto* sep_line = new QFrame(sep_wrap);
    sep_line->setFrameShape(QFrame::HLine);
    sep_line->setFixedHeight(1);
    sep_line->setStyleSheet("background: #2a3438; border: none;");
    sep_lay->addWidget(sep_line);
    feature_lay->addWidget(sep_wrap, 0);

    main_splitter_ = new QSplitter(Qt::Vertical, content_root_);
    main_splitter_->setObjectName(QString::fromUtf8("pipelaMainSplitter"));
    main_splitter_->setChildrenCollapsible(false);
    main_splitter_->addWidget(feature_top_dock_);

    main_tabs_ = new pipela::ui::widgets::PairedControlTabWidget(content_root_);
    main_tabs_->setObjectName(QString::fromUtf8("pipelaMainTabs"));
    main_tabs_->setDocumentMode(true);
    main_tabs_->tabBar()->setStyle(nullptr);
    main_tabs_->setUsesScrollButtons(false);

    auto* term_tab = new QWidget(main_tabs_);
    term_tab->setObjectName(QString::fromUtf8("pipelaTabArea"));
    auto* term_layout = new QVBoxLayout(term_tab);
    term_log_ = new pipela::ui::widgets::TerminalLogWidget(term_tab);
    term_layout->addWidget(term_log_);
    const QString term_icon = assetIconPath("terminal.png");
    if (!term_icon.isEmpty()) {
        main_tabs_->addTab(term_tab, QIcon(term_icon), QString::fromUtf8("터미널"));
    } else {
        main_tabs_->addTab(term_tab, QString::fromUtf8("터미널"));
    }

    pipela::app::panels::settings::SettingsPanelContext panel_ctx;
    panel_ctx.state = app_state_;
    panel_ctx.overlays = overlay_controller;
    panel_ctx.update = update_controller_;
    panel_ctx.log = [this](const QString& line) { appendTerminalLine(line); };
    panel_ctx.sync_console_time = [this]() { syncConsoleTimeDisplayChrome(); };
    panel_ctx.apply_console_retention = [this]() { applyConsoleLogRetentionNow(); };
    panel_ctx.apply_font_pt = [this](int pt) { applyGlobalFontPt(pt); };
    settings_hub_ = new pipela::ui::panels::SettingsHubWidget(panel_ctx, main_tabs_);
    const QString set_icon = assetIconPath("gear.png");
    if (!set_icon.isEmpty()) {
        main_tabs_->addTab(settings_hub_, QIcon(set_icon), QString::fromUtf8("설정"));
    } else {
        main_tabs_->addTab(settings_hub_, QString::fromUtf8("설정"));
    }
    if (auto* bar = qobject_cast<pipela::ui::widgets::PairedControlTabBar*>(main_tabs_->tabBar())) {
        connect(bar, &pipela::ui::widgets::PairedControlTabBar::terminalGearClicked, this,
                [this]() { openSettingsPanel("console"); });
    }
    layout->addWidget(main_splitter_, 1);
    main_splitter_->addWidget(main_tabs_);
    if (term_log_ != nullptr) {
        term_log_->setMaxVisibleLines(consoleLogMaxStoredLines());
    }

    auto* bottom_row = new QHBoxLayout();
    bottom_row->setContentsMargins(0, pipela::ui::theme::scalePxV(6, 740), 0, 0);
    bottom_row->setSpacing(pipela::ui::theme::scalePxH(8, 420));

    update_btn_ = new QPushButton(QString::fromUtf8("업데이트"), content_root_);
    update_btn_->setObjectName(QString::fromUtf8("pipelaUpdateBtn"));
    update_btn_->setCursor(Qt::PointingHandCursor);
    update_btn_->setFixedHeight(pipela::ui::theme::scalePxV(26, 740));
    update_btn_->setToolTip(QString::fromUtf8("업데이트 확인 · 설치"));
    connect(update_btn_, &QPushButton::clicked, this, [this]() {
        if (update_controller_ == nullptr) {
            return;
        }
        if (update_controller_->updateAvailable()) {
            update_controller_->installPendingUpdate();
        } else {
            update_controller_->checkNow(pipela::app::update::UpdateCheckMode::UserPrompt);
        }
    });

    auto* quit_btn = new QPushButton(QString::fromUtf8("종료"), content_root_);
    quit_btn->setObjectName(QString::fromUtf8("pipelaQuitBtn"));
    quit_btn->setCursor(Qt::PointingHandCursor);
    quit_btn->setFixedHeight(pipela::ui::theme::scalePxV(26, 740));
    quit_btn->setToolTip(QString::fromUtf8("Pipela 완전 종료"));
    connect(quit_btn, &QPushButton::clicked, this, &ControlMainWindow::quitApplicationRequested);
    bottom_row->addStretch(1);
    bottom_row->addWidget(update_btn_, 0, Qt::AlignHCenter);
    bottom_row->addWidget(quit_btn, 0, Qt::AlignHCenter);
    bottom_row->addStretch(1);
    layout->addLayout(bottom_row);

    if (update_controller_ != nullptr) {
        connect(update_controller_, &pipela::app::update::UpdateController::statusMessage, this,
                &ControlMainWindow::appendTerminalLine);
        connect(update_controller_,
                &pipela::app::update::UpdateController::updateAvailabilityChanged, this,
                [this](bool available, const QString& ver) {
                    if (update_btn_ == nullptr) {
                        return;
                    }
                    update_btn_->setText(available
                                             ? QString::fromUtf8("업데이트 (%1)").arg(ver)
                                             : QString::fromUtf8("업데이트"));
                });
        connect(update_controller_, &pipela::app::update::UpdateController::installFailed, this,
                [this](const QString& reason) {
                    pipela::ui::widgets::messageCardDialog(
                        this, QString::fromUtf8("업데이트 실패"), reason,
                        QString::fromUtf8("danger"));
                });
    }

    QTimer::singleShot(0, this, &ControlMainWindow::syncFeatureSplitterGeometry);

    connect(main_tabs_, &QTabWidget::currentChanged, this, &ControlMainWindow::onMainTabChanged);

    rel_timer_ = new QTimer(this);
    rel_timer_->setInterval(1000);
    connect(rel_timer_, &QTimer::timeout, this, [this]() {
        onRetentionTick();
        if (term_log_ != nullptr) {
            term_log_->refreshTimePrefixes();
        }
        if (action_grid_ != nullptr) {
            action_grid_->refreshActionCaptions();
            action_grid_->syncCooldownGauges();
        }
        refreshActionGridStyles();
        syncFeatureSplitterGeometry();
        pollWorkerTerminalEvents();
    });
    rel_timer_->start();

    if (overlay_mgr_ != nullptr) {
        overlay_mgr_->syncFromGameClient(0, 0, 0, 1920, 1080, 420, 1.0, true);
    }
    setDevStandbyChromeVisible(pipela::ui::shell::pipelaDevUiEnabled());
    syncTerminalSettingsTabChrome();
    if (auto* app = qApp) {
        app->installEventFilter(this);
    }
    appendTerminalLine(QString::fromUtf8("[Pipela] 준비 완료"));
    pipela::core::featureTraceEnsureSession();
    appendTerminalLine(QString::fromUtf8("[Trace] feature_trace (deep) → %1")
                           .arg(QString::fromStdString(pipela::core::featureTraceLogPath())));
    syncFeatureSplitterGeometry();
}

void ControlMainWindow::pollWorkerTerminalEvents() {
    if (app_state_ == nullptr) {
        return;
    }
    auto read_int = [this](const char* key, int fallback) {
        if (auto v = app_state_->get(key)) {
            if (const auto* n = std::get_if<int>(&*v)) {
                return *n;
            }
        }
        return fallback;
    };
    const int reload_cnt = read_int("reload_success_count", 0);
    if (reload_cnt > last_reload_success_count_) {
        appendTerminalLine(QString::fromUtf8("[Reload] 성공 (%1)").arg(reload_cnt));
        last_reload_success_count_ = reload_cnt;
    }
    const int ft_cnt = read_int("flame_trigger_press_count", 0);
    if (ft_cnt > last_flame_press_count_) {
        appendTerminalLine(QString::fromUtf8("[Flame Trigger] 발동 (%1)").arg(ft_cnt));
        last_flame_press_count_ = ft_cnt;
    }
    const int hp_cnt = read_int("hp_refill_trigger_total", 0);
    if (hp_cnt > last_hp_refill_total_) {
        appendTerminalLine(QString::fromUtf8("[HP Refill] 트리거 (%1)").arg(hp_cnt));
        last_hp_refill_total_ = hp_cnt;
    }
}

void ControlMainWindow::resizeEvent(QResizeEvent* event) {
    QWidget::resizeEvent(event);
    syncFeatureSplitterGeometry();
}

void ControlMainWindow::syncFeatureSplitterGeometry() {
    if (action_grid_ == nullptr || main_splitter_ == nullptr || feature_top_dock_ == nullptr) {
        return;
    }
    action_grid_->syncUniformButtonHeights();
    const int total_top = action_grid_->featureTopBlockHeightPx() +
                          (actions_tabs_sep_ != nullptr ? actions_tabs_sep_->sizeHint().height() : 0) +
                          pipela::ui::theme::scalePxV(8, height() > 0 ? height() : 740);
    feature_top_dock_->setFixedHeight(total_top);
    const int H = main_splitter_->height();
    if (H > 0) {
        const int hw = main_splitter_->handleWidth();
        const int rest = std::max(pipela::ui::theme::scalePxV(120, H), H - total_top - hw);
        main_splitter_->setSizes({total_top, rest});
    }
}

void ControlMainWindow::setUiDockPhase(pipela::ui::dock::UiDockPhase phase) {
    if (action_grid_ != nullptr) {
        action_grid_->setUiDockPhase(phase);
    }
    syncFeatureSplitterGeometry();
}

void ControlMainWindow::onRetentionTick() {
    const int before = static_cast<int>(log_memory_.size());
    pruneTerminalByRetention();
    capTerminalLineBuffers();
    if (term_log_ != nullptr && static_cast<int>(log_memory_.size()) != before) {
        rebuildTerminalFromMemory();
    }
}

void ControlMainWindow::syncTerminalSettingsTabChrome() {
    if (main_tabs_ == nullptr) {
        return;
    }
    const int w = width() > 0 ? width() : 420;
    const int h = height() > 0 ? height() : 740;
    main_tabs_->setStyleSheet(pipela::ui::theme::mainTabsAreaQss(w, h));
    if (auto* bar = main_tabs_->tabBar()) {
        QFont f = bar->font();
        f.setPointSizeF(pipela::ui::theme::mainTabsLabelFontPointSize(w));
        f.setWeight(QFont::DemiBold);
        bar->setFont(f);
        const int icon_side = pipela::ui::theme::mainTabsBarIconSizePx(w, h);
        bar->setIconSize(QSize(icon_side, icon_side));
        bar->updateGeometry();
    }
    if (term_log_ != nullptr) {
        const int margin = pipela::ui::theme::scalePxH(4, w);
        term_log_->setContentsMargins(margin, margin, margin, margin);
    }
    if (settings_hub_ != nullptr) {
        settings_hub_->flushSettingsLayout();
    }
}

bool ControlMainWindow::eventFilter(QObject* watched, QEvent* event) {
    if (event->type() == QEvent::MouseButtonPress && main_tabs_ != nullptr &&
        main_tabs_->currentIndex() == 1 && settings_hub_ != nullptr) {
        auto* me = static_cast<QMouseEvent*>(event);
        if (me->button() == Qt::BackButton || me->button() == Qt::ForwardButton) {
            if (settings_hub_->handleMouseNavigation(me->button())) {
                return true;
            }
        }
    }
    return QWidget::eventFilter(watched, event);
}

double ControlMainWindow::nowMonoSec() const {
    return ::nowMonoSec();
}

void ControlMainWindow::refreshActionGridStyles() {
    if (action_grid_ != nullptr) {
        action_grid_->refreshToggleStyles();
    }
}

void ControlMainWindow::setDockStatusText(const QString& text) {
    (void)text;
    // AGENT: Dock/client summary lives on title strip only — not duplicated in control footer.
}

void ControlMainWindow::setDockPhaseText(const QString& phase) {
    (void)phase;
}

void ControlMainWindow::setDevStandbyChromeVisible(bool visible) {
    if (standby_hint_ != nullptr) {
        standby_hint_->setVisible(visible);
    }
}

void ControlMainWindow::openLauncherIntroSkipSettings() {
    if (QWidget* top = window()) {
        top->show();
        top->raise();
        top->activateWindow();
    }
    if (main_tabs_ != nullptr) {
        main_tabs_->setCurrentIndex(1);
    }
    openSettingsPanel("start_game", false);
}

void ControlMainWindow::updateResolutionChrome(std::intptr_t game_hwnd,
                                               std::intptr_t launcher_hwnd,
                                               pipela::ui::dock::UiDockPhase phase) {
    (void)game_hwnd;
    (void)launcher_hwnd;
    (void)phase;
}

double ControlMainWindow::consoleLogRetentionSec() const {
    const int minutes = registryInt("console_log_retention_minutes", 30);
    const int seconds = registryInt("console_log_retention_seconds", 0);
    return static_cast<double>(minutes) * 60.0 + static_cast<double>(seconds);
}

int ControlMainWindow::consoleLogMaxStoredLines() const {
    return pipela::core::clampConsoleLogMaxLines(
        registryInt("console_log_max_lines", pipela::core::kConsoleLogMaxLinesDefault));
}

void ControlMainWindow::capTerminalLineBuffers() {
    const int cap = consoleLogMaxStoredLines();
    if (term_log_ != nullptr) {
        term_log_->setMaxVisibleLines(cap);
    }
    while (static_cast<int>(log_memory_.size()) > cap) {
        log_memory_.removeFirst();
    }
}

void ControlMainWindow::pruneTerminalByRetention() {
    if (log_memory_.isEmpty()) {
        return;
    }
    const double now = nowWallSec();
    const double retain = consoleLogRetentionSec();
    if (retain <= 0.0) {
        return;
    }
    const double cutoff = now - retain;
    QVector<LogLine> kept;
    kept.reserve(log_memory_.size());
    for (const auto& line : log_memory_) {
        if (line.wall_t >= cutoff) {
            kept.push_back(line);
        }
    }
    log_memory_ = std::move(kept);
}

void ControlMainWindow::rebuildTerminalFromMemory() {
    if (term_log_ == nullptr) {
        return;
    }
    QVector<pipela::ui::widgets::TerminalLogDisplayEntry> entries;
    entries.reserve(log_memory_.size());
    for (const auto& line : log_memory_) {
        pipela::ui::widgets::TerminalLogDisplayEntry e;
        e.wall_t = line.wall_t;
        e.mono_t = line.mono_t;
        e.body = line.text;
        entries.push_back(e);
    }
    term_log_->setLines(entries, !terminal_view_hidden_);
}

void ControlMainWindow::appendTerminalLine(const QString& line) {
    const double wall_t = nowWallSec();
    const double mono = nowMonoSec();
    log_memory_.push_back(LogLine{wall_t, mono, line});
    capTerminalLineBuffers();
    pruneTerminalByRetention();
    if (term_log_ != nullptr && !terminal_view_hidden_) {
        term_log_->appendLine(line, wall_t, mono);
    }
}

void ControlMainWindow::onMainTabChanged(int index) {
    if (index == 0) {
        terminal_view_hidden_ = false;
        rebuildTerminalFromMemory();
        syncTerminalSettingsTabChrome();
        return;
    }
    terminal_view_hidden_ = true;
    syncTerminalSettingsTabChrome();
}

void ControlMainWindow::syncConsoleTimeDisplayChrome() {
    rebuildTerminalFromMemory();
}

void ControlMainWindow::applyConsoleLogRetentionNow() {
    pruneTerminalByRetention();
    capTerminalLineBuffers();
    rebuildTerminalFromMemory();
}

void ControlMainWindow::applyGlobalFontPt(int pt) {
    const int clamped = std::max(8, std::min(24, pt));
    if (auto* app = qApp) {
        pipela::ui::theme::refreshPipelaTypography(app, this, clamped);
    }
    syncTerminalSettingsTabChrome();
    if (action_grid_ != nullptr) {
        action_grid_->syncUniformButtonHeights();
    }
    syncFeatureSplitterGeometry();
}

void ControlMainWindow::openSettingsPanel(const char* panel_id, bool toggle_same_panel_to_terminal) {
    if (panel_id == nullptr) {
        return;
    }
    if (toggle_same_panel_to_terminal && main_tabs_ != nullptr && main_tabs_->currentIndex() == 1 &&
        settings_hub_ != nullptr && settings_hub_->currentPanelId() == panel_id) {
        main_tabs_->setCurrentIndex(0);
        return;
    }
    if (main_tabs_ != nullptr) {
        main_tabs_->setCurrentIndex(1);
    }
    if (settings_hub_ != nullptr) {
        settings_hub_->openPanelById(panel_id);
    }
    if (QWidget* top = window()) {
        top->raise();
        top->activateWindow();
    }
}

void ControlMainWindow::onFeatureToggled(const QString& registry_key, bool checked) {
    syncRuntimeState(registry_key, checked);
    static const std::pair<const char*, const char*> kLabels[] = {
        {"left_click_feature_enabled", "LeftClick"},
        {"right_hold_feature_enabled", "RightHold"},
        {"flame_trigger_feature_enabled", "Flame Trigger"},
        {"reload_active", "Reload"},
        {"ride_feature_enabled", "Ride"},
        {"hp_refill_feature_enabled", "HP Refill"},
        {"ammo_restock_active", "Ammo Restock"},
        {"call_merc_active", "Call Merc"},
        {"kill_counter_enabled", "Kill Counter"},
        {"start_game_launcher_active", "Start Game"},
    };
    QString label = registry_key;
    const std::string key = registry_key.toStdString();
    for (const auto& row : kLabels) {
        if (key == row.first) {
            label = QString::fromUtf8(row.second);
            break;
        }
    }
    appendTerminalLine(QString::fromUtf8("[설정] %1 %2")
                           .arg(label)
                           .arg(checked ? QString::fromUtf8("켜짐") : QString::fromUtf8("꺼짐")));
    if (registry_key == QString::fromUtf8("start_game_launcher_active") && checked) {
        appendTerminalLine(
            QString::fromUtf8("[Start Game] 자동화 대기 · ① Launcher → ② Intro skip → ③ Accept"));
    }
}

void ControlMainWindow::syncRuntimeState(const QString& registry_key, bool checked) {
    if (app_state_ == nullptr) {
        return;
    }
    static const char* kStateKeys[] = {
        "reload_active",
        "ammo_restock_active",
        "left_click_feature_enabled",
        "kill_counter_enabled",
        "ride_feature_enabled",
        "hp_refill_feature_enabled",
        "flame_trigger_feature_enabled",
        "right_hold_feature_enabled",
        "call_merc_active",
        "start_game_launcher_active",
    };
    const std::string key = registry_key.toStdString();
    for (const char* state_key : kStateKeys) {
        if (key == state_key) {
            app_state_->set(state_key, pipela::core::state::StateValue{checked});
            return;
        }
    }
}
