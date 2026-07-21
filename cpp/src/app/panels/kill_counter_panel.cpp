#include "panels/kill_counter_panel.hpp"

#include <chrono>

#include <cmath>

#include <QEvent>
#include <QFrame>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QProgressBar>
#include <QPushButton>
#include <QResizeEvent>
#include <QTimer>
#include <QVBoxLayout>

#include <variant>

#include "overlays/kill_counter_viewport_metrics.hpp"
#include "overlays/kill_counter_viewport_typography.hpp"
#include "panels/kill_counter_bar_chart_widget.hpp"
#include "panels/kill_counter_daily_calendar_widget.hpp"
#include "panels/kill_counter_tier_table_dialog.hpp"
#include "pipela/core/kill_counter/goal_display.hpp"
#include "pipela/core/kill_counter/session.hpp"
#include "pipela/core/kill_counter/stats_store.hpp"
#include "pipela/core/kill_counter/tier_colors.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "theme/theme_engine.hpp"
#include "theme/ui_adaptive.hpp"
#include "widgets/kill_counter_region_toolbar.hpp"

namespace pipela::ui::panels {

namespace {

QWidget* makeSectionHeader(const QString& title, QWidget* parent) {
    auto* row = new QWidget(parent);
    auto* lay = new QHBoxLayout(row);
    lay->setContentsMargins(0, pipela::ui::theme::scalePxV(4, 720), 0,
                            pipela::ui::theme::scalePxV(2, 720));
    lay->setSpacing(pipela::ui::theme::scalePxH(6, 420));
    auto* accent = new QFrame(row);
    accent->setFixedSize(3, pipela::ui::theme::scalePxV(12, 720));
    accent->setStyleSheet(pipela::ui::theme::killCounterSectionAccentBarQss());
    auto* lbl = new QLabel(title, row);
    lbl->setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
    lbl->setStyleSheet(pipela::ui::theme::textQss("FG_SECONDARY", 10, 700));
    lay->addWidget(accent);
    lay->addWidget(lbl, 1);
    return row;
}

QLabel* makeStatValue(const QString& initial, QWidget* parent) {
    auto* lbl = new QLabel(initial, parent);
    lbl->setAlignment(Qt::AlignCenter);
    lbl->setStyleSheet(pipela::ui::theme::textQss("FG", 14, 700));
    return lbl;
}

QLabel* makeStatCaption(const QString& text, QWidget* parent) {
    auto* lbl = new QLabel(text, parent);
    lbl->setAlignment(Qt::AlignCenter);
    lbl->setStyleSheet(pipela::ui::theme::textQss("FG_MUTED", 9, 500));
    return lbl;
}

QWidget* makeStatChip(const QString& caption, QLabel** value_out, QWidget* parent) {
    auto* chip = new QFrame(parent);
    chip->setObjectName(QString::fromUtf8("pipelaKcStatChip"));
    chip->setStyleSheet(pipela::ui::theme::killCounterStatChipQss());
    auto* lay = new QVBoxLayout(chip);
    const int pad = pipela::ui::theme::scalePxV(4, 720);
    lay->setContentsMargins(pad, pad, pad, pad);
    lay->setSpacing(2);
    *value_out = makeStatValue(QString::fromUtf8("—"), chip);
    lay->addWidget(*value_out);
    lay->addWidget(makeStatCaption(caption, chip));
    return chip;
}

QFrame* makeGoalBlock(QWidget* parent) {
    auto* block = new QFrame(parent);
    block->setObjectName(QString::fromUtf8("pipelaKcGoalBlock"));
    block->setStyleSheet(pipela::ui::theme::killCounterGoalBlockQss());
    return block;
}

QString stateString(pipela::core::state::AppState* state, const char* key) {
    if (state == nullptr) {
        return {};
    }
    const auto v = state->get(key);
    if (!v || !std::holds_alternative<std::string>(*v)) {
        return {};
    }
    return QString::fromStdString(std::get<std::string>(*v));
}

void applyGoalLineTierColor(QLabel* label, const std::string& rank_title, const QString& pt_css) {
    if (label == nullptr) {
        return;
    }
    QString color = QString::fromUtf8("#c8e6d0");
    if (auto hex = pipela::core::kill_counter::tierFgHexForRankTitle(rank_title)) {
        color = QString::fromStdString(*hex);
    }
    label->setStyleSheet(
        QString::fromUtf8("color: %1; font-size: %2; font-weight: 600;").arg(color, pt_css));
}

void applyGoalBarTierStyle(QProgressBar* bar, const std::string& rank_title) {
    if (bar == nullptr) {
        return;
    }
    QString chunk = QString::fromUtf8("#5a9a6a");
    if (auto hex = pipela::core::kill_counter::tierFgHexForRankTitle(rank_title)) {
        chunk = QString::fromStdString(*hex);
    }
    bar->setStyleSheet(pipela::ui::theme::killCounterProgressQss(chunk));
}

QWidget* makeHubCard(QWidget* parent) {
    auto* fr = new QFrame(parent);
    fr->setStyleSheet(pipela::ui::theme::killCounterHubCardQss());
    return fr;
}

void addSectionHeader(QVBoxLayout* lay, const QString& text, QWidget* parent) {
    if (lay != nullptr) {
        lay->addWidget(makeSectionHeader(text, parent));
    }
}

void flashRecentValue(QLabel* label) {
    if (label == nullptr) {
        return;
    }
    label->setStyleSheet(
        QString::fromUtf8("color: %1; font-size: 14px; font-weight: 700; background: %2; "
                          "border-radius: %3px;")
            .arg(pipela::ui::theme::color("FG"), pipela::ui::theme::color("ACCENT_SOFT"),
                 QString::number(pipela::ui::theme::radiusPx("RADIUS_SM", 8) - 2)));
    QTimer::singleShot(420, label, [label]() {
        label->setStyleSheet(pipela::ui::theme::textQss("FG", 14, 700));
    });
}

QString formatElapsed(double sec) {
    if (sec < 0.0) {
        sec = 0.0;
    }
    const int total_cs = static_cast<int>(std::lround(sec * 100.0));
    const int cs = total_cs % 100;
    const int total_s = total_cs / 100;
    const int s = total_s % 60;
    const int total_m = total_s / 60;
    const int m = total_m % 60;
    const int h = total_m / 60;
    if (h > 0) {
        return QString::fromUtf8("%1:%2:%3.%4")
            .arg(h)
            .arg(m, 2, 10, QChar('0'))
            .arg(s, 2, 10, QChar('0'))
            .arg(cs, 2, 10, QChar('0'));
    }
    return QString::fromUtf8("%1:%2.%3")
        .arg(m, 2, 10, QChar('0'))
        .arg(s, 2, 10, QChar('0'))
        .arg(cs, 2, 10, QChar('0'));
}

}  // namespace

KillCounterPanel::KillCounterPanel(QWidget* parent) : QWidget(parent) {
    setProperty("_kc_vw", kc_vw_);
    setProperty("_kc_vh", kc_vh_);
    buildUi();
    startTimers();
    pipela::core::kill_counter::statsEnsureLoaded();
}

void KillCounterPanel::setAppState(pipela::core::state::AppState* state) { state_ = state; }

void KillCounterPanel::setOverlayController(
    pipela::ui::overlays::TemplateOverlayController* controller) {
    overlay_controller_ = controller;
    if (!toolbar_attached_ && bottom_bar_ != nullptr && overlay_controller_ != nullptr) {
        pipela::ui::overlays::attachKillCounterRegionToolbar(bottom_bar_, overlay_controller_);
        toolbar_attached_ = true;
    }
}

void KillCounterPanel::buildUi() {
    const int gap = pipela::ui::theme::scalePxV(6, 720);
    const int card_pad = pipela::ui::theme::scalePxH(8, 420);
    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(4, 4, 4, 4);
    root->setSpacing(gap);

    // —— Hero: session kills + rolling stats ——
    sec_hero_ = new QWidget(this);
    auto* hero_outer = new QVBoxLayout(sec_hero_);
    hero_outer->setContentsMargins(0, 0, 0, 0);
    hero_outer->setSpacing(gap);
    auto* hero_card = new QFrame(sec_hero_);
    hero_card->setObjectName(QString::fromUtf8("pipelaKcHeroCard"));
    hero_card->setStyleSheet(pipela::ui::theme::killCounterHeroCardQss());
    auto* hero_card_lay = new QVBoxLayout(hero_card);
    hero_card_lay->setContentsMargins(card_pad, card_pad, card_pad, card_pad);
    hero_card_lay->setSpacing(pipela::ui::theme::scalePxV(4, 720));
    hero_caption_ = new QLabel(QString::fromUtf8("현재 킬"), hero_card);
    hero_caption_->setAlignment(Qt::AlignCenter);
    hero_caption_->setStyleSheet(pipela::ui::theme::textQss("FG_SECONDARY", 10, 600));
    hero_label_ = new QLabel(QString::fromUtf8("—"), hero_card);
    hero_label_->setAlignment(Qt::AlignCenter);
    hero_label_->setStyleSheet(pipela::ui::theme::textQss("ACCENT", 32, 800));
    hero_card_lay->addWidget(hero_caption_);
    hero_card_lay->addWidget(hero_label_);
    auto* stats_row = new QHBoxLayout();
    stats_row->setSpacing(pipela::ui::theme::scalePxH(6, 420));
    stats_row->addWidget(makeStatChip(QString::fromUtf8("1시간"), &recent_1h_, hero_card), 1);
    stats_row->addWidget(makeStatChip(QString::fromUtf8("6시간"), &recent_6h_, hero_card), 1);
    stats_row->addWidget(makeStatChip(QString::fromUtf8("24시간"), &recent_24h_, hero_card), 1);
    stats_row->addWidget(makeStatChip(QString::fromUtf8("시간당"), &recent_kph_, hero_card), 1);
    hero_card_lay->addLayout(stats_row);
    hero_outer->addWidget(hero_card, 1);
    root->addWidget(sec_hero_);

    // —— Graph ——
    sec_graph_ = new QWidget(this);
    auto* graph_lay = new QVBoxLayout(sec_graph_);
    graph_lay->setContentsMargins(0, 0, 0, 0);
    graph_lay->setSpacing(gap);
    addSectionHeader(graph_lay, QString::fromUtf8("킬 추이"), sec_graph_);
    auto* graph_card = makeHubCard(sec_graph_);
    auto* graph_card_lay = new QVBoxLayout(graph_card);
    graph_card_lay->setContentsMargins(card_pad, card_pad, card_pad, card_pad);
    bar_chart_ = new KillCounterBarChartWidget(graph_card);
    graph_card_lay->addWidget(bar_chart_, 1);
    graph_lay->addWidget(graph_card, 1);
    root->addWidget(sec_graph_);

    // —— Goals: stacked blocks ——
    sec_goal_ = new QWidget(this);
    auto* goal_lay = new QVBoxLayout(sec_goal_);
    goal_lay->setContentsMargins(0, 0, 0, 0);
    goal_lay->setSpacing(gap);
    addSectionHeader(goal_lay, QString::fromUtf8("다음 목표"), sec_goal_);
    auto* goal_card = makeHubCard(sec_goal_);
    auto* goal_card_lay = new QVBoxLayout(goal_card);
    goal_card_lay->setContentsMargins(card_pad, card_pad, card_pad, card_pad);
    goal_card_lay->setSpacing(pipela::ui::theme::scalePxV(8, 720));

    auto* tier_block = makeGoalBlock(goal_card);
    auto* tier_lay = new QVBoxLayout(tier_block);
    tier_lay->setContentsMargins(8, 8, 8, 8);
    tier_lay->setSpacing(4);
    auto* tier_tag = new QLabel(QString::fromUtf8("등급"), tier_block);
    tier_tag->setStyleSheet(pipela::ui::theme::textQss("FG_MUTED", 9, 600));
    goal_tier_line_ = new QLabel(QString::fromUtf8("—"), tier_block);
    goal_tier_line_->setWordWrap(true);
    goal_tier_line_->setStyleSheet(pipela::ui::theme::textQss("SUCCESS", 11, 600));
    goal_tier_line_->setCursor(Qt::PointingHandCursor);
    goal_tier_line_->installEventFilter(this);
    goal_tier_bar_ = new QProgressBar(tier_block);
    goal_tier_bar_->setRange(0, 100);
    goal_tier_bar_->setTextVisible(false);
    goal_tier_bar_->setFixedHeight(6);
    goal_tier_rem_ = new QLabel(QString::fromUtf8("—"), tier_block);
    goal_tier_rem_->setStyleSheet(pipela::ui::theme::textQss("FG_SECONDARY", 9, 500));
    tier_lay->addWidget(tier_tag);
    tier_lay->addWidget(goal_tier_line_);
    tier_lay->addWidget(goal_tier_bar_);
    tier_lay->addWidget(goal_tier_rem_);

    auto* choin_block = makeGoalBlock(goal_card);
    auto* choin_lay = new QVBoxLayout(choin_block);
    choin_lay->setContentsMargins(8, 8, 8, 8);
    choin_lay->setSpacing(4);
    auto* choin_tag = new QLabel(QString::fromUtf8("킬작 졸업"), choin_block);
    choin_tag->setStyleSheet(pipela::ui::theme::textQss("FG_MUTED", 9, 600));
    goal_choin_line_ = new QLabel(QString::fromUtf8("—"), choin_block);
    goal_choin_line_->setWordWrap(true);
    goal_choin_line_->setStyleSheet(pipela::ui::theme::textQss("SUCCESS", 11, 600));
    goal_choin_bar_ = new QProgressBar(choin_block);
    goal_choin_bar_->setRange(0, 100);
    goal_choin_bar_->setTextVisible(false);
    goal_choin_bar_->setFixedHeight(6);
    goal_choin_rem_ = new QLabel(QString::fromUtf8("—"), choin_block);
    goal_choin_rem_->setStyleSheet(pipela::ui::theme::textQss("FG_SECONDARY", 9, 500));
    choin_lay->addWidget(choin_tag);
    choin_lay->addWidget(goal_choin_line_);
    choin_lay->addWidget(goal_choin_bar_);
    choin_lay->addWidget(goal_choin_rem_);

    goal_card_lay->addWidget(tier_block);
    goal_card_lay->addWidget(choin_block);
    goal_lay->addWidget(goal_card, 1);
    root->addWidget(sec_goal_);

    // —— Lap timer ——
    sec_lap_ = new QWidget(this);
    auto* lap_lay = new QVBoxLayout(sec_lap_);
    lap_lay->setContentsMargins(0, 0, 0, 0);
    lap_lay->setSpacing(gap);
    addSectionHeader(lap_lay, QString::fromUtf8("랩 타이머"), sec_lap_);
    auto* lap_card = makeHubCard(sec_lap_);
    auto* lap_card_lay = new QVBoxLayout(lap_card);
    lap_card_lay->setContentsMargins(card_pad, card_pad, card_pad, card_pad);
    lap_card_lay->setSpacing(pipela::ui::theme::scalePxV(6, 720));
    lap_elapsed_ = new QLabel(QString::fromUtf8("00:00.00"), lap_card);
    lap_elapsed_->setAlignment(Qt::AlignCenter);
    lap_elapsed_->setStyleSheet(pipela::ui::theme::textQss("ACCENT", 18, 700));
    lap_card_lay->addWidget(lap_elapsed_);
    auto* lap_grid = new QGridLayout();
    lap_grid->setHorizontalSpacing(pipela::ui::theme::scalePxH(6, 420));
    lap_grid->setVerticalSpacing(pipela::ui::theme::scalePxV(6, 720));
    lap_grid->addWidget(makeStatChip(QString::fromUtf8("1시간"), &lap_1h_, lap_card), 0, 0);
    lap_grid->addWidget(makeStatChip(QString::fromUtf8("6시간"), &lap_6h_, lap_card), 0, 1);
    lap_grid->addWidget(makeStatChip(QString::fromUtf8("24시간"), &lap_24h_, lap_card), 1, 0);
    lap_grid->addWidget(makeStatChip(QString::fromUtf8("누적"), &lap_total_, lap_card), 1, 1);
    lap_card_lay->addLayout(lap_grid);
    auto* lap_btn_row = new QHBoxLayout();
    lap_btn_row->setSpacing(pipela::ui::theme::scalePxH(6, 420));
    lap_main_btn_ = new QPushButton(QString::fromUtf8("시작"), lap_card);
    lap_clear_btn_ = new QPushButton(QString::fromUtf8("초기화"), lap_card);
    lap_end_btn_ = new QPushButton(QString::fromUtf8("종료"), lap_card);
    lap_main_btn_->setStyleSheet(pipela::ui::theme::killCounterPrimaryButtonQss());
    lap_clear_btn_->setStyleSheet(pipela::ui::theme::killCounterGhostButtonQss());
    lap_end_btn_->setStyleSheet(pipela::ui::theme::killCounterGhostButtonQss());
    lap_btn_row->addWidget(lap_main_btn_, 2);
    lap_btn_row->addWidget(lap_clear_btn_, 1);
    lap_btn_row->addWidget(lap_end_btn_, 1);
    lap_card_lay->addLayout(lap_btn_row);
    lap_lay->addWidget(lap_card, 1);
    connect(lap_main_btn_, &QPushButton::clicked, this, [this]() {
        if (lapStartTs() <= 0.0) {
            setLapStartTs(std::chrono::duration<double>(
                              std::chrono::system_clock::now().time_since_epoch())
                              .count());
            lap_paused_ = false;
            if (lap_main_btn_ != nullptr) {
                lap_main_btn_->setText(QString::fromUtf8("일시정지"));
            }
            return;
        }
        lap_paused_ = !lap_paused_;
        if (lap_main_btn_ != nullptr) {
            lap_main_btn_->setText(lap_paused_ ? QString::fromUtf8("재개")
                                               : QString::fromUtf8("일시정지"));
        }
    });
    connect(lap_clear_btn_, &QPushButton::clicked, this, [this]() { clearLap(); });
    connect(lap_end_btn_, &QPushButton::clicked, this, [this]() { clearLap(); });
    root->addWidget(sec_lap_);

    // —— Calendar ——
    sec_calendar_ = new QWidget(this);
    auto* cal_lay = new QVBoxLayout(sec_calendar_);
    cal_lay->setContentsMargins(0, 0, 0, 0);
    cal_lay->setSpacing(gap);
    addSectionHeader(cal_lay, QString::fromUtf8("일별 기록"), sec_calendar_);
    auto* cal_card = makeHubCard(sec_calendar_);
    auto* cal_card_lay = new QVBoxLayout(cal_card);
    cal_card_lay->setContentsMargins(4, 4, 4, 4);
    calendar_ = new KillCounterDailyCalendarWidget(cal_card);
    cal_card_lay->addWidget(calendar_, 1);
    cal_lay->addWidget(cal_card, 1);
    root->addWidget(sec_calendar_);

    // —— Footer: ROI tools + reset ——
    sec_bottom_ = new QWidget(this);
    auto* bottom_outer = new QVBoxLayout(sec_bottom_);
    bottom_outer->setContentsMargins(0, 0, 0, 0);
    bottom_outer->setSpacing(gap);
    auto* bottom_host = new QWidget(sec_bottom_);
    bottom_bar_ = new QHBoxLayout(bottom_host);
    bottom_bar_->setSpacing(pipela::ui::theme::scalePxH(6, 420));
    bottom_bar_->setContentsMargins(0, 0, 0, 0);
    bottom_outer->addWidget(bottom_host);
    session_reset_btn_ = new QPushButton(QString::fromUtf8("세션 초기화"), sec_bottom_);
    session_reset_btn_->setToolTip(
        QString::fromUtf8("세션 누적 킬 표시·기준을 지웁니다. 저장된 영구 통계는 유지됩니다."));
    session_reset_btn_->setStyleSheet(pipela::ui::theme::killCounterGhostButtonQss());
    stats_reset_btn_ = new QPushButton(QString::fromUtf8("전체 삭제"), sec_bottom_);
    stats_reset_btn_->setStyleSheet(pipela::ui::theme::killCounterDangerButtonQss(true));
    stats_reset_btn_->setToolTip(
        QString::fromUtf8("그래프·캘린더·랩 등 저장된 킬 통계와 세션·OCR 표시를 모두 삭제합니다."));
    bottom_bar_->addStretch(1);
    bottom_bar_->addWidget(session_reset_btn_);
    bottom_bar_->addWidget(stats_reset_btn_);
    connect(session_reset_btn_, &QPushButton::clicked, this, [this]() {
        if (state_ != nullptr) {
            pipela::core::kill_counter::resetSessionKills(*state_);
            state_->set("kill_counter_last_progress",
                        pipela::core::state::StateValue{std::string{}});
        }
    });
    connect(stats_reset_btn_, &QPushButton::clicked, this, [this]() {
        pipela::core::kill_counter::statsResetAll();
        if (state_ != nullptr) {
            pipela::core::kill_counter::resetSessionKills(*state_);
            state_->set("kill_counter_last_progress",
                        pipela::core::state::StateValue{std::string{}});
            state_->set("kill_counter_last_poll_phase",
                        pipela::core::state::StateValue{std::string{}});
        }
        if (bar_chart_ != nullptr) {
            bar_chart_->refresh();
        }
        if (calendar_ != nullptr) {
            calendar_->refresh();
        }
        tickSlow();
    });
    root->addWidget(sec_bottom_);
    refreshViewportTypography();
}

void KillCounterPanel::startTimers() {
    fast_timer_ = new QTimer(this);
    slow_timer_ = new QTimer(this);
    connect(fast_timer_, &QTimer::timeout, this, &KillCounterPanel::tickFast);
    connect(slow_timer_, &QTimer::timeout, this, &KillCounterPanel::tickSlow);
    fast_timer_->start(200);
    slow_timer_->start(350);
}

void KillCounterPanel::resizeEvent(QResizeEvent* event) {
    QWidget::resizeEvent(event);
    scheduleViewportLayoutRefresh();
}

void KillCounterPanel::scheduleViewportLayoutRefresh() {
    if (layout_refresh_pending_) {
        return;
    }
    layout_refresh_pending_ = true;
    QTimer::singleShot(0, this, [this]() {
        layout_refresh_pending_ = false;
        refreshViewportLayout();
    });
}

void KillCounterPanel::refreshViewportLayout() {
    const auto wh = pipela::app::overlays::kc_metrics::kcViewportWhValid(width(), height());
    const int new_vw = wh.first;
    const int new_vh = wh.second;
    if (new_vw == kc_vw_ && new_vh == kc_vh_ && last_section_layout_h_ == contentsRect().height()) {
        return;
    }
    kc_vw_ = new_vw;
    kc_vh_ = new_vh;
    setProperty("_kc_vw", kc_vw_);
    setProperty("_kc_vh", kc_vh_);

    const int total_h = contentsRect().height();
    if (total_h > 8 && total_h != last_section_layout_h_) {
        applySectionHeights();
        last_section_layout_h_ = total_h;
    }

    const double vs =
        pipela::app::overlays::kc_metrics::kcViewportHeightScale(kc_vw_, kc_vh_);
    if (std::abs(vs - last_typography_vs_) > 0.015) {
        last_typography_vs_ = vs;
        refreshViewportTypography();
    }
}

QString KillCounterPanel::kcSpt(double design_pt) const {
  const double vs =
      pipela::app::overlays::kc_metrics::kcViewportHeightScale(kc_vw_, kc_vh_);
  return pipela::app::overlays::kc_typography::kcViewportSptV(vs, design_pt);
}

void KillCounterPanel::refreshViewportTypography() {
    const double vs =
        pipela::app::overlays::kc_metrics::kcViewportHeightScale(kc_vw_, kc_vh_);
    const auto [hero_hi, hero_lo] =
        std::make_pair(pipela::app::overlays::kc_typography::heroProgPtHi(vs),
                       pipela::app::overlays::kc_typography::heroProgPtLo(vs));
    const auto [primary_hi, primary_lo] =
        pipela::app::overlays::kc_typography::recentRollValuePts(vs);
    const auto [goal_hi, goal_lo] =
        pipela::app::overlays::kc_typography::goalPlainSubvalPts(vs);
    const auto [caption_hi, caption_lo] =
        pipela::app::overlays::kc_typography::lapSheetCaptionPts(vs);
    const auto [btn_hi, btn_lo] =
        pipela::app::overlays::kc_typography::gaugeOverlayPctPts(vs);
    Q_UNUSED(hero_lo);
    Q_UNUSED(primary_lo);
    Q_UNUSED(goal_lo);
    Q_UNUSED(caption_lo);
    Q_UNUSED(btn_lo);
    if (hero_caption_ != nullptr) {
        hero_caption_->setStyleSheet(
            QString::fromUtf8("color: %1; font-size: %2; font-weight: 600;")
                .arg(pipela::ui::theme::color("FG_SECONDARY"),
                     QString::number(caption_hi, 'g', 4) + QString::fromUtf8("pt")));
    }
    if (hero_label_ != nullptr) {
        hero_label_->setStyleSheet(
            QString::fromUtf8("color: %1; font-size: %2; font-weight: 800;")
                .arg(pipela::ui::theme::color("ACCENT"))
                .arg(pipela::app::overlays::kc_typography::kcViewportSptV(vs, 32.0)));
    }
    const QString value_qss =
        QString::fromUtf8("color: %1; font-size: %2; font-weight: 700;")
            .arg(pipela::ui::theme::color("FG"),
                 QString::number(hero_hi, 'g', 4) + QString::fromUtf8("pt"));
    const QString caption_qss =
        QString::fromUtf8("color: %1; font-size: %2;")
            .arg(pipela::ui::theme::color("FG_MUTED"),
                 QString::number(caption_hi, 'g', 4) + QString::fromUtf8("pt"));
    for (QLabel* lbl : {recent_1h_, recent_6h_, recent_24h_, recent_kph_, lap_1h_, lap_6h_, lap_24h_,
                        lap_total_}) {
        if (lbl != nullptr) {
            lbl->setStyleSheet(value_qss);
        }
    }
    if (goal_tier_line_ != nullptr) {
        goal_tier_line_->setStyleSheet(
            QString::fromUtf8("color: %1; font-size: %2;")
                .arg(pipela::ui::theme::color("SUCCESS"),
                     QString::number(goal_hi * 0.55, 'g', 4) + QString::fromUtf8("pt")));
    }
    if (goal_choin_line_ != nullptr) {
        goal_choin_line_->setStyleSheet(
            QString::fromUtf8("color: %1; font-size: %2;")
                .arg(pipela::ui::theme::color("SUCCESS"),
                     QString::number(goal_hi * 0.55, 'g', 4) + QString::fromUtf8("pt")));
    }
    if (goal_tier_rem_ != nullptr || goal_choin_rem_ != nullptr) {
        const QString rem_qss =
            QString::fromUtf8("color: %1; font-size: %2;")
                .arg(pipela::ui::theme::color("FG_SECONDARY"),
                     QString::number(caption_hi, 'g', 4) + QString::fromUtf8("pt"));
        if (goal_tier_rem_ != nullptr) {
            goal_tier_rem_->setStyleSheet(rem_qss);
        }
        if (goal_choin_rem_ != nullptr) {
            goal_choin_rem_->setStyleSheet(rem_qss);
        }
    }
    if (lap_elapsed_ != nullptr) {
        lap_elapsed_->setStyleSheet(
            QString::fromUtf8("color: %1; font-size: %2; font-weight: 700;")
                .arg(pipela::ui::theme::color("ACCENT"),
                     QString::number(primary_hi, 'g', 4) + QString::fromUtf8("pt")));
    }
    const QString btn_pt = QString::number(btn_hi, 'g', 4) + QString::fromUtf8("pt");
    if (lap_main_btn_ != nullptr) {
        lap_main_btn_->setStyleSheet(pipela::ui::theme::killCounterPrimaryButtonQss(btn_pt));
    }
    if (lap_clear_btn_ != nullptr) {
        lap_clear_btn_->setStyleSheet(pipela::ui::theme::killCounterGhostButtonQss(btn_pt));
    }
    if (lap_end_btn_ != nullptr) {
        lap_end_btn_->setStyleSheet(pipela::ui::theme::killCounterGhostButtonQss(btn_pt));
    }
    if (session_reset_btn_ != nullptr) {
        session_reset_btn_->setStyleSheet(
            pipela::ui::theme::killCounterGhostButtonQss(btn_pt));
    }
    if (stats_reset_btn_ != nullptr) {
        stats_reset_btn_->setStyleSheet(
            pipela::ui::theme::killCounterDangerButtonQss(true, btn_pt));
    }
}

void KillCounterPanel::applySectionHeights() {
    const int total_h = contentsRect().height();
    if (total_h <= 8) {
        return;
    }
    struct SectionRow {
        QWidget* widget;
        double ratio;
    };
    const SectionRow rows[] = {
        {sec_hero_, 2.2},    {sec_graph_, 2.0},   {sec_goal_, 2.2},
        {sec_lap_, 2.2},     {sec_calendar_, 2.0}, {sec_bottom_, 0.6},
    };
    constexpr double kDenom = 11.2;
    constexpr int kCalendarIdx = 4;
    const double unit = static_cast<double>(total_h) / kDenom;
    int heights[6]{};
    int sum = 0;
    for (int i = 0; i < 6; ++i) {
        heights[i] = std::max(1, static_cast<int>(std::lround(unit * rows[i].ratio)));
        sum += heights[i];
    }
    const int diff = total_h - sum;
    if (diff != 0) {
        heights[kCalendarIdx] = std::max(1, heights[kCalendarIdx] + diff);
    }
    for (int i = 0; i < 6; ++i) {
        if (rows[i].widget != nullptr) {
            rows[i].widget->setFixedHeight(heights[i]);
        }
    }
}

double KillCounterPanel::lapStartTs() const {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find("kill_counter_lap_start_ts");
    if (it == all.end() || it->second.empty()) {
        return 0.0;
    }
    try {
        return std::stod(it->second);
    } catch (...) {
        return 0.0;
    }
}

void KillCounterPanel::setLapStartTs(double ts) {
    pipela::core::registry::saveStringValue("kill_counter_lap_start_ts", std::to_string(ts));
}

void KillCounterPanel::clearLap() {
    pipela::core::registry::saveStringValue("kill_counter_lap_start_ts", std::string{});
    lap_paused_ = false;
    if (lap_main_btn_ != nullptr) {
        lap_main_btn_->setText(QString::fromUtf8("시작"));
    }
}

void KillCounterPanel::tickFast() {
    const QString progress = stateString(state_, "kill_counter_last_progress");
    if (hero_label_ != nullptr) {
        hero_label_->setText(QString::fromStdString(
            pipela::core::kill_counter::panelProgressValueText(progress.toStdString())));
    }
    const double lap_ts = lapStartTs();
    if (lap_ts > 0.0 && lap_elapsed_ != nullptr) {
        const double now = std::chrono::duration<double>(
                               std::chrono::system_clock::now().time_since_epoch())
                               .count();
        lap_elapsed_->setText(formatElapsed(now - lap_ts));
    } else if (lap_elapsed_ != nullptr) {
        lap_elapsed_->setText(QString::fromUtf8("—"));
    }
}

void KillCounterPanel::tickSlow() {
    pipela::core::kill_counter::statsEnsureLoaded();
    const int k1 = pipela::core::kill_counter::statsSumLastSeconds(3600.0);
    const int k6 = pipela::core::kill_counter::statsSumLastSeconds(21600.0);
    const int k24 = pipela::core::kill_counter::statsSumLastSeconds(86400.0);
    const double kph = k24 / 24.0;
    if (recent_1h_ != nullptr) {
        recent_1h_->setText(QString::fromStdString(pipela::core::kill_counter::formatIntComma(k1)));
        if (k1 > last_recent_k1_) {
            flashRecentValue(recent_1h_);
        }
    }
    last_recent_k1_ = k1;
    if (recent_6h_ != nullptr) {
        recent_6h_->setText(QString::fromStdString(pipela::core::kill_counter::formatIntComma(k6)));
    }
    if (recent_24h_ != nullptr) {
        recent_24h_->setText(
            QString::fromStdString(pipela::core::kill_counter::formatIntComma(k24)));
    }
    if (recent_kph_ != nullptr) {
        recent_kph_->setText(QString::number(kph, 'f', 1));
    }

    const auto n1 = pipela::core::kill_counter::progressN1FromOcr(
        stateString(state_, "kill_counter_last_progress").toStdString());
    if (n1) {
        const auto tier_st = pipela::core::kill_counter::tierStateForN1(*n1);
        const QString goal_pt = kcSpt(11.0);
        if (goal_tier_line_ != nullptr) {
            goal_tier_line_->setText(
                QString::fromStdString(pipela::core::kill_counter::goalTransitionLine(*n1)));
            if (tier_st) {
                applyGoalLineTierColor(goal_tier_line_, tier_st->title, goal_pt);
            }
        }
        if (goal_choin_line_ != nullptr) {
            goal_choin_line_->setText(
                QString::fromStdString(pipela::core::kill_counter::goalChoinTransitionLine(*n1)));
            if (tier_st) {
                applyGoalLineTierColor(goal_choin_line_, tier_st->title, goal_pt);
            }
        }
        if (goal_tier_rem_ != nullptr) {
            goal_tier_rem_->setText(
                QString::fromStdString(pipela::core::kill_counter::goalRemLine(*n1)));
        }
        if (goal_choin_rem_ != nullptr) {
            goal_choin_rem_->setText(
                QString::fromStdString(pipela::core::kill_counter::goalRemLine(*n1)));
        }
        if (auto pct = pipela::core::kill_counter::goalTierPctFloat(*n1)) {
            if (goal_tier_bar_ != nullptr) {
                goal_tier_bar_->setValue(static_cast<int>(std::lround(*pct)));
                if (tier_st) {
                    applyGoalBarTierStyle(goal_tier_bar_, tier_st->title);
                }
            }
            if (goal_choin_bar_ != nullptr) {
                goal_choin_bar_->setValue(static_cast<int>(std::lround(*pct)));
                if (tier_st) {
                    applyGoalBarTierStyle(goal_choin_bar_, tier_st->title);
                }
            }
        }
    }

    const double lap_ts = lapStartTs();
    if (lap_ts > 0.0) {
        if (lap_main_btn_ != nullptr && lap_main_btn_->text() == QString::fromUtf8("시작")) {
            lap_main_btn_->setText(QString::fromUtf8("일시정지"));
        }
        if (lap_1h_ != nullptr) {
            lap_1h_->setText(QString::fromStdString(pipela::core::kill_counter::formatIntComma(
                pipela::core::kill_counter::statsSumLapInLastSeconds(lap_ts, 3600.0))));
        }
        if (lap_6h_ != nullptr) {
            lap_6h_->setText(QString::fromStdString(pipela::core::kill_counter::formatIntComma(
                pipela::core::kill_counter::statsSumLapInLastSeconds(lap_ts, 21600.0))));
        }
        if (lap_24h_ != nullptr) {
            lap_24h_->setText(QString::fromStdString(pipela::core::kill_counter::formatIntComma(
                pipela::core::kill_counter::statsSumLapInLastSeconds(lap_ts, 86400.0))));
        }
        if (lap_total_ != nullptr) {
            lap_total_->setText(QString::fromStdString(pipela::core::kill_counter::formatIntComma(
                pipela::core::kill_counter::statsSumLapTotal(lap_ts))));
        }
    }

    if (bar_chart_ != nullptr) {
        bar_chart_->refresh();
    }
    if (calendar_ != nullptr) {
        calendar_->refresh();
    }
}

bool KillCounterPanel::eventFilter(QObject* watched, QEvent* event) {
    if (watched == goal_tier_line_ && event->type() == QEvent::MouseButtonRelease) {
        showKillCounterTierTableDialog(this);
        return true;
    }
    return QWidget::eventFilter(watched, event);
}

}  // namespace pipela::ui::panels
