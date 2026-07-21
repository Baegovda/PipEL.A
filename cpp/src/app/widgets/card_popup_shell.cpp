#include "widgets/card_popup_shell.hpp"

#include "theme/theme_engine.hpp"

#include <QDesktopServices>
#include <QHBoxLayout>
#include <QLabel>
#include <QPainter>
#include <QPushButton>
#include <QScreen>
#include <QUrl>
#include <QVBoxLayout>

namespace pipela::ui::widgets {

CardFramelessDialog::CardFramelessDialog(QWidget* parent) : QDialog(parent) {
    setWindowFlags(Qt::Dialog | Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint);
    setAttribute(Qt::WA_TranslucentBackground, true);
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(12, 12, 12, 12);
    card_ = new QWidget(this);
    card_->setObjectName(QString::fromUtf8("pipelaCardFrame"));
    card_->setStyleSheet(pipela::ui::theme::cardFrameQss());
    auto* card_lay = new QVBoxLayout(card_);
    card_lay->setContentsMargins(12, 12, 12, 12);
    card_lay->setSpacing(8);
    outer->addWidget(card_);
    body_host_ = new QWidget(card_);
    card_lay->addWidget(body_host_, 1);
}

void CardFramelessDialog::setTitleText(const QString& title) {
    if (auto* lay = qobject_cast<QVBoxLayout*>(card_->layout())) {
        if (lay->count() > 0) {
            if (auto* existing = lay->itemAt(0)->widget()) {
                if (existing->objectName() == QString::fromUtf8("pipelaCardTitle")) {
                    qobject_cast<QLabel*>(existing)->setText(title);
                    return;
                }
            }
        }
        auto* lbl = new QLabel(title, card_);
        lbl->setObjectName(QString::fromUtf8("pipelaCardTitle"));
        lbl->setStyleSheet(pipela::ui::theme::cardTitleQss());
        lay->insertWidget(0, lbl);
    }
}

void CardFramelessDialog::setBodyWidget(QWidget* body) {
    if (body_host_ == nullptr || body == nullptr) {
        return;
    }
    if (auto* old = body_host_->layout()) {
        QLayoutItem* item;
        while ((item = old->takeAt(0)) != nullptr) {
            delete item->widget();
            delete item;
        }
        delete old;
    }
    auto* lay = new QVBoxLayout(body_host_);
    lay->setContentsMargins(0, 0, 0, 0);
    lay->addWidget(body);
}

void CardFramelessDialog::paintEvent(QPaintEvent* event) {
    Q_UNUSED(event);
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing, true);
    p.fillRect(rect(), QColor(0, 0, 0, 96));
}

void centerCardPopup(QWidget* widget, QWidget* parent_or_anchor) {
    if (widget == nullptr) {
        return;
    }
    QRect target;
    if (parent_or_anchor != nullptr && parent_or_anchor->isVisible()) {
        target = parent_or_anchor->frameGeometry();
    } else if (QScreen* screen = QGuiApplication::primaryScreen()) {
        target = screen->availableGeometry();
    }
    const QSize sz = widget->sizeHint().expandedTo(widget->minimumSize());
    const int x = target.x() + (target.width() - sz.width()) / 2;
    const int y = target.y() + (target.height() - sz.height()) / 2;
    widget->resize(sz);
    widget->move(x, y);
}

void messageCardDialog(QWidget* parent, const QString& title, const QString& message,
                       const QString& tone) {
    CardFramelessDialog dlg(parent);
    dlg.setTitleText(title);
    auto* body = new QLabel(message, &dlg);
    body->setWordWrap(true);
    QString color = "#c8d4cc";
    if (tone == QString::fromUtf8("danger")) {
        color = "#f0a0a0";
    } else if (tone == QString::fromUtf8("warn")) {
        color = "#e8c878";
    }
    body->setStyleSheet(QString("color: %1; font-size: 12px;").arg(color));
    auto* ok = new QPushButton(QString::fromUtf8("확인"), &dlg);
    QObject::connect(ok, &QPushButton::clicked, &dlg, &QDialog::accept);
    auto* lay = new QVBoxLayout;
    lay->addWidget(body);
    lay->addWidget(ok, 0, Qt::AlignRight);
    auto* host = new QWidget(&dlg);
    host->setLayout(lay);
    dlg.setBodyWidget(host);
    centerCardPopup(&dlg, parent);
    dlg.exec();
}

bool confirmCardDialog(QWidget* parent, const QString& title, const QString& message,
                       const QString& confirm_text, const QString& cancel_text) {
    CardFramelessDialog dlg(parent);
    dlg.setTitleText(title);
    auto* body = new QLabel(message, &dlg);
    body->setWordWrap(true);
    body->setStyleSheet("color: #c8d4cc; font-size: 12px;");
    auto* yes = new QPushButton(confirm_text, &dlg);
    auto* no = new QPushButton(cancel_text, &dlg);
    QObject::connect(yes, &QPushButton::clicked, &dlg, &QDialog::accept);
    QObject::connect(no, &QPushButton::clicked, &dlg, &QDialog::reject);
    auto* row = new QHBoxLayout;
    row->addStretch(1);
    row->addWidget(no);
    row->addWidget(yes);
    auto* lay = new QVBoxLayout;
    lay->addWidget(body);
    lay->addLayout(row);
    auto* host = new QWidget(&dlg);
    host->setLayout(lay);
    dlg.setBodyWidget(host);
    centerCardPopup(&dlg, parent);
    return dlg.exec() == QDialog::Accepted;
}

void openUrlInBrowser(QWidget* parent, const QString& url, const QString& browser_url) {
    const QString open = browser_url.trimmed().isEmpty() ? url.trimmed() : browser_url.trimmed();
    if (open.isEmpty()) {
        messageCardDialog(parent, QString::fromUtf8("업데이트"),
                          QString::fromUtf8("다운로드 URL을 확인할 수 없습니다."), QString::fromUtf8("danger"));
        return;
    }
    if (!QDesktopServices::openUrl(QUrl(open))) {
        messageCardDialog(parent, QString::fromUtf8("업데이트"),
                          QString::fromUtf8("브라우저를 열 수 없습니다.\n\n") + open,
                          QString::fromUtf8("danger"));
    }
}

}  // namespace pipela::ui::widgets
