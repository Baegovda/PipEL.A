#pragma once

#include <QWidget>

#include "dock/dock_ui_phase.hpp"

class QGridLayout;
class QPushButton;

namespace pipela::core::state {
class AppState;
}
namespace pipela::ui::widgets {
class CallMercCooldownButton;
class FlameTriggerGlassButton;
}

namespace pipela::ui::widgets {

// AGENT: 9-button action grid parity with pipela_qt/control_main.py btn_grid.
class ActionGridWidget : public QWidget {
    Q_OBJECT
public:
    explicit ActionGridWidget(pipela::core::state::AppState* app_state, QWidget* parent = nullptr);

    void refreshToggleStyles();
    void refreshActionCaptions();
    void syncCooldownGauges();
    void syncUniformButtonHeights();
    int uniformButtonHeightPx() const;
    int featureTopBlockHeightPx() const;
    void setUiDockPhase(pipela::ui::dock::UiDockPhase phase);

signals:
    void actionToggled(const QString& action_key, const QString& registry_key, bool checked);

protected:
    void contextMenuEvent(QContextMenuEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;

private:
    void buildGrid();
    void onActionClicked(const QString& key);
    bool registryBool(const char* key, bool fallback) const;
    bool stateBool(const char* key, bool fallback) const;
    void setStateBool(const char* key, bool value);
    QString styleForAction(const QString& key) const;
    QString flameActionCaption() const;
    QString reloadActionCaption() const;
    QString hpRefillActionCaption() const;
    QString mercActionCaption() const;
    QString kcActionCaption() const;
    bool isStartGameTemplate1Effective() const;
    void latchStartGameActiveLeavingLauncher();
    QPushButton* buttonForKey(const char* key) const;
    static QString formatReloadHms(double elapsed_sec);

    pipela::core::state::AppState* app_state_{nullptr};
    QGridLayout* grid_{nullptr};
    QPushButton* buttons_[10]{};
    FlameTriggerGlassButton* flame_btn_{nullptr};
    CallMercCooldownButton* reload_btn_{nullptr};
    CallMercCooldownButton* merc_btn_{nullptr};
    QPushButton* start_game_btn_{nullptr};
    pipela::ui::dock::UiDockPhase dock_phase_{pipela::ui::dock::UiDockPhase::Standby};
};

}  // namespace pipela::ui::widgets
