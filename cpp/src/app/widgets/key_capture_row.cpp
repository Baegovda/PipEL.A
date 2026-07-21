#include "widgets/key_capture_row.hpp"

#include <QKeyEvent>
#include <QPushButton>
#include <QVBoxLayout>

#include "pipela/core/input/keymap.hpp"
#include "pipela/core/registry/store.hpp"
#include "theme/ui_adaptive.hpp"
#include "widgets/settings_chrome.hpp"

namespace pipela::app::widgets {

KeyCaptureRow::KeyCaptureRow(const QString& label, QWidget* parent) : QWidget(parent) {
    auto* lay = new QVBoxLayout(this);
    lay->setContentsMargins(0, 0, 0, 0);
    display_ = new QLineEdit(this);
    display_->setReadOnly(true);
    display_->setMinimumWidth(pipela::ui::theme::scalePxH(48, 420));
    display_->setMaximumWidth(pipela::ui::theme::scalePxH(120, 420));
    auto* cap_btn = new QPushButton(QString::fromUtf8("키 입력"), this);
    cap_btn->setObjectName(QString::fromUtf8("pipelaKeyCaptureBtn"));
    QObject::connect(cap_btn, &QPushButton::clicked, this, [this]() {
        if (capturing_) {
            endCapture(true);
            return;
        }
        beginCapture();
        if (auto* btn = findChild<QPushButton*>(QString::fromUtf8("pipelaKeyCaptureBtn"))) {
            btn->setText(QString::fromUtf8("키를 누르세요…"));
        }
    });
    addSettingsFieldRow(lay, label, display_, cap_btn);
}

void KeyCaptureRow::setRegistryKey(const char* key) {
    registry_key_ = key;
}

void KeyCaptureRow::setVk(int vk) {
    vk_ = vk & 0xFF;
    refreshDisplay();
}

void KeyCaptureRow::refreshDisplay() {
    if (display_ != nullptr) {
        display_->setText(
            QString::fromStdString(pipela::core::input::vkToDisplayName(static_cast<unsigned>(vk_))));
    }
}

void KeyCaptureRow::beginCapture() {
    capturing_ = true;
    setFocus(Qt::OtherFocusReason);
    grabKeyboard();
}

void KeyCaptureRow::endCapture(bool cancel) {
    if (!capturing_) {
        return;
    }
    capturing_ = false;
    releaseKeyboard();
    if (auto* btn = findChild<QPushButton*>(QString::fromUtf8("pipelaKeyCaptureBtn"))) {
        btn->setText(QString::fromUtf8("키 입력"));
    }
    if (!cancel && registry_key_ != nullptr) {
        pipela::core::registry::saveStringValue(registry_key_, std::to_string(vk_));
        if (on_saved_) {
            on_saved_(vk_);
        }
        emit vkChanged(vk_);
    }
}

void KeyCaptureRow::keyPressEvent(QKeyEvent* event) {
    if (!capturing_) {
        QWidget::keyPressEvent(event);
        return;
    }
    if (event->key() == Qt::Key_Escape) {
        endCapture(true);
        event->accept();
        return;
    }
    const int native_vk = static_cast<int>(event->nativeVirtualKey()) & 0xFF;
    if (native_vk == 0) {
        event->ignore();
        return;
    }
    vk_ = native_vk;
    refreshDisplay();
    endCapture(false);
    event->accept();
}

}  // namespace pipela::app::widgets
