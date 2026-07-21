#include "overlay_chrome.hpp"

#include <cmath>

#include <QColor>
#include <QFont>
#include <QFontMetrics>
#include <QLinearGradient>
#include <QPainterPath>
#include <QPen>

namespace pipela::ui::overlays {

namespace {

constexpr int kAccentR = 0x5e;
constexpr int kAccentG = 0xc8;
constexpr int kAccentB = 0xff;

QColor accentColor() { return QColor(kAccentR, kAccentG, kAccentB); }

QColor panelBgColor() { return QColor(0x0e, 0x10, 0x14); }

}  // namespace

void paintOverlayDim(QPainter& painter, const QRect& bounds) {
    QColor dim = panelBgColor();
    dim.setAlphaF(0.44);
    painter.fillRect(bounds, dim);
}

void paintSelectionDragRect(QPainter& painter, const QRect& rect) {
    if (rect.width() < 1 || rect.height() < 1) {
        return;
    }
    QColor fill = accentColor();
    fill.setAlpha(75);
    painter.fillRect(rect, fill);
    QPen pen(accentColor());
    pen.setWidth(2);
    painter.setPen(pen);
    painter.setBrush(Qt::NoBrush);
    painter.drawRect(rect);
}

void paintRegionPreviewBox(QPainter& painter, const QRect& rect, double t_sec) {
    if (rect.width() < 1 || rect.height() < 1) {
        return;
    }
    double alpha = 48.0 + 12.0 * (0.5 + 0.5 * std::sin(t_sec * 0.88));
    alpha = std::clamp(alpha, 20.0, 100.0);
    QColor fill = accentColor();
    fill.setAlpha(static_cast<int>(alpha));
    painter.fillRect(rect, fill);
    QColor edge = accentColor();
    edge.setAlpha(220);
    QPen pen(edge);
    pen.setWidth(2);
    painter.setPen(pen);
    painter.setBrush(Qt::NoBrush);
    painter.drawRect(rect);
}

void paintCaptureDimAroundSelection(QPainter& painter, const QRect& bounds,
                                    const QRect& selection) {
    QColor dim(8, 10, 16, 168);
    if (!selection.isValid() || selection.width() < 2 || selection.height() < 2) {
        painter.fillRect(bounds, dim);
        return;
    }
    const QRect hole = selection.intersected(bounds);
    if (hole.width() < 1 || hole.height() < 1) {
        painter.fillRect(bounds, dim);
        return;
    }
    painter.fillRect(bounds.left(), bounds.top(), bounds.width(), hole.top() - bounds.top(), dim);
    painter.fillRect(bounds.left(), hole.bottom(), bounds.width(),
                     bounds.bottom() - hole.bottom() + 1, dim);
    painter.fillRect(bounds.left(), hole.top(), hole.left() - bounds.left(), hole.height(), dim);
    painter.fillRect(hole.right() + 1, hole.top(), bounds.right() - hole.right(), hole.height(),
                     dim);
}

void paintCaptureSelectionChrome(QPainter& painter, const QRect& bounds, const QRect& selection,
                                 double pulse_phase, const QString& size_label) {
    if (selection.width() < 2 || selection.height() < 2) {
        return;
    }
    const double pulse = 0.5 + 0.5 * std::sin(pulse_phase * 6.0);
    QColor glow = accentColor();
    glow.setAlpha(static_cast<int>(90 + 50 * pulse));
    QPainterPath path;
    path.addRoundedRect(QRectF(selection).adjusted(0.5, 0.5, -0.5, -0.5), 4.0, 4.0);
    painter.setPen(Qt::NoPen);
    painter.setBrush(glow);
    painter.drawPath(path);

    QColor inner(255, 255, 255, 28);
    painter.setBrush(inner);
    painter.drawPath(path);

    QPen border(accentColor());
    border.setWidthF(1.8);
    border.setCosmetic(true);
    painter.setPen(border);
    painter.setBrush(Qt::NoBrush);
    painter.drawRoundedRect(selection.adjusted(1, 1, -1, -1), 4, 4);

    constexpr int kHandle = 10;
    const QColor handle(255, 255, 255, 230);
    QPen hp(handle);
    hp.setWidth(3);
    hp.setCapStyle(Qt::RoundCap);
    painter.setPen(hp);
    const int l = selection.left();
    const int t = selection.top();
    const int r = selection.right();
    const int b = selection.bottom();
    painter.drawLine(l, t, l + kHandle, t);
    painter.drawLine(l, t, l, t + kHandle);
    painter.drawLine(r - kHandle, t, r, t);
    painter.drawLine(r, t, r, t + kHandle);
    painter.drawLine(l, b, l + kHandle, b);
    painter.drawLine(l, b - kHandle, l, b);
    painter.drawLine(r - kHandle, b, r, b);
    painter.drawLine(r, b - kHandle, r, b);

    if (size_label.isEmpty()) {
        return;
    }
    QFont font = painter.font();
    font.setPixelSize(12);
    font.setWeight(QFont::DemiBold);
    painter.setFont(font);
    const QFontMetrics fm(font);
    const int pad_h = 8;
    const int pad_v = 4;
    const int tw = fm.horizontalAdvance(size_label) + pad_h * 2;
    const int th = fm.height() + pad_v * 2;
    int bx = selection.center().x() - tw / 2;
    int by = selection.bottom() + 8;
    if (by + th > bounds.bottom() - 4) {
        by = selection.top() - th - 8;
    }
    bx = std::clamp(bx, bounds.left() + 4, std::max(bounds.left() + 4, bounds.right() - tw - 4));
    QRect badge(bx, by, tw, th);
    painter.setPen(Qt::NoPen);
    painter.setBrush(QColor(14, 18, 24, 220));
    painter.drawRoundedRect(badge, 6, 6);
    painter.setPen(QColor(0xe8, 0xee, 0xf8));
    painter.drawText(badge, Qt::AlignCenter, size_label);
}

void paintCaptureHintBar(QPainter& painter, const QRect& bounds, const QString& hint) {
    if (hint.isEmpty()) {
        return;
    }
    QFont font = painter.font();
    font.setPixelSize(13);
    font.setWeight(QFont::Medium);
    painter.setFont(font);
    const QFontMetrics fm(font);
    const int pad_h = 14;
    const int pad_v = 8;
    const int tw = fm.horizontalAdvance(hint) + pad_h * 2;
    const int th = fm.height() + pad_v * 2;
    QRect bar((bounds.width() - tw) / 2, 16, tw, th);
    QLinearGradient grad(bar.topLeft(), bar.bottomLeft());
    grad.setColorAt(0.0, QColor(22, 28, 38, 230));
    grad.setColorAt(1.0, QColor(14, 18, 26, 210));
    painter.setPen(QPen(QColor(kAccentR, kAccentG, kAccentB, 120), 1));
    painter.setBrush(grad);
    painter.drawRoundedRect(bar, 8, 8);
    painter.setPen(QColor(0xe0, 0xe6, 0xf0));
    painter.drawText(bar, Qt::AlignCenter, hint);
}

}  // namespace pipela::ui::overlays
