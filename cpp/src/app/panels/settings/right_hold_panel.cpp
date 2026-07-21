#include "panels/settings/right_hold_panel.hpp"

#include <QCheckBox>
#include <QLabel>
#include <QVBoxLayout>

#include "pipela/core/registry/store.hpp"
#include "theme/ui_adaptive.hpp"
#include "widgets/drag_spin_box.hpp"
#include "widgets/settings_chrome.hpp"

namespace pipela::app::panels::settings {

namespace {

double regD(const char* key, double fb) {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(key);
    if (it == all.end()) {
        return fb;
    }
    return QString::fromStdString(it->second).toDouble();
}

bool regB(const char* key, bool fb) {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(key);
    if (it == all.end()) {
        return fb;
    }
    const std::string& v = it->second;
    return v == "true" || v == "True" || v == "1";
}

}  // namespace

QWidget* createRightHoldPanel(QWidget* parent) {
    auto* page = new QWidget(parent);
    auto* lay = pipela::app::widgets::createSettingsPageLayout(page);

    auto* en = new QCheckBox(QString::fromUtf8("Right Hold 활성화"), page);
    en->setChecked(regB("right_hold_feature_enabled", true));
    QObject::connect(en, &QCheckBox::toggled, page, [](bool on) {
        pipela::core::registry::saveBoolValue("right_hold_feature_enabled", on);
    });
    pipela::app::widgets::addSettingsCheckboxRow(lay, en);

    auto* hold = new pipela::app::widgets::DragDoubleSpinBox(page);
    hold->setRange(0.02, 5.0);
    hold->setDecimals(3);
    hold->setValue(regD("right_hold_min_sec", 0.15));
    QObject::connect(hold,
                     QOverload<double>::of(&pipela::app::widgets::DragDoubleSpinBox::valueChanged),
                     page, [](double v) {
                         pipela::core::registry::saveStringValue("right_hold_min_sec",
                                                                 QString::number(v).toStdString());
                     });
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("최소 홀드(초)"), hold);

    auto* hint = new QLabel(
        QString::fromUtf8("우클릭 홀드 자동화 — registry `right_hold_*` 키와 동기화됩니다."), page);
    hint->setWordWrap(true);
    hint->setStyleSheet(pipela::app::widgets::settingsCaptionStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(hint);
    pipela::app::widgets::addSettingsProseLabel(lay, hint);
    lay->addStretch(1);
    return page;
}

}  // namespace pipela::app::panels::settings
