#pragma once

#include <vector>

#include <QWidget>

class QCalendarWidget;

namespace pipela::ui::panels {

class KillCounterDailyCalendarWidget : public QWidget {
    Q_OBJECT
public:
    explicit KillCounterDailyCalendarWidget(QWidget* parent = nullptr);

    void refresh();

private:
    QCalendarWidget* calendar_{nullptr};
};

}  // namespace pipela::ui::panels
