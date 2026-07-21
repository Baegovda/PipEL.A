#include "widgets/drag_spin_box.hpp"

#include <algorithm>
#include <cmath>
#include <optional>

#include <QGuiApplication>
#include <QLineEdit>
#include <QMouseEvent>
#include <QWheelEvent>

#include "theme/ui_adaptive.hpp"

namespace pipela::app::widgets {

namespace {

constexpr double kWheelAnglePerNotch = 120.0;

class ScrubSpinLineEdit : public QLineEdit {
public:
    ScrubSpinLineEdit(QAbstractSpinBox* owner, double scrub_pixels_scale,
                      double pre_step_highlight_start)
        : QLineEdit(owner), owner_(owner), scrub_px_scale_(scrub_pixels_scale),
          pre_hl0_(pre_step_highlight_start) {
        setCursor(Qt::IBeamCursor);
    }

protected:
    void mousePressEvent(QMouseEvent* e) override {
        if (e->button() == Qt::LeftButton) {
            scrub_ = false;
            press_global_ = e->globalPosition();
            last_global_ = press_global_;
            acc_ = 0.0;
            setPreStepHighlight(false);
            if (!hasFocus()) {
                setFocus(Qt::MouseFocusReason);
            }
            e->accept();
            return;
        }
        QLineEdit::mousePressEvent(e);
    }

    void mouseMoveEvent(QMouseEvent* e) override {
        if ((e->buttons() & Qt::LeftButton) && press_global_.has_value() && last_global_.has_value()) {
            const QPointF g = e->globalPosition();
            if (!scrub_) {
                const QPointF delta = g - *press_global_;
                if (std::abs(delta.x()) + std::abs(delta.y()) >= thresholdPx()) {
                    beginScrub(g);
                }
            }
            if (scrub_) {
                const double dx = g.x() - last_global_->x();
                const double dy = g.y() - last_global_->y();
                last_global_ = g;
                acc_ += (dx - dy) * modifierScale();
                applyAccumulated();
                e->accept();
                return;
            }
            e->accept();
            return;
        }
        QLineEdit::mouseMoveEvent(e);
    }

    void mouseReleaseEvent(QMouseEvent* e) override {
        const bool was_scrub = scrub_;
        const std::optional<QPointF> saved_press = press_global_;
        endScrubSession();

        if (!was_scrub && e->button() == Qt::LeftButton && saved_press.has_value()) {
            const QPoint local = mapFromGlobal(saved_press->toPoint());
            QMouseEvent press_evt(QEvent::MouseButtonPress, QPointF(local), *saved_press,
                                  Qt::LeftButton, Qt::LeftButton, e->modifiers());
            QLineEdit::mousePressEvent(&press_evt);
        }
        setCursor(Qt::IBeamCursor);
        QLineEdit::mouseReleaseEvent(e);
    }

private:
    double thresholdPx() const { return static_cast<double>(pipela::ui::theme::scalePxV(4, 720)); }

    double pixelsPerStep() const {
        const double base = static_cast<double>(std::max(pipela::ui::theme::scalePxV(5, 720), 4));
        return base * scrub_px_scale_;
    }

    double modifierScale() const {
        const Qt::KeyboardModifiers mods = QGuiApplication::keyboardModifiers();
        if (mods & Qt::ShiftModifier) {
            return 0.25;
        }
        if (mods & Qt::ControlModifier) {
            return 4.0;
        }
        return 1.0;
    }

    void beginScrub(const QPointF& global_pos) {
        scrub_ = true;
        deselect();
        last_global_ = global_pos;
        acc_ = 0.0;
        setCursor(Qt::ClosedHandCursor);
        grabMouse();
    }

    void endScrubSession() {
        if (scrub_ && mouseGrabber() == this) {
            releaseMouse();
        }
        scrub_ = false;
        press_global_.reset();
        last_global_.reset();
        acc_ = 0.0;
        setPreStepHighlight(false);
    }

    void setPreStepHighlight(bool on) {
        if (on == pre_hl_on_) {
            return;
        }
        pre_hl_on_ = on;
        if (on) {
            setStyleSheet(
                "QLineEdit { border: 1px solid #6cff9a; background: rgba(108, 255, 154, 0.12); "
                "border-radius: 2px; }");
        } else {
            setStyleSheet(QString());
        }
    }

    void refreshPreStepHighlight() {
        if (pre_hl0_ <= 0.0 || !scrub_) {
            setPreStepHighlight(false);
            return;
        }
        const double px = pixelsPerStep();
        if (px <= 0.0) {
            return;
        }
        const double ap = std::abs(acc_) / px;
        setPreStepHighlight(pre_hl0_ <= ap && ap < 1.0 - 1e-5);
    }

    void applyAccumulated() {
        const double px = pixelsPerStep();
        while (acc_ >= px) {
            owner_->stepBy(1);
            acc_ -= px;
            setPreStepHighlight(false);
        }
        while (acc_ <= -px) {
            owner_->stepBy(-1);
            acc_ += px;
            setPreStepHighlight(false);
        }
        refreshPreStepHighlight();
    }

    QAbstractSpinBox* owner_{nullptr};
    bool scrub_{false};
    std::optional<QPointF> press_global_;
    std::optional<QPointF> last_global_;
    double acc_{0.0};
    double scrub_px_scale_{1.0};
    double pre_hl0_{0.0};
    bool pre_hl_on_{false};
};

void applyCoarseWheelStep(QAbstractSpinBox* spin, int notches_per_step, int& accum,
                            QWheelEvent* event) {
    accum += event->angleDelta().y();
    const int threshold = static_cast<int>(std::lround(kWheelAnglePerNotch * notches_per_step));
    if (std::abs(accum) < threshold) {
        event->accept();
        return;
    }
    const int delta = accum > 0 ? 1 : -1;
    accum = 0;
    event->accept();
    spin->stepBy(delta);
}

}  // namespace

DragSpinBox::DragSpinBox(QWidget* parent, double scrub_pixels_scale,
                         double pre_step_highlight_start)
    : QSpinBox(parent) {
    const double scale = std::max(0.4, std::min(8.0, scrub_pixels_scale));
    const double hl = std::max(0.0, std::min(0.99, pre_step_highlight_start));
    setLineEdit(new ScrubSpinLineEdit(this, scale, hl));
    setAccelerated(false);
}

void DragSpinBox::setWheelNotchesPerStep(int notches) {
    wheel_notches_per_step_ = std::max(0, notches);
    wheel_accum_ = 0;
}

void DragSpinBox::wheelEvent(QWheelEvent* event) {
    if (wheel_notches_per_step_ <= 0) {
        QSpinBox::wheelEvent(event);
        return;
    }
    applyCoarseWheelStep(this, wheel_notches_per_step_, wheel_accum_, event);
}

DragDoubleSpinBox::DragDoubleSpinBox(QWidget* parent, double scrub_pixels_scale,
                                     double pre_step_highlight_start)
    : QDoubleSpinBox(parent) {
    const double scale = std::max(0.4, std::min(8.0, scrub_pixels_scale));
    const double hl = std::max(0.0, std::min(0.99, pre_step_highlight_start));
    setLineEdit(new ScrubSpinLineEdit(this, scale, hl));
    setAccelerated(false);
}

void DragDoubleSpinBox::setWheelNotchesPerStep(int notches) {
    wheel_notches_per_step_ = std::max(0, notches);
    wheel_accum_ = 0;
}

void DragDoubleSpinBox::wheelEvent(QWheelEvent* event) {
    if (wheel_notches_per_step_ <= 0) {
        QDoubleSpinBox::wheelEvent(event);
        return;
    }
    applyCoarseWheelStep(this, wheel_notches_per_step_, wheel_accum_, event);
}

}  // namespace pipela::app::widgets
