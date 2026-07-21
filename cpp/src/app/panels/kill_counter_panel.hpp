#pragma once

#include <QWidget>

class QLabel;
class QHBoxLayout;
class QProgressBar;
class QPushButton;
class QTimer;

namespace pipela::core::state {
class AppState;
}
namespace pipela::ui::overlays {
class TemplateOverlayController;
}

namespace pipela::ui::panels {

class KillCounterBarChartWidget;
class KillCounterDailyCalendarWidget;

// AGENT: KC floater body — hero, recent, goal, lap, graph, calendar, ROI toolbar.
class KillCounterPanel : public QWidget {
    Q_OBJECT
public:
    explicit KillCounterPanel(QWidget* parent = nullptr);

    void setAppState(pipela::core::state::AppState* state);
    void setOverlayController(pipela::ui::overlays::TemplateOverlayController* controller);

protected:
    void resizeEvent(QResizeEvent* event) override;
    bool eventFilter(QObject* watched, QEvent* event) override;

private:
    void buildUi();
    void applySectionHeights();
    void scheduleViewportLayoutRefresh();
    void refreshViewportLayout();
    void startTimers();
    void tickFast();
    void tickSlow();
    double lapStartTs() const;
    void setLapStartTs(double ts);
    void clearLap();

    pipela::core::state::AppState* state_{nullptr};
    pipela::ui::overlays::TemplateOverlayController* overlay_controller_{nullptr};

    QWidget* sec_hero_{nullptr};
    QWidget* sec_goal_{nullptr};
    QWidget* sec_graph_{nullptr};
    QWidget* sec_calendar_{nullptr};
    QWidget* sec_lap_{nullptr};
    QWidget* sec_bottom_{nullptr};
    QHBoxLayout* bottom_bar_{nullptr};

    QLabel* hero_caption_{nullptr};
    QLabel* hero_label_{nullptr};
    QLabel* recent_1h_{nullptr};
    QLabel* recent_6h_{nullptr};
    QLabel* recent_24h_{nullptr};
    QLabel* recent_kph_{nullptr};
    QLabel* goal_tier_line_{nullptr};
    QLabel* goal_tier_rem_{nullptr};
    QLabel* goal_choin_line_{nullptr};
    QLabel* goal_choin_rem_{nullptr};
    QProgressBar* goal_tier_bar_{nullptr};
    QProgressBar* goal_choin_bar_{nullptr};
    QLabel* lap_1h_{nullptr};
    QLabel* lap_6h_{nullptr};
    QLabel* lap_24h_{nullptr};
    QLabel* lap_total_{nullptr};
    QLabel* lap_elapsed_{nullptr};
    QPushButton* lap_main_btn_{nullptr};
    QPushButton* lap_clear_btn_{nullptr};
    QPushButton* lap_end_btn_{nullptr};
    QPushButton* session_reset_btn_{nullptr};
    QPushButton* stats_reset_btn_{nullptr};
    KillCounterBarChartWidget* bar_chart_{nullptr};
    KillCounterDailyCalendarWidget* calendar_{nullptr};

    QTimer* fast_timer_{nullptr};
    QTimer* slow_timer_{nullptr};
    void refreshViewportTypography();
    QString kcSpt(double design_pt) const;

    int kc_vw_{440};
    int kc_vh_{740};
    int last_section_layout_h_{0};
    double last_typography_vs_{0.0};
    bool layout_refresh_pending_{false};
    bool toolbar_attached_{false};
    bool lap_paused_{false};
    int last_recent_k1_{-1};
};

}  // namespace pipela::ui::panels
