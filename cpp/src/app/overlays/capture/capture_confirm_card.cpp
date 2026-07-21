#include "capture/capture_confirm_card.hpp"

#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>

#include "pipela/core/win32/game_windows.hpp"
#include "widgets/bgr_image_qt.hpp"
#include "widgets/card_popup_shell.hpp"

namespace pipela::ui::overlays::capture {

void showCaptureConfirmCard(QWidget* host, const QString& title,
                            const pipela::core::vision::BgrImage& preview,
                            std::intptr_t anchor_hwnd, std::function<void(bool accepted)> on_done) {
    auto* dlg = new pipela::ui::widgets::CardFramelessDialog(nullptr);
    dlg->setAttribute(Qt::WA_DeleteOnClose, true);
    dlg->setTitleText(title);

    auto* body = new QWidget(dlg);
    auto* layout = new QVBoxLayout(body);
    layout->setContentsMargins(4, 4, 4, 4);
    layout->setSpacing(12);

    auto* thumb = new QLabel(body);
    thumb->setAlignment(Qt::AlignCenter);
    thumb->setMinimumSize(240, 140);
    thumb->setStyleSheet(
        "background: #0a0c10; border: 1px solid #2a3440; border-radius: 6px; padding: 6px;");
    const QPixmap pm = pipela::app::widgets::pixmapFromBgr(preview, 280, 160);
    if (!pm.isNull()) {
        thumb->setPixmap(pm);
    } else {
        thumb->setText(QString::fromUtf8("(미리보기 없음)"));
        thumb->setStyleSheet(thumb->styleSheet() + " color: #8a92a0;");
    }
    layout->addWidget(thumb);

    auto* hint = new QLabel(QString::fromUtf8("이 영역을 템플릿으로 저장할까요?"), body);
    hint->setAlignment(Qt::AlignCenter);
    hint->setStyleSheet("color: #a8b0bc; font-size: 12px;");
    layout->addWidget(hint);

    auto* row = new QHBoxLayout();
    row->setSpacing(10);
    auto* cancel = new QPushButton(QString::fromUtf8("취소"), body);
    auto* ok = new QPushButton(QString::fromUtf8("저장"), body);
    cancel->setCursor(Qt::PointingHandCursor);
    ok->setCursor(Qt::PointingHandCursor);
    cancel->setStyleSheet(
        "QPushButton { background: #2a3038; color: #e8ecf2; border: 1px solid #3a424c; "
        "border-radius: 6px; padding: 9px 20px; min-width: 72px; text-align: center; }"
        "QPushButton:hover { background: #343c48; }");
    ok->setStyleSheet(
        "QPushButton { background: #2d6a4f; color: #f0faf4; border: none; border-radius: 6px; "
        "padding: 9px 22px; min-width: 72px; font-weight: 600; text-align: center; }"
        "QPushButton:hover { background: #35875f; }");
    row->addStretch(1);
    row->addWidget(cancel);
    row->addWidget(ok);
    layout->addLayout(row);

    dlg->setBodyWidget(body);
    dlg->resize(380, 300);

    QObject::connect(cancel, &QPushButton::clicked, dlg, [dlg, on_done]() {
        if (on_done) {
            on_done(false);
        }
        dlg->close();
    });
    QObject::connect(ok, &QPushButton::clicked, dlg, [dlg, on_done]() {
        if (on_done) {
            on_done(true);
        }
        dlg->close();
    });

    if (anchor_hwnd && pipela::core::win32::isWindow(anchor_hwnd)) {
        const auto cr = pipela::core::win32::getClientRectScreen(anchor_hwnd);
        const int cx = (std::get<0>(cr) + std::get<2>(cr)) / 2;
        const int cy = (std::get<1>(cr) + std::get<3>(cr)) / 2;
        dlg->move(cx - dlg->width() / 2, cy - dlg->height() / 2);
    } else {
        pipela::ui::widgets::centerCardPopup(dlg, host);
    }

    dlg->show();
    dlg->raise();
    dlg->activateWindow();
}

}  // namespace pipela::ui::overlays::capture
