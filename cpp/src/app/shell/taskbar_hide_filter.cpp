#include "shell/taskbar_hide_filter.hpp"

#include <QEvent>
#include <QTimer>
#include <QWidget>

#include "pipela/core/win32/window_ops.hpp"

namespace pipela::ui::shell {

namespace {

void hideFromTaskbar(QWidget* widget) {
    if (widget == nullptr || !widget->isWindow()) {
        return;
    }
    const std::intptr_t hwnd = static_cast<std::intptr_t>(static_cast<qintptr>(widget->winId()));
    if (hwnd != 0) {
        pipela::core::win32::forceToolwindowExstyle(hwnd);
    }
}

}  // namespace

TaskbarHideFilter::TaskbarHideFilter(QObject* parent) : QObject(parent) {}

bool TaskbarHideFilter::eventFilter(QObject* watched, QEvent* event) {
    if (event->type() != QEvent::Show) {
        return false;
    }
    if (auto* widget = qobject_cast<QWidget*>(watched)) {
        if (widget->isWindow()) {
            hideFromTaskbar(widget);
            QTimer::singleShot(0, widget, [widget]() { hideFromTaskbar(widget); });
        }
    }
    return false;
}

}  // namespace pipela::ui::shell
