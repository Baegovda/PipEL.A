#pragma once

#include <QWidget>

#include <cstdint>

#include "dock/dock_ui_phase.hpp"

namespace pipela::core::state {
class AppState;
}
namespace pipela::ui::widgets {
class TerminalLogWidget;
class ActionGridWidget;
}
namespace pipela::ui::panels {
class SettingsHubWidget;
}
namespace pipela::ui::overlays {
class OverlayManager;
class TemplateOverlayController;
}
namespace pipela::app::update {
class UpdateController;
}

class QLabel;
class QSplitter;
class QTabWidget;
class QTimer;
class QPushButton;
class QEvent;
class QResizeEvent;

class ControlMainWindow : public QWidget {
    Q_OBJECT
public:
    explicit ControlMainWindow(pipela::ui::overlays::OverlayManager* overlay_mgr,
                               pipela::core::state::AppState* app_state,
                               pipela::ui::overlays::TemplateOverlayController* overlay_controller,
                               pipela::app::update::UpdateController* update_controller,
                               QWidget* parent = nullptr);

    QWidget* contentRoot() const { return content_root_; }

    void setDockStatusText(const QString& text);
    void setDockPhaseText(const QString& phase);
    void setDevStandbyChromeVisible(bool visible);
    void updateResolutionChrome(std::intptr_t game_hwnd, std::intptr_t launcher_hwnd,
                                pipela::ui::dock::UiDockPhase phase);
    pipela::ui::widgets::TerminalLogWidget* terminalLog() const { return term_log_; }

    void openLauncherIntroSkipSettings();

public slots:
    void appendTerminalLine(const QString& line);
    void syncConsoleTimeDisplayChrome();
    void applyConsoleLogRetentionNow();
    void applyGlobalFontPt(int pt);
    void refreshActionGridStyles();
    void syncTerminalSettingsTabChrome();
    void syncFeatureSplitterGeometry();
    void setUiDockPhase(pipela::ui::dock::UiDockPhase phase);

signals:
    void quitApplicationRequested();

protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;

private slots:
    void onFeatureToggled(const QString& registry_key, bool checked);
    void onMainTabChanged(int index);
    void onRetentionTick();

private:
    void syncRuntimeState(const QString& registry_key, bool checked);
    void pruneTerminalByRetention();
    double consoleLogRetentionSec() const;
    int consoleLogMaxStoredLines() const;
    void capTerminalLineBuffers();
    void rebuildTerminalFromMemory();
    void openSettingsPanel(const char* panel_id, bool toggle_same_panel_to_terminal = false);
    void pollWorkerTerminalEvents();
    double nowMonoSec() const;

    pipela::ui::overlays::OverlayManager* overlay_mgr_{nullptr};
    pipela::core::state::AppState* app_state_{nullptr};
    QWidget* content_root_{nullptr};
    QLabel* standby_hint_{nullptr};
    pipela::ui::widgets::TerminalLogWidget* term_log_{nullptr};
    pipela::ui::widgets::ActionGridWidget* action_grid_{nullptr};
    pipela::ui::panels::SettingsHubWidget* settings_hub_{nullptr};
    QWidget* feature_top_dock_{nullptr};
    QWidget* actions_tabs_sep_{nullptr};
    QSplitter* main_splitter_{nullptr};
    QTabWidget* main_tabs_{nullptr};
    QTimer* rel_timer_{nullptr};

    pipela::app::update::UpdateController* update_controller_{nullptr};
    QPushButton* update_btn_{nullptr};

    int last_reload_success_count_{0};
    int last_flame_press_count_{0};
    int last_hp_refill_total_{0};

    struct LogLine {
        double wall_t{0.0};
        double mono_t{0.0};
        QString text;
    };
    QVector<LogLine> log_memory_;
    bool terminal_view_hidden_{false};
};
