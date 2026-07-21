#include "widgets/paired_control_tab_bar.hpp"

#include <algorithm>

#include <cmath>

#include <QCursor>
#include <QFontMetricsF>
#include <QMouseEvent>
#include <QPaintEvent>
#include <QResizeEvent>
#include <QShowEvent>
#include <QStyle>
#include <QStyleOptionTab>
#include <QStylePainter>
#include <QTabWidget>
#include <QToolTip>

#include <QPainter>
#include <QPen>

#include "theme/control_tab_chrome.hpp"
#include "theme/theme_engine.hpp"
#include "theme/ui_adaptive.hpp"

namespace pipela::ui::widgets {

PairedControlTabBar::PairedControlTabBar(QWidget* parent) : QTabBar(parent) {
    setExpanding(true);
    setDrawBase(false);
    setUsesScrollButtons(false);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
}

int PairedControlTabBar::targetBarWidth() const {
    if (auto* tabs = qobject_cast<QTabWidget*>(parentWidget())) {
        return std::max(width(), tabs->width());
    }
    return width();
}

QSize PairedControlTabBar::tabSizeHint(int index) const {
    const QSize base = QTabBar::tabSizeHint(index);
    const int n = count();
    if (n <= 0) {
        return base;
    }
    const int w_bar = targetBarWidth();
    if (w_bar <= 0) {
        return base;
    }
    const int gap = pipela::ui::theme::mainTabsInterTabGapPx(w_bar);
    const int rail = pipela::ui::theme::mainTabsRailHpadPx(w_bar) * 2;
    const int inner = std::max(0, w_bar - gap * (n - 1) - rail);
    int w = inner / n;
    if (n == 2 && index == 1) {
        w = inner - inner / 2;
    } else if (n == 2) {
        w = inner / 2;
    }
    const int min_h =
        std::max(base.height(), pipela::ui::theme::mainTabsMinHeightPx(height()) + 2);
    return QSize(std::max(1, w), min_h);
}

QSize PairedControlTabBar::minimumTabSizeHint(int index) const { return tabSizeHint(index); }

QSize PairedControlTabBar::sizeHint() const {
    const QSize base = QTabBar::sizeHint();
    const int n = count();
    if (n <= 0) {
        return base;
    }
    const int w_bar = targetBarWidth();
    if (w_bar <= 0) {
        return base;
    }
    const int th = pipela::ui::theme::mainTabsMinHeightPx(height()) +
                   pipela::ui::theme::scalePxV(6, height());
    const int h = std::max(base.height(), th);
    return QSize(w_bar, h);
}

void PairedControlTabBar::showEvent(QShowEvent* event) {
    QTabBar::showEvent(event);
    updateGeometry();
}

void PairedControlTabBar::resizeEvent(QResizeEvent* event) {
    QTabBar::resizeEvent(event);
    updateGeometry();
}

void PairedControlTabBar::tabLayoutChange() {
    QTabBar::tabLayoutChange();
    updateGeometry();
}

QRect PairedControlTabBar::terminalGearHitRect() const {
    if (count() <= 0) {
        return {};
    }
    QStyleOptionTab opt;
    initStyleOption(&opt, 0);
    QRect rect = opt.rect;
    const int ph = pipela::ui::theme::mainTabsTabPadHPx(targetBarWidth());
    const int pv = pipela::ui::theme::mainTabsTabPadVPx(height());
    rect = rect.adjusted(ph, pv, -ph, -pv);
    if (rect.width() <= 0 || rect.height() <= 0) {
        return {};
    }
    QSize icon_sz = opt.iconSize;
    if (icon_sz.width() <= 0) {
        icon_sz = iconSize();
    }
    if (icon_sz.width() <= 0) {
        icon_sz = QSize(pipela::ui::theme::mainTabsBarIconSizePx(targetBarWidth(), height()),
                        pipela::ui::theme::mainTabsBarIconSizePx(targetBarWidth(), height()));
    }
    const int gap = pipela::ui::theme::mainTabsIconLabelGapPx(targetBarWidth());
    const int gap_gear = std::max(gap, pipela::ui::theme::scalePxH(6, targetBarWidth()));
    const QString text = opt.text;
    QFont font = this->font();
    QFontMetricsF fm(font);
    const int tw = text.isEmpty() ? 0 : static_cast<int>(fm.horizontalAdvance(text));
    const int icon_w = std::max(1, icon_sz.width());
    const bool icon_valid = !opt.icon.isNull();
    int cluster = 0;
    if (icon_valid) {
        cluster += icon_w + gap;
    }
    cluster += tw;
    const int gear_side =
        std::max(12, pipela::ui::theme::mainTabsBarIconSizePx(targetBarWidth(), height()) - 2);
    cluster += gap_gear + gear_side;
    const int x0 = rect.left() + std::max(0, (rect.width() - cluster) / 2);
    float after_text = static_cast<float>(x0);
    if (icon_valid) {
        after_text += icon_w + gap;
    }
    after_text += tw;
    const int gx = static_cast<int>(std::lround(after_text + gap_gear));
    const int gy = rect.center().y() - gear_side / 2;
    return QRect(gx, gy, gear_side, gear_side);
}

void PairedControlTabBar::paintOneTab(QStylePainter& painter, QStyleOptionTab& opt, int index) {
    initStyleOption(&opt, index);
    const bool selected = opt.state & QStyle::State_Selected;
    const bool hovered = opt.state & QStyle::State_MouseOver;
    QRect tab_rect = opt.rect.adjusted(3, 5, -3, -5);
    const int rad = pipela::ui::theme::mainTabsSegmentRadiusPx(height());
    painter.save();
    painter.setRenderHint(QPainter::Antialiasing, true);
    if (selected) {
        painter.setBrush(QColor(pipela::ui::theme::color("ACCENT_SOFT")));
        painter.setPen(QPen(QColor(pipela::ui::theme::color("ACCENT_BORDER")), 1));
        painter.drawRoundedRect(tab_rect, rad, rad);
    } else if (hovered) {
        painter.setBrush(QColor(pipela::ui::theme::color("BTN_HOVER")));
        painter.setPen(Qt::NoPen);
        painter.drawRoundedRect(tab_rect, rad, rad);
    }
    painter.restore();

    QRect rect = opt.rect;
    const int ph = pipela::ui::theme::mainTabsTabPadHPx(targetBarWidth());
    const int pv = pipela::ui::theme::mainTabsTabPadVPx(height());
    rect = rect.adjusted(ph, pv, -ph, -pv);
    if (rect.width() <= 0 || rect.height() <= 0) {
        return;
    }
    const bool terminal_gear = index == 0;
    QSize icon_sz = opt.iconSize;
    if (icon_sz.width() <= 0) {
        icon_sz = iconSize();
    }
    const bool en = opt.state & QStyle::State_Enabled;
    const auto icon_mode = en ? QIcon::Normal : QIcon::Disabled;
    const auto icon_state =
        (opt.state & QStyle::State_Selected) ? QIcon::On : QIcon::Off;
    QPixmap pm_icon = opt.icon.pixmap(icon_sz, icon_mode, icon_state);
    const bool icon_valid =
        !pm_icon.isNull() && pm_icon.width() > 1 && pm_icon.height() > 1;
    const int gap = pipela::ui::theme::mainTabsIconLabelGapPx(targetBarWidth());
    const int gap_gear = std::max(gap, pipela::ui::theme::scalePxH(6, targetBarWidth()));
    QFont font = this->font();
    const QString text = opt.text;
    QFontMetricsF fm(font);
    const int tw = text.isEmpty() ? 0 : static_cast<int>(fm.horizontalAdvance(text));
    const int icon_w = std::max(1, icon_sz.width());
    const int icon_h = std::max(1, icon_sz.height());
  int gear_w = 0;
    int gear_h = 0;
    QPixmap gear_pm;
    if (terminal_gear) {
        const int iz = std::max(icon_w, std::max(icon_h, std::max(iconSize().width(), iconSize().height())));
        gear_pm = style()->standardIcon(QStyle::SP_FileDialogDetailedView)
                      .pixmap(QSize(iz - 2, iz - 2), icon_mode, icon_state);
        if (!gear_pm.isNull()) {
            gear_w = gear_pm.width();
            gear_h = gear_pm.height();
        }
    }
    int cluster = 0;
    if (icon_valid) {
        cluster += icon_w + gap;
    }
    cluster += tw;
    if (terminal_gear && gear_w > 0) {
        cluster += gap_gear + gear_w;
    }
    const int x0 = rect.left() + std::max(0, (rect.width() - cluster) / 2);
    const int y_c = rect.center().y();
    painter.save();
    if (icon_valid) {
        painter.drawPixmap(x0, y_c - icon_h / 2, icon_w, icon_h, pm_icon);
    }
    float text_left = static_cast<float>(x0);
    if (icon_valid) {
        text_left += icon_w + gap;
    }
    if (tw > 0) {
        const QRect tr(static_cast<int>(text_left), rect.top(), std::max(1, tw), rect.height());
        QPalette pal = opt.palette;
        if (selected) {
            pal.setColor(QPalette::WindowText, QColor(pipela::ui::theme::color("ACCENT")));
        } else if (!en) {
            pal.setColor(QPalette::WindowText, QColor(pipela::ui::theme::color("FG_DIM")));
        } else {
            pal.setColor(QPalette::WindowText, QColor(pipela::ui::theme::color("FG_SECONDARY")));
        }
        style()->drawItemText(&painter, tr, Qt::AlignLeft | Qt::AlignVCenter, pal, en, text,
                              QPalette::WindowText);
    }
    if (terminal_gear && gear_w > 0 && gear_h > 0) {
        float after = static_cast<float>(x0);
        if (icon_valid) {
            after += icon_w + gap;
        }
        after += tw;
        const int gx = static_cast<int>(std::lround(after + gap_gear));
        const int gy = y_c - gear_h / 2;
        painter.drawPixmap(gx, gy, gear_w, gear_h, gear_pm);
    }
    painter.restore();
}

void PairedControlTabBar::paintEvent(QPaintEvent* event) {
    Q_UNUSED(event);
    QStylePainter painter(this);
    QStyleOptionTab opt;
    const int selected = currentIndex();
    for (int i = 0; i < count(); ++i) {
        if (i == selected) {
            continue;
        }
        paintOneTab(painter, opt, i);
    }
    if (selected >= 0) {
        paintOneTab(painter, opt, selected);
    }
}

void PairedControlTabBar::mousePressEvent(QMouseEvent* event) {
    if (event != nullptr && event->button() == Qt::LeftButton && tabAt(event->pos()) == 0) {
        const QRect gr = terminalGearHitRect();
        if (gr.isValid() && gr.contains(event->pos())) {
            emit terminalGearClicked();
            event->accept();
            return;
        }
    }
    QTabBar::mousePressEvent(event);
}

void PairedControlTabBar::mouseMoveEvent(QMouseEvent* event) {
    bool over = false;
    if (event != nullptr && tabAt(event->pos()) == 0) {
        const QRect gr = terminalGearHitRect();
        over = gr.isValid() && gr.contains(event->pos());
    }
    if (over != terminal_gear_hover_) {
        terminal_gear_hover_ = over;
        if (over) {
            setCursor(Qt::PointingHandCursor);
            setToolTip(QString::fromUtf8("터미널 설정"));
        } else {
            unsetCursor();
            setToolTip(QString());
        }
    }
    QTabBar::mouseMoveEvent(event);
}

void PairedControlTabBar::leaveEvent(QEvent* event) {
    if (terminal_gear_hover_) {
        terminal_gear_hover_ = false;
        unsetCursor();
        setToolTip(QString());
    }
    QTabBar::leaveEvent(event);
}

}  // namespace pipela::ui::widgets
