#pragma once

#include <nlohmann/json.hpp>

#include <QWidget>

class QComboBox;
class QLabel;
class QPushButton;

namespace pipela::app::update {
class UpdateController;
}

namespace pipela::app::panels::settings {

class UpdateSettingsPanel : public QWidget {
    Q_OBJECT
public:
    explicit UpdateSettingsPanel(pipela::app::update::UpdateController* controller,
                                 QWidget* parent = nullptr);

    void runVersionCheck();

private slots:
    void onAutoToggle(bool on);
    void onIntervalChanged(int index);
    void requestManifest();
    void clickInstall();

private:
    void onManifest(const nlohmann::json& data, const std::string& err);
    void refreshPendingUi();

    pipela::app::update::UpdateController* controller_{nullptr};
    QLabel* ver_lbl_{nullptr};
    QComboBox* interval_combo_{nullptr};
    QPushButton* install_btn_{nullptr};
    bool manifest_busy_{false};
};

QWidget* createUpdateSettingsPanel(pipela::app::update::UpdateController* controller,
                                   QWidget* parent);

}  // namespace pipela::app::panels::settings
