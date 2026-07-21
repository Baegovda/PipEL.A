#include "panels/kill_counter_daily_calendar_widget.hpp"

#include <QCalendarWidget>
#include <QDate>
#include <QMap>
#include <QSizePolicy>
#include <QTextCharFormat>
#include <QVBoxLayout>

#include "pipela/core/kill_counter/stats_store.hpp"

namespace pipela::ui::panels {

KillCounterDailyCalendarWidget::KillCounterDailyCalendarWidget(QWidget* parent) : QWidget(parent) {
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    calendar_ = new QCalendarWidget(this);
    calendar_->setGridVisible(true);
    calendar_->setVerticalHeaderFormat(QCalendarWidget::NoVerticalHeader);
    calendar_->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    calendar_->setStyleSheet(
        "QCalendarWidget QWidget { alternate-background-color: #1e262c; }"
        "QCalendarWidget QAbstractItemView:enabled { color: #c8d0cc; background: #141a1e; "
        "selection-background-color: #3dd4c9; selection-color: #0a0e10; }");
    layout->addWidget(calendar_, 1);
    refresh();
}

void KillCounterDailyCalendarWidget::refresh() {
    if (calendar_ == nullptr) {
        return;
    }
    const auto days = pipela::core::kill_counter::statsDailySumsLastDays(42);
    QMap<QString, int> kills_by_date;
    for (const auto& d : days) {
        kills_by_date[QString::fromStdString(d.date_key)] = d.kills;
    }
    const QDate today = QDate::currentDate();
    for (int offset = 0; offset < 42; ++offset) {
        const QDate day = today.addDays(-offset);
        const QString key = day.toString(QString::fromUtf8("yyyy-MM-dd"));
        QTextCharFormat fmt;
        const int kills = kills_by_date.value(key, 0);
        if (kills > 0) {
            const int alpha = std::min(255, 80 + kills * 4);
            fmt.setBackground(QColor(61, 212, 201, alpha));
            fmt.setForeground(QColor(232, 240, 234));
            fmt.setToolTip(QString::fromUtf8("%1킬").arg(kills));
        } else {
            fmt.setBackground(QColor(24, 30, 36));
            fmt.setForeground(QColor(120, 130, 125));
        }
        calendar_->setDateTextFormat(day, fmt);
    }
}

}  // namespace pipela::ui::panels
