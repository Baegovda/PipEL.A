#include "widgets/control_left_resize_edge.hpp"

#include <QGuiApplication>
#include <QMouseEvent>
#include <QScreen>

#include "dock/dock_panel_pair_resize.hpp"
#include "dock/side_dock_layout.hpp"
#include "shell/application.hpp"
#include "theme/dpi_helpers.hpp"

#include "pipela/core/win32/game_windows.hpp"

namespace pipela::ui::widgets {

ControlLeftResizeEdge::ControlLeftResizeEdge(PipelaMainWindow* main_window, QWidget* parent)
    : QWidget(parent), main_window_(main_window) {
    setCursor(Qt::SizeHorCursor);
    setToolTip(QString::fromUtf8("폭 조절 — 더블클릭: 작업영역 채움"));
    setFocusPolicy(Qt::NoFocus);
    setAttribute(Qt::WA_TransparentForMouseEvents, false);
    setStyleSheet("background: transparent;");
}

void ControlLeftResizeEdge::mousePressEvent(QMouseEvent* event) {
    if (event->button() == Qt::LeftButton && main_window_ != nullptr) {
        drag_ = true;
        drag_start_global_x_ = static_cast<int>(event->globalPosition().x());
        drag_start_w_ = std::max(8, main_window_->dockWidthLogical());
        grabMouse();
        event->accept();
        return;
    }
    QWidget::mousePressEvent(event);
}

void ControlLeftResizeEdge::mouseMoveEvent(QMouseEvent* event) {
    if (drag_ && main_window_ != nullptr) {
        const int gx = static_cast<int>(event->globalPosition().x());
        const int nw = pipela::app::dock::clampDockPairPanelW(drag_start_w_ + (drag_start_global_x_ - gx));
        main_window_->applyDockWidthLogical(nw);
        event->accept();
        return;
    }
    QWidget::mouseMoveEvent(event);
}

void ControlLeftResizeEdge::mouseReleaseEvent(QMouseEvent* event) {
    if (drag_ && event->button() == Qt::LeftButton) {
        drag_ = false;
        releaseMouse();
        event->accept();
        return;
    }
    QWidget::mouseReleaseEvent(event);
}

void ControlLeftResizeEdge::mouseDoubleClickEvent(QMouseEvent* event) {
    if (event->button() == Qt::LeftButton && main_window_ != nullptr) {
        int fill_w = 420;
        if (QScreen* scr = QGuiApplication::primaryScreen()) {
            fill_w = pipela::app::dock::clampDockPairPanelW(scr->availableGeometry().width() / 2);
        }
        const std::intptr_t anchor = main_window_->titleStripAnchorHwnd();
        if (anchor && pipela::core::win32::isWindow(anchor)) {
            const double scale = pipela::ui::theme::win32DpiScaleForHwnd(anchor);
            if (const auto w_fill = pipela::app::dock::computeDockPairFillWLog(anchor, scale)) {
                fill_w = *w_fill;
            }
        }
        main_window_->applyDockWidthLogical(fill_w);
        event->accept();
        return;
    }
    QWidget::mouseDoubleClickEvent(event);
}

}  // namespace pipela::ui::widgets
