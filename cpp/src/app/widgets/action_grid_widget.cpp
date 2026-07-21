#include "widgets/action_grid_widget.hpp"

#include <chrono>
#include <cmath>

#include <QContextMenuEvent>
#include <QFileInfo>
#include <QFontMetricsF>
#include <QGridLayout>
#include <QIcon>
#include <QPushButton>
#include <QResizeEvent>
#include <QSizePolicy>
#include <QVBoxLayout>

#include "pipela/core/feature_trace_log.hpp"
#include "pipela/core/paths.hpp"
#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "theme/theme_engine.hpp"
#include "theme/ui_adaptive.hpp"
#include "widgets/call_merc_cooldown_button.hpp"
#include "widgets/flame_trigger_glass_button.hpp"

namespace pipela::ui::widgets {

namespace {

struct ActionSpec {
    const char* key;
    const char* label;
    const char* registry_key;
    const char* icon_file;
    const char* panel_id;
    int row;
    int col;
    int row_span;
    int col_span;
    bool specialized;
};

const ActionSpec kActions[] = {
    {"left", "LeftClick", "left_click_feature_enabled", "arrow.png", "left_click", 0, 0, 1, 1, false},
    {"right", "RightHold", "right_hold_feature_enabled", "gunfire.png", nullptr, 0, 1, 1, 1, false},
    {"flame", "Flame Trigger", "flame_trigger_feature_enabled", "ui_icon_flame.png",
     "flame_trigger", 1, 0, 1, 2, true},
    {"reload", "Reload", "reload_active", "ui_icon_reload.png", "reload", 2, 0, 1, 2, true},
    {"ride", "Ride", "ride_feature_enabled", "chopper.png", "ride", 3, 0, 1, 1, false},
    {"hp", "HP Refill", "hp_refill_feature_enabled", "ui_icon_hp_refill.png", "hp_refill", 3, 1, 1,
     1, false},
    {"ammo", "Ammo Restock", "ammo_restock_active", "ui_icon_ammo.png", "ammo_restock", 4, 0, 1, 1,
     false},
    {"merc", "Call Merc", "call_merc_active", "ui_icon_merc.png", "call_merc", 4, 1, 1, 1, true},
    {"kc", "Kill Counter", "kill_counter_enabled", "ui_icon_kill_counter.png", "kill_counter", 5, 0,
     1, 2, false},
    {"start_game", "Start Game", "start_game_launcher_active", "ui_icon_start_game.png", "start_game",
     6, 0, 1, 2, false},
};

QString iconPath(const char* filename) {
    const QString path =
        QString::fromStdString(pipela::core::assetsDir()) + QLatin1Char('/') +
        QString::fromUtf8(filename);
    if (QFileInfo::exists(path)) {
        return QFileInfo(path).absoluteFilePath();
    }
    return {};
}

QString glassStyle(bool enabled, bool emitting) {
    return pipela::ui::theme::actionGridGlassQss(enabled, emitting, 420);
}

double nowMonoSec() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

}  // namespace

ActionGridWidget::ActionGridWidget(pipela::core::state::AppState* app_state, QWidget* parent)
    : QWidget(parent), app_state_(app_state) {
    setObjectName(QString::fromUtf8("pipelaActionBtnPanel"));
    auto* outer = new QVBoxLayout(this);
    const int pad = pipela::ui::theme::scalePxH(8, 420);
    outer->setContentsMargins(pad, pad, pad, pad);
    grid_ = new QGridLayout();
    grid_->setHorizontalSpacing(pipela::ui::theme::scalePxH(8, 420));
    grid_->setVerticalSpacing(pipela::ui::theme::scalePxV(8, 740));
    grid_->setColumnStretch(0, 1);
    grid_->setColumnStretch(1, 1);
    auto* grid_row = new QHBoxLayout();
    grid_row->addStretch(1);
    grid_row->addLayout(grid_);
    grid_row->addStretch(1);
    outer->addLayout(grid_row);
    buildGrid();
    refreshToggleStyles();
    refreshActionCaptions();
    syncUniformButtonHeights();
}

void ActionGridWidget::buildGrid() {
    const int icon_side = pipela::ui::theme::scalePxH(18, 420);
    int idx = 0;
    for (const auto& spec : kActions) {
        QPushButton* btn = nullptr;
        if (QString::fromUtf8(spec.key) == QString::fromUtf8("flame")) {
            auto* fb = new FlameTriggerGlassButton(this);
            flame_btn_ = fb;
            btn = fb;
        } else if (QString::fromUtf8(spec.key) == QString::fromUtf8("reload")) {
            auto* rb = new CallMercCooldownButton(this);
            rb->setText(QString::fromUtf8(spec.label));
            reload_btn_ = rb;
            btn = rb;
        } else if (QString::fromUtf8(spec.key) == QString::fromUtf8("merc")) {
            auto* mb = new CallMercCooldownButton(this);
            mb->setText(QString::fromUtf8(spec.label));
            merc_btn_ = mb;
            btn = mb;
        } else {
            btn = new QPushButton(QString::fromUtf8(spec.label), this);
        }
        if (QString::fromUtf8(spec.key) == QString::fromUtf8("start_game")) {
            start_game_btn_ = btn;
        }
        btn->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
        const QString ipath = iconPath(spec.icon_file);
        if (!ipath.isEmpty()) {
            btn->setIcon(QIcon(ipath));
            btn->setIconSize(QSize(icon_side, icon_side));
        }
        btn->setProperty("action_key", QString::fromUtf8(spec.key));
        btn->setProperty("registry_key", QString::fromUtf8(spec.registry_key));
        if (spec.panel_id != nullptr) {
            btn->setProperty("panel_id", QString::fromUtf8(spec.panel_id));
            btn->setContextMenuPolicy(Qt::CustomContextMenu);
            connect(btn, &QWidget::customContextMenuRequested, this,
                    [this, btn](const QPoint& pos) {
                        Q_UNUSED(pos);
                        const QString panel = btn->property("panel_id").toString();
                        if (!panel.isEmpty()) {
                            emit actionToggled(QString::fromUtf8("__open__:") + panel,
                                             QString(), false);
                        }
                    });
        }
        const QString key = QString::fromUtf8(spec.key);
        connect(btn, &QPushButton::clicked, this, [this, key]() { onActionClicked(key); });
        grid_->addWidget(btn, spec.row, spec.col, spec.row_span, spec.col_span);
        buttons_[idx++] = btn;
    }
}

int ActionGridWidget::uniformButtonHeightPx() const {
    const int iz = pipela::ui::theme::scalePxH(18, width() > 0 ? width() : 420);
    QFont f = font();
    f.setWeight(QFont::DemiBold);
    f.setPointSizeF(10.0);
    const QFontMetricsF fm(f);
    const int text_h = static_cast<int>(std::ceil(fm.height()));
    const int pv = pipela::ui::theme::scalePxV(6, 740);
    const int core = std::max(iz, text_h) + 2 * pv + 2;
    return std::max(pipela::ui::theme::scalePxV(32, 740), core);
}

void ActionGridWidget::syncUniformButtonHeights() {
    const int btn_h = uniformButtonHeightPx();
    for (QPushButton* btn : buttons_) {
        if (btn != nullptr) {
            btn->setFixedHeight(btn_h);
        }
    }
}

int ActionGridWidget::featureTopBlockHeightPx() const {
    const int btn_h = uniformButtonHeightPx();
    const int grid_gap = pipela::ui::theme::scalePxV(8, 740);
    const int n_rows = 7;
    return n_rows * btn_h + std::max(0, n_rows - 1) * grid_gap + 2 * pipela::ui::theme::scalePxV(8, 740);
}

void ActionGridWidget::latchStartGameActiveLeavingLauncher() {
    // AGENT: Parity main.py bootstrap — launcher START chain must stay armed into client (intro/accept).
    if (registryBool("start_game_launcher_active", false)) {
        return;
    }
    pipela::core::registry::saveBoolValue("start_game_launcher_active", true);
    setStateBool("start_game_launcher_active", true);
}

void ActionGridWidget::resizeEvent(QResizeEvent* event) {
    QWidget::resizeEvent(event);
    syncUniformButtonHeights();
}

bool ActionGridWidget::registryBool(const char* key, bool fallback) const {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(key);
    if (it == all.end()) {
        return fallback;
    }
    return pipela::core::registry::parseBool(it->second);
}

bool ActionGridWidget::stateBool(const char* key, bool fallback) const {
    if (app_state_ == nullptr) {
        return fallback;
    }
    if (auto v = app_state_->get(key)) {
        if (const auto* b = std::get_if<bool>(&*v)) {
            return *b;
        }
    }
    return fallback;
}

void ActionGridWidget::setStateBool(const char* key, bool value) {
    if (app_state_ != nullptr) {
        app_state_->set(key, pipela::core::state::StateValue{value});
    }
}

QPushButton* ActionGridWidget::buttonForKey(const char* key) const {
    for (QPushButton* btn : buttons_) {
        if (btn != nullptr && btn->property("action_key").toString() == QString::fromUtf8(key)) {
            return btn;
        }
    }
    return nullptr;
}

QString ActionGridWidget::formatReloadHms(double elapsed_sec) {
    const int total = static_cast<int>(std::max(0.0, elapsed_sec));
    const int h = total / 3600;
    const int m = (total % 3600) / 60;
    const int s = total % 60;
    if (h > 0) {
        return QString::fromUtf8("%1:%2:%3")
            .arg(h)
            .arg(m, 2, 10, QChar('0'))
            .arg(s, 2, 10, QChar('0'));
    }
    return QString::fromUtf8("%1:%2").arg(m).arg(s, 2, 10, QChar('0'));
}

QString ActionGridWidget::flameActionCaption() const {
    int count = 0;
    double interval = 0.0;
    if (app_state_ != nullptr) {
        if (auto v = app_state_->get("flame_trigger_press_count")) {
            if (const auto* n = std::get_if<int>(&*v)) {
                count = *n;
            }
        }
        if (auto v = app_state_->get("flame_trigger_last_press_interval_sec")) {
            if (const auto* d = std::get_if<double>(&*v)) {
                interval = *d;
            }
        }
    }
    return QString::fromUtf8("Flame Trigger  : %1 : %2s").arg(count).arg(interval, 0, 'f', 2);
}

QString ActionGridWidget::reloadActionCaption() const {
    int r_cnt = 0;
    double trig_t = 0.0;
    if (app_state_ != nullptr) {
        if (auto v = app_state_->get("flame_trigger_session_reload_count")) {
            if (const auto* n = std::get_if<int>(&*v)) {
                r_cnt = *n;
            }
        }
        if (auto v = app_state_->get("flame_trigger_last_reload_trigger_time")) {
            if (const auto* d = std::get_if<double>(&*v)) {
                trig_t = *d;
            }
        }
    }
    const double elapsed = trig_t > 0.0 ? (nowMonoSec() - trig_t) : 0.0;
    return QString::fromUtf8("Reload : %1 (%2)").arg(r_cnt).arg(formatReloadHms(elapsed));
}

QString ActionGridWidget::hpRefillActionCaption() const {
    int n = 0;
    if (app_state_ != nullptr) {
        if (auto v = app_state_->get("hp_refill_trigger_total")) {
            if (const auto* i = std::get_if<int>(&*v)) {
                n = *i;
            }
        }
    }
    return QString::fromUtf8("HP Refill · %1").arg(n);
}

QString ActionGridWidget::mercActionCaption() const {
    int n = 0;
    if (app_state_ != nullptr) {
        if (auto v = app_state_->get("call_merc_loop_count")) {
            if (const auto* i = std::get_if<int>(&*v)) {
                n = *i;
            }
        }
    }
    if (n > 0) {
        return QString::fromUtf8("Call Merc · %1").arg(n);
    }
    return QString::fromUtf8("Call Merc");
}

QString ActionGridWidget::kcActionCaption() const {
    QString phase;
    if (app_state_ != nullptr) {
        if (auto v = app_state_->get("kill_counter_last_poll_phase")) {
            if (const auto* s = std::get_if<std::string>(&*v)) {
                phase = QString::fromStdString(*s);
            }
        }
    }
    if (phase.isEmpty()) {
        return QString::fromUtf8("Kill Counter");
    }
    return QString::fromUtf8("Kill Counter · %1").arg(phase);
}

bool ActionGridWidget::isStartGameTemplate1Effective() const {
    if (dock_phase_ == pipela::ui::dock::UiDockPhase::Launcher) {
        return true;
    }
    return registryBool("start_game_launcher_active", false) ||
           stateBool("start_game_launcher_active", false);
}

void ActionGridWidget::setUiDockPhase(pipela::ui::dock::UiDockPhase phase) {
    const auto prev = dock_phase_;
    if (prev == pipela::ui::dock::UiDockPhase::Launcher &&
        phase == pipela::ui::dock::UiDockPhase::Client) {
        latchStartGameActiveLeavingLauncher();
    }
    dock_phase_ = phase;
    if (start_game_btn_ != nullptr) {
        start_game_btn_->setVisible(true);
    }
    refreshToggleStyles();
    refreshActionCaptions();
    syncUniformButtonHeights();
}

void ActionGridWidget::syncCooldownGauges() {
    const double now = nowMonoSec();
    if (reload_btn_ != nullptr) {
        bool reload_on = registryBool("reload_active", true);
        double until = 0.0;
        if (app_state_ != nullptr) {
            if (auto v = app_state_->get("reload_nobullet_arm_until_mono")) {
                if (const auto* d = std::get_if<double>(&*v)) {
                    until = *d;
                }
            }
        }
        constexpr double kReloadCd = 10.0;
        if (!reload_on || until <= 0.0 || now >= until) {
            reload_btn_->setCooldownFill(0.0);
        } else {
            reload_btn_->setCooldownFill((until - now) / kReloadCd);
        }
    }
    if (merc_btn_ != nullptr) {
        double until = 0.0;
        if (app_state_ != nullptr) {
            if (auto v = app_state_->get("call_merc_arm_until_mono")) {
                if (const auto* d = std::get_if<double>(&*v)) {
                    until = *d;
                }
            }
        }
        constexpr double kMercCd = 10.0;
        if (until <= 0.0 || now >= until) {
            merc_btn_->setCooldownFill(0.0);
        } else {
            merc_btn_->setCooldownFill((until - now) / kMercCd);
        }
    }
}

void ActionGridWidget::refreshActionCaptions() {
    if (auto* fb = buttonForKey("flame")) {
        fb->setText(flameActionCaption());
    }
    if (reload_btn_ != nullptr) {
        reload_btn_->setText(reloadActionCaption());
    }
    if (merc_btn_ != nullptr) {
        merc_btn_->setText(mercActionCaption());
    }
    if (auto* hp = buttonForKey("hp")) {
        hp->setText(hpRefillActionCaption());
    }
    if (auto* kc = buttonForKey("kc")) {
        kc->setText(kcActionCaption());
    }
    if (start_game_btn_ != nullptr && start_game_btn_->isVisible()) {
        const bool on = isStartGameTemplate1Effective();
        start_game_btn_->setText(on ? QString::fromUtf8("Start Game · ON")
                                    : QString::fromUtf8("Start Game"));
    }
    if (flame_btn_ != nullptr) {
        const bool en = registryBool("flame_trigger_feature_enabled", false);
        const bool em = en && stateBool("flame_trigger_active", false);
        flame_btn_->setEmitting(em);
    }
}

void ActionGridWidget::onActionClicked(const QString& key) {
    QString registry_key;
    bool next = false;
    if (key == QString::fromUtf8("left")) {
        registry_key = QString::fromUtf8("left_click_feature_enabled");
        next = !registryBool("left_click_feature_enabled", true);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("left_click_feature_enabled", next);
        if (!next) {
            setStateBool("left_click_active", false);
            setStateBool("left_pressed", false);
        }
    } else if (key == QString::fromUtf8("right")) {
        registry_key = QString::fromUtf8("right_hold_feature_enabled");
        next = !registryBool("right_hold_feature_enabled", true);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("right_hold_feature_enabled", next);
        if (!next) {
            setStateBool("right_hold_active", false);
        }
    } else if (key == QString::fromUtf8("flame")) {
        registry_key = QString::fromUtf8("flame_trigger_feature_enabled");
        next = !registryBool("flame_trigger_feature_enabled", false);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("flame_trigger_feature_enabled", next);
        if (!next) {
            setStateBool("flame_trigger_active", false);
        }
    } else if (key == QString::fromUtf8("reload")) {
        registry_key = QString::fromUtf8("reload_active");
        next = !registryBool("reload_active", true);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("reload_active", next);
        if (!next && app_state_ != nullptr) {
            app_state_->set("reload_nobullet_arm_until_mono",
                            pipela::core::state::StateValue{0.0});
        }
    } else if (key == QString::fromUtf8("ride")) {
        registry_key = QString::fromUtf8("ride_feature_enabled");
        next = !registryBool("ride_feature_enabled", true);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("ride_feature_enabled", next);
    } else if (key == QString::fromUtf8("hp")) {
        registry_key = QString::fromUtf8("hp_refill_feature_enabled");
        next = !registryBool("hp_refill_feature_enabled", true);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("hp_refill_feature_enabled", next);
    } else if (key == QString::fromUtf8("ammo")) {
        registry_key = QString::fromUtf8("ammo_restock_active");
        next = !stateBool("ammo_restock_active", false);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("ammo_restock_active", next);
    } else if (key == QString::fromUtf8("merc")) {
        registry_key = QString::fromUtf8("call_merc_active");
        next = !stateBool("call_merc_active", false);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("call_merc_active", next);
    } else if (key == QString::fromUtf8("kc")) {
        registry_key = QString::fromUtf8("kill_counter_enabled");
        next = !registryBool("kill_counter_enabled", true);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("kill_counter_enabled", next);
    } else if (key == QString::fromUtf8("start_game")) {
        registry_key = QString::fromUtf8("start_game_launcher_active");
        next = !registryBool("start_game_launcher_active", false);
        pipela::core::registry::saveBoolValue(registry_key.toStdString(), next);
        setStateBool("start_game_launcher_active", next);
    }
    refreshToggleStyles();
    refreshActionCaptions();
    if (!key.startsWith(QString::fromUtf8("__open__:")) && !registry_key.isEmpty()) {
        pipela::core::featureTraceLog(
            "ui_action",
            std::string("key=") + key.toUtf8().constData() + " registry=" +
                registry_key.toUtf8().constData() + " next=" + (next ? "1" : "0"));
    }
    if (key.startsWith(QString::fromUtf8("__open__:"))) {
        emit actionToggled(key, QString(), false);
    } else {
        emit actionToggled(key, registry_key, next);
    }
}

QString ActionGridWidget::styleForAction(const QString& key) const {
    if (key == QString::fromUtf8("left")) {
        const bool en = registryBool("left_click_feature_enabled", true);
        return glassStyle(en, en && stateBool("left_click_active", false));
    }
    if (key == QString::fromUtf8("right")) {
        const bool en = registryBool("right_hold_feature_enabled", true);
        return glassStyle(en, en && stateBool("right_hold_active", false));
    }
    if (key == QString::fromUtf8("flame")) {
        const bool en = registryBool("flame_trigger_feature_enabled", false);
        return glassStyle(en, en && stateBool("flame_trigger_active", false));
    }
    if (key == QString::fromUtf8("reload")) {
        return glassStyle(registryBool("reload_active", true), false);
    }
    if (key == QString::fromUtf8("ride")) {
        return glassStyle(registryBool("ride_feature_enabled", true), false);
    }
    if (key == QString::fromUtf8("hp")) {
        return glassStyle(registryBool("hp_refill_feature_enabled", true), false);
    }
    if (key == QString::fromUtf8("ammo")) {
        return glassStyle(stateBool("ammo_restock_active", false), false);
    }
    if (key == QString::fromUtf8("merc")) {
        return glassStyle(stateBool("call_merc_active", false), false);
    }
    if (key == QString::fromUtf8("kc")) {
        return glassStyle(registryBool("kill_counter_enabled", true), false);
    }
    if (key == QString::fromUtf8("start_game")) {
        const bool on = isStartGameTemplate1Effective();
        return glassStyle(on, on);
    }
    return glassStyle(false, false);
}

void ActionGridWidget::refreshToggleStyles() {
    for (const auto& spec : kActions) {
        if (QPushButton* btn = buttonForKey(spec.key)) {
            btn->setStyleSheet(styleForAction(QString::fromUtf8(spec.key)));
        }
    }
}

void ActionGridWidget::contextMenuEvent(QContextMenuEvent* event) { Q_UNUSED(event); }

}  // namespace pipela::ui::widgets
