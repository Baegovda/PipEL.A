#include "panels/settings/panel_factory.hpp"

#include <QImage>
#include <QLabel>
#include <QPixmap>
#include <QPushButton>
#include <QComboBox>
#include <QVBoxLayout>

#include "pipela/core/registry/store.hpp"
#include "widgets/bgr_image_qt.hpp"

#include "panels/settings/dedicated_panels.hpp"
#include "panels/settings/left_click_panel.hpp"
#include "panels/settings/registry_prefix_panel.hpp"
#include "panels/settings/right_hold_panel.hpp"
#include "panels/settings/worker_template_panel.hpp"
#include "panels/kill_counter_tier_table_dialog.hpp"
#include "panels/kill_counter_daily_calendar_widget.hpp"
#include "pipela/core/vision/registry_image_loader.hpp"
#include "panels/settings_panel_defs.hpp"
#include "widgets/settings_chrome.hpp"

namespace pipela::app::panels::settings {

namespace {

QWidget* makePlaceholderPanel(QWidget* parent, const QString& title, const QString& detail) {
    auto* page = new QWidget(parent);
    auto* layout = pipela::app::widgets::createSettingsPageLayout(page);
    auto* header = new QLabel(title, page);
    header->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(header);
    pipela::app::widgets::addSettingsCenteredWidget(layout, header);
    auto* hint = new QLabel(detail, page);
    hint->setWordWrap(true);
    hint->setStyleSheet(pipela::app::widgets::settingsCaptionStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(hint);
    pipela::app::widgets::addSettingsProseLabel(layout, hint);
    layout->addStretch(1);
    return page;
}

}  // namespace

QWidget* createPanelForDef(QWidget* parent, const pipela::ui::panels::SettingsPanelDef& def,
                           const SettingsPanelContext& ctx) {
    const QString title = QString::fromUtf8(def.title_ko);
    const QString prefix = QString::fromUtf8(def.registry_prefix);
    const std::string id(def.id);

    if (id == "interface") {
        return createInterfacePanel(parent, ctx);
    }
    if (id == "console") {
        return createConsolePanel(parent, ctx);
    }
    if (id == "left_click") {
        return createLeftClickPanel(parent);
    }
    if (id == "right_hold") {
        return createRightHoldPanel(parent);
    }
    if (id == "flame_trigger") {
        return createFlameTriggerPanel(parent);
    }
    if (id == "update") {
        return createUpdatePanel(parent, ctx);
    }
    if (id == "tesseract") {
        return createTesseractPanel(parent);
    }
    if (id == "kc_tier_table") {
        auto* page = new QWidget(parent);
        auto* layout = pipela::app::widgets::createSettingsPageLayout(page);
        auto* btn = new QPushButton(QString::fromUtf8("등급표 열기"), page);
        QObject::connect(btn, &QPushButton::clicked, page, [parent]() {
            pipela::ui::panels::showKillCounterTierTableDialog(parent);
        });
        pipela::app::widgets::addSettingsCenteredWidget(layout, btn);
        layout->addStretch(1);
        return page;
    }
    if (id == "kc_daily_calendar") {
        auto* page = new QWidget(parent);
        auto* layout = new QVBoxLayout(page);
        layout->addWidget(new pipela::ui::panels::KillCounterDailyCalendarWidget(page));
        return page;
    }
    if (id == "image_preview" || id == "template_thumb") {
        auto* page = new QWidget(parent);
        auto* layout = new QVBoxLayout(page);
        auto* hint = new QLabel(QString::fromUtf8("레지스트리 이미지 키 선택"), page);
        hint->setStyleSheet("color: #9aa0ac; font-size: 11px;");
        layout->addWidget(hint);
        auto* combo = new QComboBox(page);
        auto* img = new QLabel(page);
        img->setAlignment(Qt::AlignCenter);
        img->setMinimumHeight(160);
        img->setStyleSheet("background: #141a1e; border: 1px solid #3a4a42;");
        const auto values = pipela::core::registry::loadAllStringValues();
        QStringList keys;
#if defined(PIPELA_HAS_OPENCV)
        for (const auto& [k, v] : values) {
            if (k.find("_image_data") != std::string::npos && !v.empty()) {
                keys << QString::fromStdString(k);
            }
        }
        keys.sort();
        combo->addItems(keys);
        auto refresh = [combo, img]() {
            if (combo->count() < 1) {
                img->setText(QString::fromUtf8("이미지 없음"));
                return;
            }
            const std::string key = combo->currentText().toStdString();
            const auto all = pipela::core::registry::loadAllStringValues();
            const auto it = all.find(key);
            if (it == all.end() || it->second.empty()) {
                img->setPixmap(QPixmap());
                img->setText(QString::fromUtf8("데이터 없음"));
                return;
            }
            if (auto bgr = pipela::core::vision::loadBgrFromRegistryBase64(it->second)) {
                const QPixmap pm = pipela::app::widgets::pixmapFromBgr(*bgr, 480, 320);
                if (!pm.isNull()) {
                    img->setText({});
                    img->setPixmap(pm);
                    return;
                }
            }
            img->setPixmap(QPixmap());
            img->setText(QString::fromUtf8("로드 실패"));
        };
        QObject::connect(combo, QOverload<int>::of(&QComboBox::currentIndexChanged), page,
                         [refresh](int) { refresh(); });
        refresh();
#endif
        layout->addWidget(combo);
        layout->addWidget(img, 1);
        layout->addStretch(1);
        return page;
    }
    if (id == "settings_chrome") {
        auto* page = new QWidget(parent);
        auto* layout = new QVBoxLayout(page);
        layout->addWidget(new QLabel(QString::fromUtf8("설정 허브 푸터·크롬 — C++ parity path"), page));
        layout->addStretch(1);
        return page;
    }
    if (const WorkerSettingsSpec* spec = workerSettingsSpecForId(def.id)) {
        return createWorkerTemplatePanel(parent, *spec, ctx);
    }
    if (!prefix.isEmpty()) {
        return makeRegistryPrefixPanel(parent, title, prefix);
    }
    return makePlaceholderPanel(
        parent, title,
        QString::fromUtf8("전용 UI 순차 포팅 중 — Python `pipela_qt/panels/` 패리티 대기."));
}

}  // namespace pipela::app::panels::settings
