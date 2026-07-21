#pragma once

#include <QObject>

namespace pipela::ui::shell {

// AGENT: pipela_qt/taskbar_hide.py — WS_EX_TOOLWINDOW on Pipela top-level Show events.
class TaskbarHideFilter : public QObject {
    Q_OBJECT
public:
    explicit TaskbarHideFilter(QObject* parent = nullptr);

protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
};

}  // namespace pipela::ui::shell
