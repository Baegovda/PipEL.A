#include "panels/settings/worker_template_panel.hpp"

#include <QScrollArea>
#include <QLabel>
#include <QTimer>
#include <QVBoxLayout>

#include <functional>
#include <variant>
#include <vector>

#include "pipela/core/settings_sequence_scroll.hpp"
#include "theme/ui_adaptive.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "widgets/drag_spin_box.hpp"
#include "widgets/key_capture_row.hpp"
#include "widgets/settings_chrome.hpp"
#include "widgets/settings_sequence_autoscroll.hpp"
#include "widgets/template_path_connector_arrow.hpp"
#include "widgets/template_probe_section.hpp"

namespace pipela::app::panels::settings {

namespace {

TemplateSectionSpec section(const char* title, const char* threshold, const char* path,
                            const char* data, const char* region, const char* score,
                            const char* kind) {
    return TemplateSectionSpec{
        QString::fromUtf8(title),    QString::fromUtf8(threshold), QString::fromUtf8(path),
        QString::fromUtf8(data),     QString::fromUtf8(region),    QString::fromUtf8(score),
        QString::fromUtf8(kind),
    };
}

const WorkerSettingsSpec kRideSpec{
    "ride",
    {section("Ride 타겟 · 테스트", "ride_threshold", "RIDE_TARGET_IMAGE_PATH",
             "ride_target_image_data", "ride_detect_region", "ride_detection_score", "ride_target")}};

const WorkerSettingsSpec kHpRefillSpec{
    "hp_refill",
    {section("HP 바 · 체력 막대", "hp_refill_threshold", "HP_REFILL_ZKEY_IMAGE_PATH",
             "hp_refill_zkey_image_data", "hp_refill_detect_region", "hp_refill_detection_score",
             "hp_zkey")}};

const WorkerSettingsSpec kReloadSpec{
    "reload",
    {section("No bullet", "reload_nobullet_threshold", "RELOAD_NOBULLET_IMAGE_PATH",
             "reload_nobullet_image_data", "reload_nobullet_match_region", "nobullet_detection_score",
             "reload_nobullet"),
     section("Bullet", "reload_bullet_threshold", "RELOAD_BULLET_IMAGE_PATH",
             "reload_bullet_image_data", "reload_bullet_match_region", "bullet_detection_score",
             "reload_bullet"),
     section("Vault", "reload_vault_threshold", "RELOAD_VAULT_IMAGE_PATH", "reload_vault_image_data",
             "reload_vault_match_region", "vault_detection_score", "reload_vault")}};

const WorkerSettingsSpec kAmmoSpec{
    "ammo_restock",
    {section("Inven", "ammo_restock_inven_threshold", "AMMO_RESTOCK_INVEN_IMAGE_PATH",
             "ammo_restock_inven_image_data", "ammo_inven_match_region", "ammo_restock_inven_score",
             "ammo_inven"),
     section("Bank", "ammo_restock_bank_threshold", "AMMO_RESTOCK_BANK_IMAGE_PATH",
             "ammo_restock_bank_image_data", "ammo_bank_match_region", "ammo_restock_bank_score",
             "ammo_bank"),
     section("Buy button", "ammo_restock_buybutton_threshold", "AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH",
             "ammo_restock_buybutton_image_data", "ammo_buybutton_match_region",
             "ammo_restock_buybutton_score", "ammo_buybutton")}};

const WorkerSettingsSpec kCallMercSpec{
    "call_merc",
    {section("Merc 1", "call_merc_1_threshold", "CALL_MERC_1_IMAGE_PATH", "call_merc_1_image_data",
             "call_merc_1_match_region", "call_merc_1_score", "call_merc_1"),
     section("Merc 2", "call_merc_2_threshold", "CALL_MERC_2_IMAGE_PATH", "call_merc_2_image_data",
             "call_merc_2_match_region", "call_merc_2_score", "call_merc_2"),
     section("Merc 3", "call_merc_3_threshold", "CALL_MERC_3_IMAGE_PATH", "call_merc_3_image_data",
             "call_merc_3_match_region", "call_merc_3_score", "call_merc_3"),
     section("Merc 4", "call_merc_4_threshold", "CALL_MERC_4_IMAGE_PATH", "call_merc_4_image_data",
             "call_merc_4_match_region", "call_merc_4_score", "call_merc_4")}};

const WorkerSettingsSpec kStartGameSpec{
    "start_game",
    {section("Launcher", "start_game_launcher_threshold", "START_GAME_IMAGE_PATH",
             "start_game_launcher_image_data", "start_game_launcher_match_region",
             "start_game_launcher_score", "start_game_launcher"),
     section("Intro skip", "start_game_intro_skip_threshold", "START_GAME_INTRO_SKIP_IMAGE_PATH",
             "start_game_intro_skip_image_data", "start_game_intro_skip_match_region",
             "start_game_intro_skip_score", "start_game_intro_skip"),
     section("Accept", "start_game_accept_threshold", "START_GAME_ACCEPT_IMAGE_PATH",
             "start_game_accept_image_data", "start_game_accept_match_region",
             "start_game_accept_score", "start_game_accept")}};

const WorkerSettingsSpec* kAllSpecs[] = {&kRideSpec, &kHpRefillSpec, &kReloadSpec, &kAmmoSpec,
                                       &kCallMercSpec, &kStartGameSpec};

std::optional<std::string> autoscrollFeatureForPanel(const QString& panel_id) {
    if (panel_id == QString::fromUtf8("reload")) {
        return pipela::core::settings::kFeatReload;
    }
    if (panel_id == QString::fromUtf8("ammo_restock")) {
        return pipela::core::settings::kFeatAmmoRestock;
    }
    if (panel_id == QString::fromUtf8("call_merc")) {
        return pipela::core::settings::kFeatCallMerc;
    }
    if (panel_id == QString::fromUtf8("start_game")) {
        return pipela::core::settings::kFeatStartGame;
    }
    return std::nullopt;
}

bool panelUsesConnectorArrows(const QString& panel_id) {
    return panel_id == QString::fromUtf8("reload") || panel_id == QString::fromUtf8("ammo_restock") ||
           panel_id == QString::fromUtf8("call_merc") || panel_id == QString::fromUtf8("start_game");
}

double readDetectionScore(const SettingsPanelContext& ctx, const QString& score_key) {
    if (ctx.state == nullptr || score_key.isEmpty()) {
        return 0.0;
    }
    const auto v = ctx.state->get(score_key.toStdString());
    if (!v) {
        return 0.0;
    }
    if (const auto* d = std::get_if<double>(&*v)) {
        return *d;
    }
    if (const auto* i = std::get_if<int>(&*v)) {
        return static_cast<double>(*i);
    }
    return 0.0;
}

double readThresholdValue(const QString& threshold_key) {
    if (threshold_key.isEmpty()) {
        return 0.8;
    }
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(threshold_key.toStdString());
    if (it == all.end()) {
        return 0.8;
    }
    bool ok = false;
    const double v = QString::fromStdString(it->second).toDouble(&ok);
    return ok ? v : 0.8;
}

struct PathArrowBinding {
    pipela::app::widgets::TemplatePathConnectorArrow* arrow{nullptr};
    TemplateSectionSpec section;
};

}  // namespace

QWidget* createWorkerTemplatePanel(QWidget* parent, const WorkerSettingsSpec& spec,
                                   const SettingsPanelContext& ctx) {
    auto* page = new QWidget(parent);
    auto* outer = new QVBoxLayout(page);
    outer->setContentsMargins(0, 0, 0, 0);
    outer->setSpacing(pipela::app::widgets::settingsRootVerticalSpacing());

    auto* scroll = new QScrollArea(page);
    pipela::app::widgets::configureSettingsScrollArea(scroll);
    auto* inner = new QWidget(scroll);
    auto* layout = new QVBoxLayout(inner);
    layout->setSpacing(pipela::app::widgets::settingsRootVerticalSpacing());
    layout->setContentsMargins(0, 0, 0, 0);

    std::vector<pipela::app::widgets::TemplateProbeSection*> probes;
    std::vector<PathArrowBinding> arrow_bindings;
    const bool use_arrows = panelUsesConnectorArrows(spec.panel_id);
    for (size_t i = 0; i < spec.sections.size(); ++i) {
        const auto& section_spec = spec.sections[i];
        if (use_arrows && spec.panel_id != QString::fromUtf8("reload") &&
            spec.panel_id != QString::fromUtf8("start_game") && i > 0) {
            auto* arrow = new pipela::app::widgets::TemplatePathConnectorArrow(inner);
            pipela::app::widgets::addSettingsCenteredWidget(layout, arrow);
            arrow_bindings.push_back({arrow, spec.sections[i - 1]});
        }
        auto* probe = new pipela::app::widgets::TemplateProbeSection(inner);
        probe->configure(section_spec, ctx);
        addSettingsCenteredWidget(layout, probe);
        probes.push_back(probe);
        if (use_arrows && spec.panel_id == QString::fromUtf8("reload")) {
            auto* arrow = new pipela::app::widgets::TemplatePathConnectorArrow(inner);
            pipela::app::widgets::addSettingsCenteredWidget(layout, arrow);
            arrow_bindings.push_back({arrow, section_spec});
        }
        if (use_arrows && spec.panel_id == QString::fromUtf8("start_game") &&
            i + 1 < spec.sections.size()) {
            auto* arrow = new pipela::app::widgets::TemplatePathConnectorArrow(inner);
            pipela::app::widgets::addSettingsCenteredWidget(layout, arrow);
            arrow_bindings.push_back({arrow, section_spec});
        }
    }
    if (spec.panel_id == QString::fromUtf8("hp_refill")) {
        auto* key_heading = new QLabel(QString::fromUtf8("Z 키 입력"), inner);
        key_heading->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle(4));
        pipela::app::widgets::settingsLabelAlignCenterH(key_heading);
        layout->addWidget(key_heading);
        auto* key_row = new pipela::app::widgets::KeyCaptureRow(QString::fromUtf8("HP 회복 키"), inner);
        key_row->setRegistryKey("hp_refill_key_code");
        int vk = 0x5A;
        const auto all_keys = pipela::core::registry::loadAllStringValues();
        const auto kit = all_keys.find("hp_refill_key_code");
        if (kit != all_keys.end()) {
            vk = QString::fromStdString(kit->second).toInt();
        }
        key_row->setVk(vk);
        key_row->setOnSaved([state = ctx.state](int v) {
            if (state != nullptr) {
                state->set("hp_refill_key_code", pipela::core::state::StateValue{v});
            }
        });
        layout->addWidget(key_row);
    }
    if (spec.panel_id == QString::fromUtf8("ammo_restock")) {
        auto* key_heading = new QLabel(QString::fromUtf8("토글 키"), inner);
        key_heading->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle(4));
        pipela::app::widgets::settingsLabelAlignCenterH(key_heading);
        layout->addWidget(key_heading);
        auto* key_row =
            new pipela::app::widgets::KeyCaptureRow(QString::fromUtf8("Ammo Restock 토글"), inner);
        key_row->setRegistryKey("ammo_restock_toggle_key_code");
        int vk = 0x75;
        const auto all_keys = pipela::core::registry::loadAllStringValues();
        const auto kit = all_keys.find("ammo_restock_toggle_key_code");
        if (kit != all_keys.end()) {
            vk = QString::fromStdString(kit->second).toInt();
        }
        key_row->setVk(vk);
        key_row->setOnSaved([state = ctx.state](int v) {
            if (state != nullptr) {
                state->set("ammo_restock_toggle_key_code",
                           pipela::core::state::StateValue{v});
            }
        });
        layout->addWidget(key_row);
    }
    if (spec.panel_id == QString::fromUtf8("reload")) {
        auto* ammo_heading = new QLabel(QString::fromUtf8("탄약 수"), inner);
        ammo_heading->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle(4));
        pipela::app::widgets::settingsLabelAlignCenterH(ammo_heading);
        layout->addWidget(ammo_heading);
        auto* ammo_spin = new pipela::app::widgets::DragSpinBox(inner);
        ammo_spin->setRange(1, 99999);
        const int ammo_default = 45;
        int ammo_val = ammo_default;
        const auto all = pipela::core::registry::loadAllStringValues();
        const auto it = all.find("reload_ammo_count");
        if (it != all.end()) {
            ammo_val = QString::fromStdString(it->second).toInt();
        }
        ammo_spin->setValue(std::max(1, std::min(99999, ammo_val)));
        ammo_spin->setMaximumWidth(pipela::ui::theme::scalePxH(88, 420));
        QObject::connect(ammo_spin, QOverload<int>::of(&pipela::app::widgets::DragSpinBox::valueChanged),
                         page,
                         [ctx](int v) {
                             const int clamped = std::max(1, std::min(99999, v));
                             pipela::core::registry::saveStringValue("reload_ammo_count",
                                                                     std::to_string(clamped));
                             if (ctx.state != nullptr) {
                                 ctx.state->set("reload_ammo_count",
                                                pipela::core::state::StateValue{clamped});
                             }
                         });
        pipela::app::widgets::addSettingsFieldRow(layout, QString::fromUtf8("리로드 탄 수"), ammo_spin);
    }
    layout->addStretch(1);
    scroll->setWidget(inner);
    outer->addWidget(scroll, 1);

    if (!arrow_bindings.empty()) {
        auto* arrow_timer = new QTimer(page);
        arrow_timer->setInterval(200);
        QObject::connect(arrow_timer, &QTimer::timeout, page,
                         [arrow_bindings, ctx]() {
                             for (const auto& binding : arrow_bindings) {
                                 if (binding.arrow == nullptr) {
                                     continue;
                                 }
                                 const double score =
                                     readDetectionScore(ctx, binding.section.score_state_key);
                                 const double thr =
                                     readThresholdValue(binding.section.threshold_key);
                                 binding.arrow->feedThresholdEdge(score, thr);
                             }
                         });
        arrow_timer->start();
    }

    if (const auto feature = autoscrollFeatureForPanel(spec.panel_id)) {
        auto* scroll_timer = new QTimer(page);
        scroll_timer->setInterval(200);
        QObject::connect(scroll_timer, &QTimer::timeout, page, [page, scroll, feature, probes, ctx]() {
            std::vector<QWidget*> targets;
            targets.reserve(probes.size());
            for (auto* probe : probes) {
                targets.push_back(probe);
            }
            std::function<bool()> active;
            if (*feature == pipela::core::settings::kFeatReload) {
                active = [ctx]() {
                    if (ctx.state != nullptr) {
                        const auto v = ctx.state->get("reload_active");
                        if (v && std::holds_alternative<bool>(*v)) {
                            return std::get<bool>(*v);
                        }
                    }
                    const auto all = pipela::core::registry::loadAllStringValues();
                    const auto it = all.find("reload_active");
                    if (it == all.end()) {
                        return true;
                    }
                    return it->second == "true" || it->second == "1";
                };
            } else if (*feature == pipela::core::settings::kFeatAmmoRestock) {
                active = [ctx]() {
                    if (ctx.state == nullptr) {
                        return false;
                    }
                    const auto v = ctx.state->get("ammo_restock_active");
                    if (!v || !std::holds_alternative<bool>(*v)) {
                        return false;
                    }
                    return std::get<bool>(*v);
                };
            } else if (*feature == pipela::core::settings::kFeatCallMerc) {
                active = []() {
                    const auto all = pipela::core::registry::loadAllStringValues();
                    const auto it = all.find("call_merc_active");
                    if (it == all.end()) {
                        return true;
                    }
                    return it->second == "true" || it->second == "1";
                };
            } else if (*feature == pipela::core::settings::kFeatStartGame) {
                active = []() {
                    const auto all = pipela::core::registry::loadAllStringValues();
                    const auto it = all.find("start_game_launcher_enabled");
                    if (it == all.end()) {
                        return true;
                    }
                    return it->second == "true" || it->second == "1";
                };
            }
            pipela::app::widgets::applySequenceAutoscroll(page, scroll, *feature, targets, active);
        });
        scroll_timer->start();
    }

    return page;
}

const WorkerSettingsSpec* workerSettingsSpecForId(const char* panel_id) {
    for (const WorkerSettingsSpec* spec : kAllSpecs) {
        if (spec->panel_id == panel_id) {
            return spec;
        }
    }
    return nullptr;
}

}  // namespace pipela::app::panels::settings
