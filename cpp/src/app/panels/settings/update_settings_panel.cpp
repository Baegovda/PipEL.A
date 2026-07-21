#include "panels/settings/update_settings_panel.hpp"

#include <QComboBox>
#include <QFont>
#include <QLabel>
#include <QPointer>
#include <QPushButton>
#include <QThread>
#include <QVBoxLayout>

#include <nlohmann/json.hpp>

#include "pipela/core/registry/store.hpp"
#include "pipela/core/update/manifest.hpp"
#include "pipela/core/version.hpp"
#include "update/update_controller.hpp"
#include "widgets/card_popup_shell.hpp"
#include "widgets/settings_binary_toggle.hpp"
#include "widgets/settings_chrome.hpp"

namespace pipela::app::panels::settings {

namespace {

int registryInt(const char* key, int fallback) {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(key);
    if (it == all.end()) {
        return fallback;
    }
    try {
        return std::stoi(it->second);
    } catch (...) {
        return fallback;
    }
}

}  // namespace

UpdateSettingsPanel::UpdateSettingsPanel(pipela::app::update::UpdateController* controller,
                                       QWidget* parent)
    : QWidget(parent), controller_(controller) {
    auto* lay = pipela::app::widgets::createSettingsPageLayout(this);

    ver_lbl_ = new QLabel(
        QString::fromUtf8("현재 버전: %1").arg(QString::fromStdString(pipela::core::appVersion())),
        this);
    ver_lbl_->setWordWrap(true);
    ver_lbl_->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(ver_lbl_);
    pipela::app::widgets::addSettingsCenteredWidget(lay, ver_lbl_);

    auto* auto_toggle = new pipela::ui::widgets::SettingsBinaryToggle(
        QString::fromUtf8("자동 업데이트"), "update_auto_enabled", this, true);
    pipela::app::widgets::addSettingsCenteredWidget(lay, auto_toggle);
    QObject::connect(auto_toggle, &pipela::ui::widgets::SettingsBinaryToggle::toggled, this,
                    &UpdateSettingsPanel::onAutoToggle);

  auto* interval_hint = new QLabel(
        QString::fromUtf8("백그라운드 확인 주기 — manifest JSON만 조회(~2KB)하므로 성능 영향은 거의 없습니다."),
        this);
    interval_hint->setWordWrap(true);
    interval_hint->setStyleSheet(pipela::app::widgets::settingsCaptionStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(interval_hint);
    pipela::app::widgets::addSettingsProseLabel(lay, interval_hint);

    interval_combo_ = new QComboBox(this);
    interval_combo_->addItem(QString::fromUtf8("5분"), 5);
    interval_combo_->addItem(QString::fromUtf8("10분 (권장)"), 10);
    interval_combo_->addItem(QString::fromUtf8("15분"), 15);
    interval_combo_->addItem(QString::fromUtf8("30분"), 30);
    interval_combo_->addItem(QString::fromUtf8("60분"), 60);
    const int cur_interval = std::max(5, registryInt("update_check_interval_min", 10));
    for (int i = 0; i < interval_combo_->count(); ++i) {
        if (interval_combo_->itemData(i).toInt() == cur_interval) {
            interval_combo_->setCurrentIndex(i);
            break;
        }
    }
    QObject::connect(interval_combo_, QOverload<int>::of(&QComboBox::currentIndexChanged), this,
                    &UpdateSettingsPanel::onIntervalChanged);
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("확인 주기"), interval_combo_);

    auto* check_btn = new QPushButton(QString::fromUtf8("버전 확인"), this);
    install_btn_ = new QPushButton(QString::fromUtf8("지금 업데이트"), this);
    QFont bold = install_btn_->font();
    bold.setWeight(QFont::Bold);
    install_btn_->setFont(bold);
    QObject::connect(check_btn, &QPushButton::clicked, this, &UpdateSettingsPanel::requestManifest);
    QObject::connect(install_btn_, &QPushButton::clicked, this, &UpdateSettingsPanel::clickInstall);
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("수동"), check_btn,
                                              install_btn_);

    if (controller_ != nullptr) {
        QObject::connect(controller_, &pipela::app::update::UpdateController::updateAvailabilityChanged,
                         this, [this](bool available, const QString&) { refreshPendingUi(); });
        refreshPendingUi();
    }

    lay->addStretch(1);
}

void UpdateSettingsPanel::onAutoToggle(bool on) {
    pipela::core::registry::saveBoolValue("update_auto_enabled", on);
    if (controller_ != nullptr && on) {
        controller_->checkNow(pipela::app::update::UpdateCheckMode::Background);
    }
}

void UpdateSettingsPanel::onIntervalChanged(int index) {
    if (index < 0 || interval_combo_ == nullptr) {
        return;
    }
    const int minutes = interval_combo_->itemData(index).toInt();
    pipela::core::registry::saveStringValue("update_check_interval_min",
                                            std::to_string(minutes));
}

void UpdateSettingsPanel::refreshPendingUi() {
    if (install_btn_ == nullptr || controller_ == nullptr) {
        return;
    }
    const bool pending = controller_->updateAvailable();
    install_btn_->setEnabled(pending);
    install_btn_->setText(pending
                              ? QString::fromUtf8("지금 업데이트 (%1)").arg(controller_->pendingVersion())
                              : QString::fromUtf8("지금 업데이트"));
}

void UpdateSettingsPanel::runVersionCheck() {
    if (controller_ != nullptr) {
        controller_->checkNow(pipela::app::update::UpdateCheckMode::UserPrompt);
    } else {
        requestManifest();
    }
}

void UpdateSettingsPanel::requestManifest() {
    if (controller_ != nullptr) {
        controller_->checkNow(pipela::app::update::UpdateCheckMode::UserPrompt);
        return;
    }
    if (manifest_busy_) {
        return;
    }
    manifest_busy_ = true;
    QPointer<UpdateSettingsPanel> self(this);
    QThread* worker = QThread::create([self]() {
        const auto result = pipela::core::update::fetchUpdateManifest();
        if (!self) {
            return;
        }
        QMetaObject::invokeMethod(
            self,
            [self, result]() {
                if (!self) {
                    return;
                }
                self->manifest_busy_ = false;
                self->onManifest(result.first, result.second);
            },
            Qt::QueuedConnection);
    });
    QObject::connect(worker, &QThread::finished, worker, &QObject::deleteLater);
    worker->start();
}

void UpdateSettingsPanel::clickInstall() {
    if (controller_ != nullptr) {
        controller_->installPendingUpdate();
    }
}

void UpdateSettingsPanel::onManifest(const nlohmann::json& manifest, const std::string& err) {
    if (err == "no_manifest_url") {
        pipela::ui::widgets::messageCardDialog(
            this, QString::fromUtf8("업데이트"),
            QString::fromUtf8("업데이트 주소(manifest URL)가 비어 있습니다."));
        return;
    }
    if (!err.empty()) {
        pipela::ui::widgets::messageCardDialog(this, QString::fromUtf8("업데이트 확인 실패"),
                                               QString::fromStdString(err),
                                               QString::fromUtf8("danger"));
        return;
    }
    std::string rv;
    if (manifest.contains("version") && manifest["version"].is_string()) {
        rv = manifest["version"].get<std::string>();
    }
    if (rv.empty()) {
        pipela::ui::widgets::messageCardDialog(
            this, QString::fromUtf8("업데이트"),
            QString::fromUtf8("manifest에 version 필드가 없습니다."), QString::fromUtf8("warn"));
        return;
    }
    const std::string current = pipela::core::appVersion();
    if (pipela::core::update::compareVersions(rv, current) <= 0) {
        pipela::ui::widgets::messageCardDialog(
            this, QString::fromUtf8("업데이트"),
            QString::fromUtf8("이미 최신 버전입니다.\n\n현재: %1\n배포: %2")
                .arg(QString::fromStdString(current))
                .arg(QString::fromStdString(rv)));
        return;
    }
    QString msg = QString::fromUtf8("새 버전이 있습니다.\n\n현재: %1\n배포: %2")
                      .arg(QString::fromStdString(current))
                      .arg(QString::fromStdString(rv));
    if (manifest.contains("notes") && manifest["notes"].is_string()) {
        const QString notes =
            QString::fromStdString(manifest["notes"].get<std::string>()).trimmed();
        if (!notes.isEmpty()) {
            msg += QString::fromUtf8("\n\n") + notes;
        }
    }
    if (pipela::ui::widgets::confirmCardDialog(
            this, QString::fromUtf8("업데이트"),
            msg + QString::fromUtf8("\n\n지금 자동으로 설치할까요?"))) {
        if (controller_ != nullptr) {
            controller_->installPendingUpdate();
        }
    }
}

QWidget* createUpdateSettingsPanel(pipela::app::update::UpdateController* controller,
                                   QWidget* parent) {
    return new UpdateSettingsPanel(controller, parent);
}

}  // namespace pipela::app::panels::settings
