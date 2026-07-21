#pragma once

#include <QObject>
#include <QTimer>

#include <atomic>
#include <optional>
#include <string>

#include <nlohmann/json.hpp>

class QWidget;

namespace pipela::app::update {

enum class UpdateCheckMode {
    Background,
    UserPrompt,
    InstallNow,
};

// AGENT: Manifest fetch + optional auto-install; periodic timer when auto-update enabled.
class UpdateController : public QObject {
    Q_OBJECT
public:
    explicit UpdateController(QWidget* dialog_parent, QObject* parent = nullptr);

    void start();
    void stop();

    bool autoUpdateEnabled() const;
    int checkIntervalMinutes() const;

    bool updateAvailable() const { return pending_version_.has_value(); }
    QString pendingVersion() const;

public slots:
    void checkNow(UpdateCheckMode mode = UpdateCheckMode::UserPrompt);
    void installPendingUpdate();

signals:
    void statusMessage(const QString& line);
    void updateAvailabilityChanged(bool available, const QString& remote_version);
    void installStarted();
    void installFailed(const QString& reason);
    void quitForUpdate();

private slots:
    void onPeriodicTick();

private:
    void scheduleNextPeriodicCheck();
    void finishCheck(UpdateCheckMode mode, const nlohmann::json& manifest, const std::string& err);
    void beginInstall(const std::string& version, const std::string& download_url);
    bool registryBool(const char* key, bool fallback) const;
    int registryInt(const char* key, int fallback) const;

    QWidget* dialog_parent_{nullptr};
    QTimer* periodic_timer_{nullptr};
    std::atomic<bool> busy_{false};
    std::atomic<bool> installing_{false};
    std::optional<std::string> pending_version_;
    std::optional<std::string> pending_download_url_;
    nlohmann::json pending_manifest_{};
};

}  // namespace pipela::app::update
