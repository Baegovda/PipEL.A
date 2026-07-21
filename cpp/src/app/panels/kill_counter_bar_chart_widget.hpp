#pragma once

#include <chrono>
#include <vector>

#include <QWidget>

class QButtonGroup;
class QPushButton;
class QTimer;

#include "pipela/core/kill_counter/stats_store.hpp"

namespace pipela::ui::panels {

class KillCounterBarChartWidget : public QWidget {
    Q_OBJECT
public:
    explicit KillCounterBarChartWidget(QWidget* parent = nullptr);

    void refresh();

    const std::vector<int>& bucketsForPaint() const;
    int bucketMinutes() const;
    int hoverIndex() const;
    void setHoverIndex(int idx);
    int panOffset() const;
    void setPanOffset(int offset);
    double xScale() const;
    void setXScale(double scale);
    int visibleBarCount(int n_total) const;
    void setUserPanned(bool panned);
    void touchUserPan();
    bool userPanned() const;
    void followTailIfNeeded();
    QString hoverTooltipText(int bucket_index) const;
    int barDelta(int bucket_index) const;
    bool bucketReloadMark(int bucket_index) const;

protected:
    QWidget* chart_host_{nullptr};
    QWidget* range_indicator_{nullptr};
    QButtonGroup* bucket_group_{nullptr};
    QTimer* pan_idle_timer_{nullptr};
    std::vector<pipela::core::kill_counter::TodayBucketEntry> bucket_entries_;
    int bucket_minutes_{30};
    int hover_index_{-1};
    int pan_offset_{0};
    double x_scale_{1.0};
    bool user_panned_{false};
    std::chrono::steady_clock::time_point last_user_pan_mono_{};
};

}  // namespace pipela::ui::panels
