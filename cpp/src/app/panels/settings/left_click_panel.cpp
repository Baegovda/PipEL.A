#include "panels/settings/left_click_panel.hpp"

#include <algorithm>
#include <cmath>

#include <QCheckBox>
#include <QLabel>
#include <QStackedWidget>
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

QWidget* createLeftClickPanel(QWidget* parent) {
    auto* page = new QWidget(parent);
    auto* lay = pipela::app::widgets::createSettingsPageLayout(page);

    auto* st1 = new QLabel(QString::fromUtf8("발동 조건"), page);
    st1->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(st1);
    pipela::app::widgets::addSettingsCenteredWidget(lay, st1);

    auto* hold = new pipela::app::widgets::DragDoubleSpinBox(page);
    hold->setRange(0.02, 2.0);
    hold->setDecimals(4);
    hold->setSingleStep(0.01);
    hold->setValue(regD("left_click_hold_sec", 0.05));
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("홀드 시간"), hold,
                                              new QLabel(QString::fromUtf8("초")));

    auto* st2 = new QLabel(QString::fromUtf8("클릭 간격"), page);
    st2->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle(6));
    pipela::app::widgets::settingsLabelAlignCenterH(st2);
    pipela::app::widgets::addSettingsCenteredWidget(lay, st2);

    auto* random_cb = new QCheckBox(QString::fromUtf8("랜덤 간격 사용"), page);
    random_cb->setChecked(regB("left_click_random_enabled", false));
    pipela::app::widgets::addSettingsCheckboxRow(lay, random_cb);

    auto* stack = new QStackedWidget(page);
    auto* fixed_w = new QWidget(page);
    auto* fixed_lay = pipela::app::widgets::createSettingsPageLayout(fixed_w);
    auto* fixed = new pipela::app::widgets::DragDoubleSpinBox(fixed_w);
    fixed->setRange(0.01, 5.0);
    fixed->setDecimals(4);
    fixed->setValue(regD("left_click_interval_ms", 100.0) / 1000.0);
    pipela::app::widgets::addSettingsFieldRow(fixed_lay, QString::fromUtf8("간격"), fixed,
                                              new QLabel(QString::fromUtf8("초")));

    auto* rand_w = new QWidget(page);
    auto* rand_lay = pipela::app::widgets::createSettingsPageLayout(rand_w);
    auto* min_iv = new pipela::app::widgets::DragDoubleSpinBox(rand_w);
    auto* max_iv = new pipela::app::widgets::DragDoubleSpinBox(rand_w);
    for (auto* sp : {min_iv, max_iv}) {
        sp->setRange(0.01, 5.0);
        sp->setDecimals(4);
    }
    min_iv->setValue(regD("left_click_random_min_ms", 80.0) / 1000.0);
    max_iv->setValue(regD("left_click_random_max_ms", 120.0) / 1000.0);
    pipela::app::widgets::addSettingsFieldRow(rand_lay, QString::fromUtf8("최소"), min_iv,
                                              new QLabel(QString::fromUtf8("초")));
    pipela::app::widgets::addSettingsFieldRow(rand_lay, QString::fromUtf8("최대"), max_iv,
                                              new QLabel(QString::fromUtf8("초")));

    stack->addWidget(fixed_w);
    stack->addWidget(rand_w);
    pipela::app::widgets::addSettingsCenteredWidget(lay, stack);
    stack->setCurrentIndex(random_cb->isChecked() ? 1 : 0);

    auto commit = [hold, fixed, min_iv, max_iv, random_cb]() {
        const double hold_v = std::clamp(hold->value(), 0.02, 2.0);
        double lo = std::clamp(min_iv->value(), 0.01, 5.0);
        double hi = std::clamp(max_iv->value(), 0.01, 5.0);
        if (lo > hi) {
            std::swap(lo, hi);
        }
        const double fixed_sec = std::clamp(fixed->value(), 0.01, 5.0);
        pipela::core::registry::saveStringValue("left_click_hold_sec",
                                                QString::number(hold_v, 'g', 8).toStdString());
        pipela::core::registry::saveStringValue(
            "left_click_interval_ms",
            QString::number(fixed_sec * 1000.0, 'g', 10).toStdString());
        pipela::core::registry::saveStringValue(
            "left_click_random_min_ms", QString::number(lo * 1000.0, 'g', 10).toStdString());
        pipela::core::registry::saveStringValue(
            "left_click_random_max_ms", QString::number(hi * 1000.0, 'g', 10).toStdString());
        pipela::core::registry::saveBoolValue("left_click_random_enabled", random_cb->isChecked());
    };

    QObject::connect(random_cb, &QCheckBox::toggled, page, [stack, random_cb, commit](bool on) {
        stack->setCurrentIndex(on ? 1 : 0);
        commit();
    });
    QObject::connect(hold,
                     QOverload<double>::of(&pipela::app::widgets::DragDoubleSpinBox::valueChanged),
                     page, [commit](double) { commit(); });
    QObject::connect(fixed,
                     QOverload<double>::of(&pipela::app::widgets::DragDoubleSpinBox::valueChanged),
                     page, [commit](double) { commit(); });
    QObject::connect(min_iv,
                     QOverload<double>::of(&pipela::app::widgets::DragDoubleSpinBox::valueChanged),
                     page, [commit](double) { commit(); });
    QObject::connect(max_iv,
                     QOverload<double>::of(&pipela::app::widgets::DragDoubleSpinBox::valueChanged),
                     page, [commit](double) { commit(); });

    lay->addStretch(1);
    return page;
}

}  // namespace pipela::app::panels::settings
