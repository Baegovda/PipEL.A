#include "game_overlay_window.hpp"

#include <QLabel>
#include <QVBoxLayout>

#include "theme/dpi_helpers.hpp"

namespace pipela::ui::overlays {

GameOverlayWindow::GameOverlayWindow(QWidget* parent) : QWidget(parent) {
    setWindowFlags(Qt::FramelessWindowHint | Qt::Tool | Qt::WindowStaysOnTopHint);
    setAttribute(Qt::WA_TranslucentBackground, true);
    setAttribute(Qt::WA_ShowWithoutActivating, true);
    setWindowOpacity(0.02);

    hint_ = new QLabel(this);
    hint_->setAlignment(Qt::AlignCenter);
    hint_->setStyleSheet("color: rgba(200,210,220,80); font-size: 11px;");
    hint_->setText(QString::fromUtf8("ROI 오버레이 (포팅 중)"));
    hint_->hide();
    auto* layout = new QVBoxLayout(this);
    layout->addWidget(hint_);
}

void GameOverlayWindow::syncToClientRect(std::intptr_t anchor_hwnd, int left, int top, int right,
                                         int bottom) {
    if (right <= left || bottom <= top) {
        hide();
        return;
    }
    const QRect geom = pipela::ui::theme::win32PhysicalScreenRectToQtOverlayGeometry(
        anchor_hwnd, left, top, right - left, bottom - top);
    setGeometry(geom);
    if (!isVisible()) {
        show();
    }
}

void GameOverlayWindow::setRegionPreviewActive(bool active) {
    if (hint_ != nullptr) {
        hint_->setVisible(active);
        setWindowOpacity(active ? 0.08 : 0.02);
    }
}

}  // namespace pipela::ui::overlays
