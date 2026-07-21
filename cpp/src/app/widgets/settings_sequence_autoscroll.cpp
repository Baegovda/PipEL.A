#include "widgets/settings_sequence_autoscroll.hpp"

#include <algorithm>

#include <QAbstractAnimation>
#include <QEasingCurve>
#include <QPropertyAnimation>
#include <QScrollArea>
#include <QScrollBar>

#include "pipela/core/settings_sequence_scroll.hpp"
#include "theme/ui_adaptive.hpp"

namespace pipela::app::widgets {

namespace {

std::pair<int, int> scrollTargetsXy(QScrollArea* scroll, QWidget* target, int xm, int ym) {
    QWidget* w = scroll->widget();
    if (w == nullptr || target == nullptr) {
        return {0, 0};
    }
    QWidget* vp = scroll->viewport();
    const QPoint tl = target->mapTo(w, target->rect().topLeft());
    const QPoint br = target->mapTo(w, target->rect().bottomRight());
    QScrollBar* vbar = scroll->verticalScrollBar();
    QScrollBar* hbar = scroll->horizontalScrollBar();
    int cur_y = vbar->value();
    int cur_x = hbar->value();
    const int vh = std::max(1, vp->height());
    const int vw = std::max(1, vp->width());
    int y = cur_y;
    if (tl.y() - ym < y) {
        y = tl.y() - ym;
    }
    if (br.y() + ym > y + vh) {
        y = br.y() + ym - vh;
    }
    y = std::clamp(y, vbar->minimum(), vbar->maximum());
    int x = cur_x;
    if (tl.x() - xm < x) {
        x = tl.x() - xm;
    }
    if (br.x() + xm > x + vw) {
        x = br.x() + xm - vw;
    }
    x = std::clamp(x, hbar->minimum(), hbar->maximum());
    return {x, y};
}

void stopFeatureScrollAnims(QWidget* panel, const std::string& feature) {
    const QByteArray key = QByteArray("_seq_autoscroll_anims_") + QByteArray::fromStdString(feature);
    if (auto* list = panel->findChild<QObject*>(key)) {
        list->deleteLater();
    }
    panel->setProperty(key.constData(), QVariant{});
}

void animateScrollbars(QWidget* panel, const std::string& feature, QScrollArea* scroll, int target_x,
                       int target_y, int duration_ms) {
    QScrollBar* vbar = scroll->verticalScrollBar();
    QScrollBar* hbar = scroll->horizontalScrollBar();
    const int sx = hbar->value();
    const int sy = vbar->value();
    if (sy != target_y) {
        auto* av = new QPropertyAnimation(vbar, "value", panel);
        av->setDuration(duration_ms);
        av->setStartValue(sy);
        av->setEndValue(target_y);
        av->setEasingCurve(QEasingCurve::OutCubic);
        av->start(QAbstractAnimation::DeleteWhenStopped);
    }
    if (sx != target_x) {
        auto* ah = new QPropertyAnimation(hbar, "value", panel);
        ah->setDuration(duration_ms);
        ah->setStartValue(sx);
        ah->setEndValue(target_x);
        ah->setEasingCurve(QEasingCurve::OutCubic);
        ah->start(QAbstractAnimation::DeleteWhenStopped);
    }
    (void)feature;
}

}  // namespace

void applySequenceAutoscroll(QWidget* panel, QScrollArea* scroll, const std::string& feature,
                             const std::vector<QWidget*>& targets,
                             std::function<bool()> active_check) {
    if (panel == nullptr || scroll == nullptr || targets.empty() || !panel->isVisible()) {
        return;
    }
    const QByteArray last_key = QByteArray("_seq_autoscroll_last_") + QByteArray::fromStdString(feature);
    if (active_check && !active_check()) {
        panel->setProperty(last_key.constData(), QVariant{});
        return;
    }
    int st = pipela::core::settings::seqScrollGet(feature, 0);
    st = std::clamp(st, 0, static_cast<int>(targets.size()) - 1);
    const QVariant last = panel->property(last_key.constData());
    if (last.isValid() && last.toInt() == st) {
        return;
    }
    panel->setProperty(last_key.constData(), st);
    const int xm = pipela::ui::theme::scalePxV(8, 720);
    const int ym = pipela::ui::theme::scalePxV(24, 720);
    QWidget* tgt = targets[static_cast<size_t>(st)];
    const auto [tx, ty] = scrollTargetsXy(scroll, tgt, xm, ym);
    const int dur =
        std::clamp(pipela::ui::theme::scalePxV(340, 720), 200, 480);
    stopFeatureScrollAnims(panel, feature);
    animateScrollbars(panel, feature, scroll, tx, ty, dur);
}

}  // namespace pipela::app::widgets
