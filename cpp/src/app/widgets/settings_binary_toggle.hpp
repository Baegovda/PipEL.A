#pragma once

#include <QWidget>

class QCheckBox;

namespace pipela::ui::widgets {

// AGENT: ON/OFF registry bool toggle for settings panels (Python settings_binary_toggle parity).
class SettingsBinaryToggle : public QWidget {
    Q_OBJECT
public:
    explicit SettingsBinaryToggle(const QString& label, const char* registry_key,
                                  QWidget* parent = nullptr, bool default_on = false);

    bool checked() const;

signals:
    void toggled(bool on);

private:
    QCheckBox* cb_{nullptr};
    const char* registry_key_{nullptr};
};

}  // namespace pipela::ui::widgets
