#include "update/update_controller.hpp"

#include <QMetaObject>
#include <QPointer>
#include <QThread>

#include <algorithm>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/update/installer.hpp"
#include "pipela/core/update/manifest.hpp"
#include "pipela/core/version.hpp"
#include "widgets/card_popup_shell.hpp"

namespace pipela::app::update {

namespace {

constexpr int kMinIntervalMin = 5;
constexpr int kDefaultIntervalMin = 10;

bool parseRegistryBool(const char* key, bool fallback) {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(key);
    if (it == all.end()) {
        return fallback;
    }
    return pipela::core::registry::parseBool(it->second);
}

int parseRegistryInt(const char* key, int fallback) {
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

UpdateController::UpdateController(QWidget* dialog_parent, QObject* parent)
    : QObject(parent), dialog_parent_(dialog_parent) {
    periodic_timer_ = new QTimer(this);
    periodic_timer_->setSingleShot(true);
    connect(periodic_timer_, &QTimer::timeout, this, &UpdateController::onPeriodicTick);
}

void UpdateController::start() {
    scheduleNextPeriodicCheck();
    QTimer::singleShot(4000, this, [this]() {
        if (autoUpdateEnabled()) {
            checkNow(UpdateCheckMode::Background);
        }
    });
}

void UpdateController::stop() {
    if (periodic_timer_ != nullptr) {
        periodic_timer_->stop();
    }
}

bool UpdateController::autoUpdateEnabled() const {
    return registryBool("update_auto_enabled", true);
}

int UpdateController::checkIntervalMinutes() const {
    const int v = registryInt("update_check_interval_min", kDefaultIntervalMin);
    return std::max(kMinIntervalMin, v);
}

QString UpdateController::pendingVersion() const {
    return pending_version_ ? QString::fromStdString(*pending_version_) : QString{};
}

bool UpdateController::registryBool(const char* key, bool fallback) const {
    return parseRegistryBool(key, fallback);
}

int UpdateController::registryInt(const char* key, int fallback) const {
    return parseRegistryInt(key, fallback);
}

void UpdateController::scheduleNextPeriodicCheck() {
    if (periodic_timer_ == nullptr) {
        return;
    }
    const int ms = checkIntervalMinutes() * 60 * 1000;
    periodic_timer_->start(ms);
}

void UpdateController::onPeriodicTick() {
    if (autoUpdateEnabled()) {
        checkNow(UpdateCheckMode::Background);
    } else {
        scheduleNextPeriodicCheck();
    }
}

void UpdateController::checkNow(UpdateCheckMode mode) {
    if (busy_.load() || installing_.load()) {
        return;
    }
    busy_.store(true);
    QPointer<UpdateController> self(this);
    const UpdateCheckMode mode_copy = mode;
    QThread* worker = QThread::create([self, mode_copy]() {
        const auto result = pipela::core::update::fetchUpdateManifest();
        if (!self) {
            return;
        }
        QMetaObject::invokeMethod(
            self,
            [self, result, mode_copy]() {
                if (!self) {
                    return;
                }
                self->busy_.store(false);
                self->finishCheck(mode_copy, result.first, result.second);
            },
            Qt::QueuedConnection);
    });
    QObject::connect(worker, &QThread::finished, worker, &QObject::deleteLater);
    worker->start();
}

void UpdateController::finishCheck(UpdateCheckMode mode, const nlohmann::json& manifest,
                                   const std::string& err) {
    scheduleNextPeriodicCheck();

    if (err == "no_manifest_url") {
        if (mode != UpdateCheckMode::Background) {
            pipela::ui::widgets::messageCardDialog(
                dialog_parent_, QString::fromUtf8("업데이트"),
                QString::fromUtf8("manifest URL이 비어 있습니다."));
        }
        return;
    }
    if (!err.empty()) {
        if (mode != UpdateCheckMode::Background) {
            pipela::ui::widgets::messageCardDialog(
                dialog_parent_, QString::fromUtf8("업데이트 확인 실패"),
                QString::fromStdString(err), QString::fromUtf8("danger"));
        }
        return;
    }

    std::string rv;
    if (manifest.contains("version") && manifest["version"].is_string()) {
        rv = manifest["version"].get<std::string>();
    }
    if (rv.empty()) {
        if (mode != UpdateCheckMode::Background) {
            pipela::ui::widgets::messageCardDialog(
                dialog_parent_, QString::fromUtf8("업데이트"),
                QString::fromUtf8("manifest에 version 필드가 없습니다."),
                QString::fromUtf8("warn"));
        }
        return;
    }

    const std::string current = pipela::core::appVersion();
    if (pipela::core::update::compareVersions(rv, current) <= 0) {
        pending_version_.reset();
        pending_download_url_.reset();
        pending_manifest_ = nlohmann::json{};
        emit updateAvailabilityChanged(false, {});
        if (mode != UpdateCheckMode::Background) {
            pipela::ui::widgets::messageCardDialog(
                dialog_parent_, QString::fromUtf8("업데이트"),
                QString::fromUtf8("이미 최신 버전입니다.\n\n현재: %1\n배포: %2")
                    .arg(QString::fromStdString(current))
                    .arg(QString::fromStdString(rv)));
        }
        return;
    }

    const auto dl = pipela::core::update::manifestDownloadUrl(manifest);
    if (!dl) {
        if (mode != UpdateCheckMode::Background) {
            pipela::ui::widgets::messageCardDialog(
                dialog_parent_, QString::fromUtf8("업데이트"),
                QString::fromUtf8("새 버전(%1)이 있으나 download_url이 없습니다.")
                    .arg(QString::fromStdString(rv)),
                QString::fromUtf8("warn"));
        }
        return;
    }

    pending_version_ = rv;
    pending_download_url_ = *dl;
    pending_manifest_ = manifest;
    emit updateAvailabilityChanged(true, QString::fromStdString(rv));
    emit statusMessage(QString::fromUtf8("[업데이트] 새 버전 %1 감지 (현재 %2)")
                           .arg(QString::fromStdString(rv))
                           .arg(QString::fromStdString(current)));

    const bool auto_install = mode == UpdateCheckMode::InstallNow ||
                              (autoUpdateEnabled() && mode == UpdateCheckMode::Background);
    if (auto_install) {
        beginInstall(rv, *dl);
        return;
    }

    if (mode == UpdateCheckMode::UserPrompt) {
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
                dialog_parent_, QString::fromUtf8("업데이트"),
                msg + QString::fromUtf8("\n\n지금 자동으로 설치할까요?"))) {
            beginInstall(rv, *dl);
        }
    }
}

void UpdateController::installPendingUpdate() {
    if (!pending_version_ || !pending_download_url_) {
        checkNow(UpdateCheckMode::InstallNow);
        return;
    }
    beginInstall(*pending_version_, *pending_download_url_);
}

void UpdateController::beginInstall(const std::string& version,
                                    const std::string& download_url) {
    if (installing_.load()) {
        return;
    }
    installing_.store(true);
    emit installStarted();
    emit statusMessage(QString::fromUtf8("[업데이트] %1 다운로드·설치 중…")
                           .arg(QString::fromStdString(version)));

#ifdef _WIN32
    const unsigned long pid = GetCurrentProcessId();
#else
    const unsigned long pid = 0;
#endif

    QPointer<UpdateController> self(this);
    QThread* worker = QThread::create([self, version, download_url, pid]() {
        const std::string err =
            pipela::core::update::applyReleaseFromUrl(download_url, version, pid);
        if (!self) {
            return;
        }
        QMetaObject::invokeMethod(
            self,
            [self, err]() {
                if (!self) {
                    return;
                }
                self->installing_.store(false);
                if (!err.empty()) {
                    emit self->installFailed(QString::fromStdString(err));
                    emit self->statusMessage(
                        QString::fromUtf8("[업데이트] 실패: %1").arg(QString::fromStdString(err)));
                    return;
                }
                emit self->statusMessage(QString::fromUtf8("[업데이트] 설치 완료 — 재시작합니다."));
                emit self->quitForUpdate();
            },
            Qt::QueuedConnection);
    });
    QObject::connect(worker, &QThread::finished, worker, &QObject::deleteLater);
    worker->start();
}

}  // namespace pipela::app::update
