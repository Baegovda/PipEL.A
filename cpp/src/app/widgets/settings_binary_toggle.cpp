#include "widgets/settings_binary_toggle.hpp"

#include <QCheckBox>
#include <QHBoxLayout>

#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "widgets/settings_chrome.hpp"

namespace pipela::ui::widgets {

SettingsBinaryToggle::SettingsBinaryToggle(const QString& label, const char* registry_key,
                                           QWidget* parent, bool default_on)
    : QWidget(parent), registry_key_(registry_key) {
    auto* lay = new QHBoxLayout(this);
    lay->setContentsMargins(0, 0, 0, 0);
    cb_ = new QCheckBox(label, this);
    bool on = default_on;
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(registry_key);
    if (it != all.end()) {
        on = pipela::core::registry::parseBool(it->second);
    }
    cb_->setChecked(on);
    connect(cb_, &QCheckBox::toggled, this, [this](bool checked) {
        if (registry_key_ != nullptr) {
            pipela::core::registry::saveBoolValue(registry_key_, checked);
        }
        emit toggled(checked);
    });
    lay->addStretch(1);
    lay->addWidget(cb_, 0, Qt::AlignHCenter);
    lay->addStretch(1);
}

bool SettingsBinaryToggle::checked() const { return cb_ != nullptr && cb_->isChecked(); }

}  // namespace pipela::ui::widgets
