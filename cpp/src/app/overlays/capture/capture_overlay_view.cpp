#include "capture/capture_overlay_view.hpp"

#include <algorithm>

#include <QKeyEvent>
#include <QMouseEvent>
#include <QPaintEvent>
#include <QPainter>
#include <QTimer>
#include <QTimerEvent>

#include "capture/anchor_overlay_geometry.hpp"
#include "overlay_chrome.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/vision/roi.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::ui::overlays::capture {

CaptureOverlayView::CaptureOverlayView(QWidget* parent) : QWidget(parent) {
    setWindowFlags(Qt::Tool | Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint |
                   Qt::NoDropShadowWindowHint);
    setAttribute(Qt::WA_TranslucentBackground, false);
    setAttribute(Qt::WA_ShowWithoutActivating, true);
    setFocusPolicy(Qt::StrongFocus);
    setMouseTracking(true);
    setCursor(Qt::CrossCursor);
}

void CaptureOverlayView::beginSession(std::intptr_t anchor_hwnd,
                                      pipela::core::state::AppState* state,
                                      const QString& log_label, const QPixmap& freeze_pixmap,
                                      DragCompleteFn on_complete, VoidFn on_cancelled, LogFn log) {
    anchor_hwnd_ = anchor_hwnd;
    state_ = state;
    log_label_ = log_label;
    hint_text_ = QString::fromUtf8("드래그로 영역 지정 · Esc 취소 · 우클릭 취소");
    on_complete_ = std::move(on_complete);
    on_cancelled_ = std::move(on_cancelled);
    log_ = std::move(log);
    dragging_ = false;
    selection_ = QRect();
    freeze_pixmap_ = freeze_pixmap;
    anim_phase_ = 0.0;

    const auto geom = syncWidgetToAnchor(this, anchor_hwnd_);
    client_w_ = geom.client_w;
    client_h_ = geom.client_h;

    if (client_w_ < 2 || client_h_ < 2) {
        endSession(true);
        return;
    }
    if (state_ != nullptr) {
        state_->set("select_mode", pipela::core::state::StateValue{true});
    }
    if (anim_timer_id_ == 0) {
        anim_timer_id_ = startTimer(33);
    }
    show();
    raiseTopmost();
    QTimer::singleShot(0, this, [this]() { raiseTopmost(); });
    activateWindow();
    setFocus(Qt::PopupFocusReason);
}

void CaptureOverlayView::endSession(bool cancelled) {
    if (dragging_) {
        releaseMouse();
        dragging_ = false;
    }
    if (anim_timer_id_ != 0) {
        killTimer(anim_timer_id_);
        anim_timer_id_ = 0;
    }
    if (state_ != nullptr) {
        state_->set("select_mode", pipela::core::state::StateValue{false});
    }
    freeze_pixmap_ = QPixmap();
    hide();
    if (cancelled && on_cancelled_) {
        on_cancelled_();
    }
    on_complete_ = nullptr;
    on_cancelled_ = nullptr;
    log_ = nullptr;
}

void CaptureOverlayView::raiseTopmost() {
#ifdef _WIN32
    const auto wid = static_cast<HWND>(reinterpret_cast<void*>(winId()));
    if (wid) {
        SetWindowPos(wid, HWND_TOPMOST, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    }
#endif
}

QPoint CaptureOverlayView::clampToClient(const QPoint& p) const {
    const int max_x = std::max(0, client_w_ - 1);
    const int max_y = std::max(0, client_h_ - 1);
    return QPoint(std::clamp(p.x(), 0, max_x), std::clamp(p.y(), 0, max_y));
}

QRect CaptureOverlayView::normalizedSelection() const {
    QRect r = selection_.normalized();
    return r.intersected(QRect(0, 0, client_w_, client_h_));
}

QString CaptureOverlayView::selectionSizeLabel(const QRect& r) const {
    if (r.width() < 2 || r.height() < 2) {
        return {};
    }
    return QString::fromUtf8("%1 × %2").arg(r.width()).arg(r.height());
}

void CaptureOverlayView::finishDragRelease(const QPoint& release_pos) {
    if (!dragging_) {
        return;
    }
    dragging_ = false;
    releaseMouse();
    selection_ = QRect(drag_origin_, clampToClient(release_pos)).normalized();
    const QRect r = normalizedSelection();
    if (!pipela::core::vision::dragRectExceedsMinSize(r.width(), r.height())) {
        if (log_) {
            log_(QString::fromUtf8("[%1] 영역이 너무 작음").arg(log_label_));
        }
        endSession(true);
        return;
    }
    if (on_complete_) {
        on_complete_(r.x(), r.y(), r.width(), r.height(), client_w_, client_h_);
    }
    if (state_ != nullptr) {
        state_->set("select_mode", pipela::core::state::StateValue{false});
    }
    if (anim_timer_id_ != 0) {
        killTimer(anim_timer_id_);
        anim_timer_id_ = 0;
    }
    hide();
    on_complete_ = nullptr;
    on_cancelled_ = nullptr;
    log_ = nullptr;
}

void CaptureOverlayView::paintEvent(QPaintEvent* event) {
    Q_UNUSED(event);
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing, true);
    painter.setRenderHint(QPainter::SmoothPixmapTransform, true);

    if (!freeze_pixmap_.isNull()) {
        painter.drawPixmap(rect(), freeze_pixmap_);
    } else {
        painter.fillRect(rect(), QColor(0x0e, 0x10, 0x14));
    }

    const QRect sel = normalizedSelection();
    paintCaptureDimAroundSelection(painter, rect(), sel);
    if (sel.width() > 1 && sel.height() > 1) {
        paintCaptureSelectionChrome(painter, rect(), sel, anim_phase_, selectionSizeLabel(sel));
    }
    paintCaptureHintBar(painter, rect(), hint_text_);
}

void CaptureOverlayView::mousePressEvent(QMouseEvent* event) {
    if (event->button() == Qt::RightButton) {
        endSession(true);
        return;
    }
    if (event->button() != Qt::LeftButton) {
        return;
    }
    dragging_ = true;
    drag_origin_ = clampToClient(event->position().toPoint());
    selection_ = QRect(drag_origin_, drag_origin_);
    grabMouse();
    update();
}

void CaptureOverlayView::mouseMoveEvent(QMouseEvent* event) {
    if (!dragging_) {
        return;
    }
    selection_ = QRect(drag_origin_, clampToClient(event->position().toPoint())).normalized();
    anim_phase_ += 0.12;
    update(selection_.adjusted(-24, -40, 24, 48));
}

void CaptureOverlayView::mouseReleaseEvent(QMouseEvent* event) {
    if (event->button() != Qt::LeftButton) {
        return;
    }
    finishDragRelease(event->position().toPoint());
}

void CaptureOverlayView::keyPressEvent(QKeyEvent* event) {
    if (event->key() == Qt::Key_Escape) {
        endSession(true);
        return;
    }
    QWidget::keyPressEvent(event);
}

void CaptureOverlayView::timerEvent(QTimerEvent* event) {
    if (event->timerId() == anim_timer_id_) {
        if (dragging_) {
            anim_phase_ += 0.08;
            const QRect sel = normalizedSelection();
            if (sel.isValid()) {
                update(sel.adjusted(-24, -40, 24, 48));
            }
        }
        return;
    }
    QWidget::timerEvent(event);
}

}  // namespace pipela::ui::overlays::capture
