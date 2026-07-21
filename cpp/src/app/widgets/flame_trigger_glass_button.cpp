#include "widgets/flame_trigger_glass_button.hpp"

#include <cmath>

#include <QColor>
#include <QLinearGradient>
#include <QPainter>
#include <QPaintEvent>
#include <QStyle>
#include <QStyleOptionButton>
#include <QStylePainter>
#include <QTimer>

namespace pipela::ui::widgets {

FlameTriggerGlassButton::FlameTriggerGlassButton(QWidget* parent) : QPushButton(parent) {
    anim_timer_ = new QTimer(this);
    anim_timer_->setInterval(16);
    connect(anim_timer_, &QTimer::timeout, this, &FlameTriggerGlassButton::tickPrism);
}

void FlameTriggerGlassButton::setEmitting(bool emitting) {
    if (emitting_ == emitting) {
        return;
    }
    emitting_ = emitting;
    if (emitting_) {
        if (!anim_timer_->isActive()) {
            anim_timer_->start();
        }
    } else if (anim_timer_ != nullptr) {
        anim_timer_->stop();
        phase_ = 0.0;
    }
    update();
}

void FlameTriggerGlassButton::tickPrism() {
    phase_ += 0.04;
    if (phase_ > 6.28318) {
        phase_ -= 6.28318;
    }
    update();
}

void FlameTriggerGlassButton::paintEvent(QPaintEvent* event) {
    QStyleOptionButton opt;
    initStyleOption(&opt);
    QStylePainter sp(this);
    sp.drawControl(QStyle::CE_PushButton, opt);
    if (!emitting_) {
        QPushButton::paintEvent(event);
        return;
    }
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);
    const QRect r = rect().adjusted(1, 1, -1, -1);
    const double sweep = 0.35 + 0.15 * std::sin(phase_);
    const int cx = r.center().x();
    QLinearGradient g(static_cast<qreal>(cx - r.width() * sweep), 0,
                      static_cast<qreal>(cx + r.width() * sweep), r.height());
    g.setColorAt(0.0, QColor(255, 255, 255, 0));
    g.setColorAt(0.45, QColor(120, 255, 230, 90));
    g.setColorAt(0.55, QColor(255, 255, 255, 140));
    g.setColorAt(1.0, QColor(255, 255, 255, 0));
    p.fillRect(r, g);
    Q_UNUSED(event);
}

}  // namespace pipela::ui::widgets
