#include "overlays/flame_hud_popup.hpp"

#include <QLabel>
#include <QVBoxLayout>

namespace pipela::ui::overlays {

namespace {

constexpr int kHiddenX = -10000;
constexpr int kHiddenY = -10000;

}  // namespace

FlameHudPopup::FlameHudPopup(QWidget* parent) : QWidget(parent) {
    setWindowFlags(Qt::FramelessWindowHint | Qt::Tool | Qt::WindowStaysOnTopHint |
                   Qt::WindowDoesNotAcceptFocus);
    setAttribute(Qt::WA_ShowWithoutActivating, true);
    setAttribute(Qt::WA_TransparentForMouseEvents, true);
    setAttribute(Qt::WA_TranslucentBackground, true);

    auto* panel = new QWidget(this);
    panel->setStyleSheet(
        "background: rgba(12, 16, 20, 210); border: 1px solid rgba(61, 212, 201, 0.45); "
        "border-radius: 6px;");
    auto* lay = new QVBoxLayout(panel);
    lay->setContentsMargins(8, 6, 8, 6);
    lay->setSpacing(2);
    const QString line_qss = QString::fromUtf8("color: #e8f0ea; font-size: 10px; font-weight: 600;");
    line1_ = new QLabel(panel);
    line2_ = new QLabel(panel);
    line3_ = new QLabel(panel);
    for (QLabel* lbl : {line1_, line2_, line3_}) {
        lbl->setStyleSheet(line_qss);
        lbl->setWordWrap(true);
        lay->addWidget(lbl);
    }
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(0, 0, 0, 0);
    outer->addWidget(panel);
    setGeometry(kHiddenX, kHiddenY, 1, 1);
    hide();
}

void FlameHudPopup::setFlameLines(const QString& line1, const QString& line2,
                                  const QString& line3) {
    if (line1_ != nullptr) {
        line1_->setText(line1);
    }
    if (line2_ != nullptr) {
        line2_->setText(line2);
    }
    if (line3_ != nullptr) {
        line3_->setText(line3);
    }
}

void FlameHudPopup::placeAtCursorHotspot(int cur_x_phys, int cur_y_phys) {
    adjustSize();
    const int w = width() > 0 ? width() : sizeHint().width();
    const int h = height() > 0 ? height() : sizeHint().height();
    const int x = cur_x_phys - w / 2;
    const int y = cur_y_phys + 18;
    setGeometry(x, y, w, h);
    show();
    raise();
}

void FlameHudPopup::parkHidden() {
    hide();
    setGeometry(kHiddenX, kHiddenY, 1, 1);
}

}  // namespace pipela::ui::overlays
