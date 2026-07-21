#include "widgets/call_merc_cooldown_button.hpp"

#include <chrono>
#include <cmath>

#include <QColor>
#include <QPainter>
#include <QPaintEvent>
#include <QTimer>

namespace pipela::ui::widgets {

namespace {

double nowMonoSec() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

}  // namespace

CallMercCooldownButton::CallMercCooldownButton(QWidget* parent) : QPushButton(parent) {
    flash_timer_ = new QTimer(this);
    flash_timer_->setInterval(16);
    connect(flash_timer_, &QTimer::timeout, this, &CallMercCooldownButton::tickCooldownFlash);
}

void CallMercCooldownButton::setCooldownFill(double v) {
    v = std::clamp(v, 0.0, 1.0);
    const double prev = cd_fill_;
    if (std::abs(v - prev) < 0.002 && !(cd_gauge_armed_ && v <= 0.01)) {
        return;
    }
    if (v > 0.02) {
        stopCooldownDoneFlash();
    }
    if (v > 0.001) {
        cd_gauge_armed_ = true;
    }
    cd_fill_ = v;
    if (cd_gauge_armed_ && v <= 0.01) {
        startCooldownDoneFlash();
        cd_gauge_armed_ = false;
    }
    update();
}

void CallMercCooldownButton::stopCooldownDoneFlash() {
    flash_start_mono_ = 0.0;
    if (flash_timer_ != nullptr) {
        flash_timer_->stop();
    }
}

void CallMercCooldownButton::startCooldownDoneFlash() {
    flash_start_mono_ = nowMonoSec();
    if (flash_timer_ != nullptr && !flash_timer_->isActive()) {
        flash_timer_->start();
    }
}

void CallMercCooldownButton::tickCooldownFlash() {
    if (flash_start_mono_ <= 0.0) {
        if (flash_timer_ != nullptr) {
            flash_timer_->stop();
        }
        return;
    }
    if (nowMonoSec() - flash_start_mono_ >= kFlashDurSec) {
        stopCooldownDoneFlash();
    }
    update();
}

void CallMercCooldownButton::paintEvent(QPaintEvent* event) {
    QPushButton::paintEvent(event);
    const int h = height();
    const int w = width();
    if (h <= 0 || w <= 0) {
        return;
    }
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);
    if (cd_fill_ > 0.001) {
        const int fill_h = std::max(1, static_cast<int>(std::round(h * cd_fill_)));
        const int y0 = h - fill_h;
        QColor c(QString::fromUtf8("#3dd4c9"));
        c.setAlpha(108);
        p.fillRect(0, y0, w, fill_h, c);
    }
    if (flash_start_mono_ > 0.0) {
        const double elapsed = nowMonoSec() - flash_start_mono_;
        if (elapsed >= kFlashDurSec) {
            stopCooldownDoneFlash();
        } else {
            const double u = elapsed / kFlashDurSec;
            const double wfade = std::pow(1.0 - u, 2.05);
            const QRect r = rect();
            QColor c2(QString::fromUtf8("#3dd4c9"));
            c2.setAlpha(static_cast<int>(55 + 185 * wfade));
            p.fillRect(r, c2);
            p.fillRect(r, QColor(255, 255, 255, static_cast<int>(40 + 145 * wfade)));
        }
    }
    Q_UNUSED(event);
}

}  // namespace pipela::ui::widgets
