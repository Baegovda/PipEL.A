#include "overlays/flame_start_banner.hpp"

#include <chrono>

#include <QPainter>
#include <QPaintEvent>
#include <QTimer>

#include "pipela/core/state/app_state.hpp"
#include "pipela/core/win32/game_windows.hpp"

namespace pipela::ui::overlays {

namespace {

double wallNow() {
    using clock = std::chrono::system_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

}  // namespace

FlameStartBanner::FlameStartBanner(pipela::core::state::AppState* state, QWidget* parent)
    : QWidget(parent), state_(state) {
    setWindowFlags(Qt::FramelessWindowHint | Qt::Tool | Qt::WindowStaysOnTopHint |
                   Qt::WindowDoesNotAcceptFocus);
    setAttribute(Qt::WA_ShowWithoutActivating, true);
    setAttribute(Qt::WA_TransparentForMouseEvents, true);
    setAttribute(Qt::WA_TranslucentBackground, true);
    auto* timer = new QTimer(this);
    connect(timer, &QTimer::timeout, this, &FlameStartBanner::tick);
    timer->start(33);
    hide();
}

std::intptr_t FlameStartBanner::targetHwnd() const {
    if (state_ == nullptr) {
        return 0;
    }
    if (auto v = state_->get("target_hwnd")) {
        if (const auto* l = std::get_if<std::int64_t>(&*v)) {
            return static_cast<std::intptr_t>(*l);
        }
        if (const auto* i = std::get_if<int>(&*v)) {
            return *i;
        }
    }
    return 0;
}

void FlameStartBanner::parkHidden() {
    banner_text_.clear();
    hide();
}

void FlameStartBanner::tick() {
    if (state_ == nullptr) {
        parkHidden();
        return;
    }
    bool active = false;
    if (auto v = state_->get("flame_trigger_active")) {
        if (const auto* b = std::get_if<bool>(&*v)) {
            active = *b;
        }
    }
    if (active && !was_active_) {
        banner_text_ = QString::fromUtf8("Flame Trigger 시작!");
        hold_end_wall_ = wallNow() + 2.5;
    }
    was_active_ = active;
    if (banner_text_.isEmpty() || wallNow() > hold_end_wall_) {
        parkHidden();
        return;
    }
    const std::intptr_t hwnd = targetHwnd();
    if (!hwnd) {
        parkHidden();
        return;
    }
    const auto cr = pipela::core::win32::getClientRectScreen(hwnd);
    const int cl = std::get<0>(cr);
    const int ct = std::get<1>(cr);
    const int cr_r = std::get<2>(cr);
    const int cb = std::get<3>(cr);
    if (cr_r <= cl || cb <= ct) {
        parkHidden();
        return;
    }
    const int cw = cr_r - cl;
    const int ch = cb - ct;
    const int bw = std::min(cw - 40, 360);
    const int bh = 48;
    const int x = cl + (cw - bw) / 2;
    const int y = ct + ch / 4;
    setGeometry(x, y, bw, bh);
    if (!isVisible()) {
        show();
        raise();
    }
    update();
}

void FlameStartBanner::paintEvent(QPaintEvent* event) {
    Q_UNUSED(event);
    if (banner_text_.isEmpty()) {
        return;
    }
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing, true);
    QRect r = rect().adjusted(1, 1, -2, -2);
    p.setBrush(QColor(0, 0, 0, 200));
    p.setPen(QPen(QColor(72, 72, 92, 220), 1));
    p.drawRoundedRect(r, 6, 6);
    p.setPen(QColor(230, 230, 240));
    p.drawText(r, Qt::AlignCenter, banner_text_);
}

}  // namespace pipela::ui::overlays
