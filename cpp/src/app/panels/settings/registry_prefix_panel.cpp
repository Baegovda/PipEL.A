#include "panels/settings/registry_prefix_panel.hpp"

#include <QCheckBox>
#include <QLabel>
#include <QLineEdit>
#include <QScrollArea>
#include <QVBoxLayout>

#include "widgets/drag_spin_box.hpp"

#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "theme/ui_adaptive.hpp"
#include "widgets/settings_chrome.hpp"

namespace pipela::app::panels::settings {

namespace {

enum class FieldKind { kBool, kInt, kDouble, kStringReadOnly };

FieldKind inferFieldKind(const std::string& key, const std::string& value) {
    if (key.size() >= 11 && key.compare(key.size() - 11, 11, "_image_data") == 0) {
        return FieldKind::kStringReadOnly;
    }
    if (key.find("_region") != std::string::npos) {
        return FieldKind::kStringReadOnly;
    }
    if (value.size() > 200) {
        return FieldKind::kStringReadOnly;
    }
    if (value == "true" || value == "false" || value == "True" || value == "False") {
        return FieldKind::kBool;
    }
    bool has_dot = false;
    bool all_num = !value.empty();
    for (char c : value) {
        if (c == '.') {
            has_dot = true;
            continue;
        }
        if (c == '-' && &c == &value[0]) {
            continue;
        }
        if (c < '0' || c > '9') {
            all_num = false;
            break;
        }
    }
    if (all_num) {
        return has_dot ? FieldKind::kDouble : FieldKind::kInt;
    }
    return FieldKind::kStringReadOnly;
}

QString humanKeyLabel(const std::string& key) {
    return QString::fromStdString(key);
}

void commitString(const std::string& key, const std::string& value) {
    pipela::core::registry::saveStringValue(key, value);
}

}  // namespace

QWidget* makeRegistryPrefixPanel(QWidget* parent, const QString& title, const QString& prefix) {
    auto* page = new QWidget(parent);
    auto* outer = new QVBoxLayout(page);
    outer->setSpacing(pipela::app::widgets::settingsRootVerticalSpacing());
    outer->setContentsMargins(0, 0, 0, 0);

    auto* header = new QLabel(title, page);
    header->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(header);
    pipela::app::widgets::addSettingsCenteredWidget(outer, header);

    auto* scroll = new QScrollArea(page);
    pipela::app::widgets::configureSettingsScrollArea(scroll);
    auto* inner = new QWidget(scroll);
    auto* layout = new QVBoxLayout(inner);
    layout->setSpacing(pipela::app::widgets::settingsRootVerticalSpacing());
    layout->setContentsMargins(0, 0, 0, 0);

    const auto values = pipela::core::registry::loadAllStringValues();
    int shown = 0;
    if (!prefix.isEmpty()) {
        const std::string pfx = prefix.toStdString();
        for (const auto& [key, val] : values) {
            if (key.rfind(pfx, 0) != 0) {
                continue;
            }
            const FieldKind kind = inferFieldKind(key, val);
            const QString label = humanKeyLabel(key);

            if (kind == FieldKind::kBool) {
                auto* box = new QCheckBox(label, inner);
                box->setChecked(pipela::core::registry::parseBool(val));
                QObject::connect(box, &QCheckBox::toggled, inner,
                                 [key](bool on) { pipela::core::registry::saveBoolValue(key, on); });
                pipela::app::widgets::addSettingsCheckboxRow(layout, box);
            } else if (kind == FieldKind::kInt) {
                auto* spin = new pipela::app::widgets::DragSpinBox(inner);
                spin->setRange(-999999999, 999999999);
                spin->setValue(QString::fromStdString(val).toInt());
                spin->setMaximumWidth(pipela::ui::theme::scalePxH(120, 420));
                QObject::connect(
                    spin, QOverload<int>::of(&pipela::app::widgets::DragSpinBox::valueChanged), inner,
                    [key](int v) { commitString(key, std::to_string(v)); });
                pipela::app::widgets::addSettingsFieldRow(layout, label, spin);
            } else if (kind == FieldKind::kDouble) {
                auto* spin = new pipela::app::widgets::DragDoubleSpinBox(inner);
                spin->setRange(-1e9, 1e9);
                spin->setDecimals(6);
                spin->setSingleStep(0.01);
                spin->setValue(QString::fromStdString(val).toDouble());
                spin->setMaximumWidth(pipela::ui::theme::scalePxH(120, 420));
                QObject::connect(
                    spin, QOverload<double>::of(&pipela::app::widgets::DragDoubleSpinBox::valueChanged),
                    inner,
                    [key](double v) { commitString(key, QString::number(v, 'g', 12).toStdString()); });
                pipela::app::widgets::addSettingsFieldRow(layout, label, spin);
            } else {
                auto* row = new QLabel(
                    QString::fromUtf8("%1 = %2").arg(label, QString::fromStdString(val)), inner);
                row->setWordWrap(true);
                row->setStyleSheet(pipela::app::widgets::settingsCaptionStyle());
                pipela::app::widgets::settingsLabelAlignCenterH(row);
                pipela::app::widgets::addSettingsProseLabel(layout, row);
            }
            if (++shown >= 48) {
                break;
            }
        }
    }
    if (shown == 0) {
        auto* hint = new QLabel(
            QString::fromUtf8("레지스트리에 해당 prefix 키가 없습니다. 값을 편집하면 자동 저장됩니다."),
            inner);
        hint->setWordWrap(true);
        hint->setStyleSheet(pipela::app::widgets::settingsCaptionStyle());
        pipela::app::widgets::settingsLabelAlignCenterH(hint);
        pipela::app::widgets::addSettingsProseLabel(layout, hint);
    }
    layout->addStretch(1);
    scroll->setWidget(inner);
    outer->addWidget(scroll, 1);
    return page;
}

}  // namespace pipela::app::panels::settings
