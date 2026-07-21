#include "panels/settings_hub.hpp"

#include <Qt>

#include <QFrame>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QScrollArea>
#include <QSizePolicy>
#include <QStackedWidget>
#include <QVBoxLayout>

#include "panels/settings/panel_factory.hpp"
#include "panels/settings_hub_entries.hpp"
#include "panels/settings_panel_defs.hpp"
#include "theme/app_shell_styles.hpp"
#include "theme/ui_adaptive.hpp"

namespace pipela::ui::panels {

namespace {

bool panelDefListed(const std::vector<SettingsPanelDef>& defs, const char* panel_id) {
    for (const auto& def : defs) {
        if (def.id == panel_id) {
            return true;
        }
    }
    return false;
}

}  // namespace

SettingsHubWidget::SettingsHubWidget(
    const pipela::app::panels::settings::SettingsPanelContext& ctx, QWidget* parent)
    : QWidget(parent), panel_ctx_(ctx) {
    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(pipela::ui::theme::scalePxV(8, 24));

    header_wrap_ = new QWidget(this);
    header_wrap_->setObjectName(QString::fromUtf8("pipelaSettingsHeader"));
    auto* header_l = new QHBoxLayout(header_wrap_);
    header_l->setContentsMargins(pipela::ui::theme::scalePxH(8, 400), pipela::ui::theme::scalePxV(6, 24),
                                   pipela::ui::theme::scalePxH(8, 400), pipela::ui::theme::scalePxV(6, 24));
    header_l->setSpacing(pipela::ui::theme::scalePxH(8, 400));

    nav_back_btn_ = new QPushButton(QString::fromUtf8("←"), header_wrap_);
    nav_back_btn_->setObjectName(QString::fromUtf8("pipelaSettingsNavBtn"));
    nav_forward_btn_ = new QPushButton(QString::fromUtf8("→"), header_wrap_);
    nav_forward_btn_->setObjectName(QString::fromUtf8("pipelaSettingsNavBtn"));
    connect(nav_back_btn_, &QPushButton::clicked, this, &SettingsHubWidget::navigateBack);
    connect(nav_forward_btn_, &QPushButton::clicked, this, &SettingsHubWidget::navigateForward);

    header_title_ = new QLabel(QString::fromUtf8("설정"), header_wrap_);
    header_title_->setObjectName(QString::fromUtf8("pipelaSettingsHeaderTitle"));
    header_title_->setAlignment(Qt::AlignCenter);
    header_title_->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);

    header_l->addWidget(nav_back_btn_);
    header_l->addWidget(header_title_, 1);
    header_l->addWidget(nav_forward_btn_);
    root->addWidget(header_wrap_);

    stack_ = new QStackedWidget(this);
    stack_->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    root->addWidget(stack_, 1);

    buildHubPage();
    buildPanels();
    gotoHub();
    applyHeaderChrome();
    updateNavButtons();
}

void SettingsHubWidget::applyHeaderChrome() {
    if (header_wrap_ == nullptr) {
        return;
    }
    const int w = width() > 0 ? width() : 400;
    const int h = height() > 0 ? height() : 24;
    header_wrap_->setStyleSheet(pipela::ui::theme::settingsHubHeaderQss(w, h));
}

QPushButton* SettingsHubWidget::makeCategoryRow(QWidget* parent, const char* panel_id,
                                                const QString& title) {
    auto* btn = new QPushButton(parent);
    btn->setObjectName(QString::fromUtf8("pipelaSettingsCategoryRow"));
    btn->setText(QString::fromUtf8("%1   ›").arg(title));
    btn->setCursor(Qt::PointingHandCursor);
    btn->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
    btn->setMinimumHeight(pipela::ui::theme::scalePxV(40, 24));
    btn->setStyleSheet(pipela::ui::theme::settingsHubCategoryRowQss());
    connect(btn, &QPushButton::clicked, this, [this, panel_id]() { openPanelById(panel_id); });
    return btn;
}

void SettingsHubWidget::addSectionLabel(QVBoxLayout* layout, const QString& text, QWidget* parent) {
    if (layout == nullptr) {
        return;
    }
    auto* label = new QLabel(text, parent);
    label->setObjectName(QString::fromUtf8("pipelaSettingsSectionLabel"));
    label->setAlignment(Qt::AlignHCenter | Qt::AlignVCenter);
    layout->addWidget(label);
}

void SettingsHubWidget::buildHubPage() {
    auto* hub_pg = new QWidget(this);
    auto* hvl = new QVBoxLayout(hub_pg);
    hvl->setContentsMargins(0, 0, 0, 0);

    hub_scroll_ = new QScrollArea(hub_pg);
    hub_scroll_->setWidgetResizable(true);
    hub_scroll_->setFrameShape(QFrame::NoFrame);
    hub_scroll_->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);

    hub_list_host_ = new QWidget(hub_scroll_);
    const int hub_gap = pipela::ui::theme::scalePxV(6, 24);
    const int side_pad = pipela::ui::theme::scalePxH(4, 400);
    hub_list_host_->setMaximumWidth(pipela::ui::theme::scalePxH(360, 400));

    auto* outer_row = new QHBoxLayout(hub_list_host_);
    outer_row->setContentsMargins(side_pad, 0, side_pad, 0);
    outer_row->addStretch(1);

    auto* list_col = new QVBoxLayout();
    list_col->setSpacing(hub_gap);
    list_col->setContentsMargins(0, 0, 0, pipela::ui::theme::scalePxV(8, 24));

    addSectionLabel(list_col, QString::fromUtf8("기능"), hub_list_host_);
    for (const auto& entry : hubMainEntries()) {
        panel_titles_[entry.panel_id] = QString::fromUtf8(entry.title_ko);
        list_col->addWidget(makeCategoryRow(hub_list_host_, entry.panel_id,
                                            QString::fromUtf8(entry.title_ko)));
    }

    auto* divider = new QFrame(hub_list_host_);
    divider->setFrameShape(QFrame::HLine);
    divider->setFixedHeight(1);
    divider->setStyleSheet(QString::fromUtf8("background: #2a3438; border: none; margin: 6px 0;"));
    list_col->addWidget(divider);

    addSectionLabel(list_col, QString::fromUtf8("기타"), hub_list_host_);
    for (const auto& entry : hubFooterEntries()) {
        panel_titles_[entry.panel_id] = QString::fromUtf8(entry.title_ko);
        list_col->addWidget(makeCategoryRow(hub_list_host_, entry.panel_id,
                                            QString::fromUtf8(entry.title_ko)));
    }

    list_col->addStretch(1);
    outer_row->addLayout(list_col, 0);
    outer_row->addStretch(1);

    hub_scroll_->setWidget(hub_list_host_);
    hvl->addWidget(hub_scroll_, 1);
    stack_->addWidget(hub_pg);
}

void SettingsHubWidget::buildPanels() {
    const auto& defs = allSettingsPanelDefs();
    panel_ids_.clear();
    panel_id_to_stack_index_.clear();

    std::vector<const char*> ordered_ids;
    for (const auto& entry : hubMainEntries()) {
        if (panelDefListed(defs, entry.panel_id)) {
            ordered_ids.push_back(entry.panel_id);
        }
    }
    for (const auto& entry : hubFooterEntries()) {
        if (panelDefListed(defs, entry.panel_id)) {
            ordered_ids.push_back(entry.panel_id);
        }
    }
    for (const auto& def : defs) {
        if (!isHubPanelId(def.id)) {
            ordered_ids.push_back(def.id);
        }
        if (panel_titles_.find(def.id) == panel_titles_.end()) {
            panel_titles_[def.id] = QString::fromUtf8(def.title_ko);
        }
    }

    for (const char* panel_id : ordered_ids) {
        const SettingsPanelDef* def = nullptr;
        for (const auto& d : defs) {
            if (d.id == panel_id) {
                def = &d;
                break;
            }
        }
        if (def == nullptr) {
            continue;
        }
        const int idx = stack_->count();
        panel_ids_.push_back(def->id);
        panel_id_to_stack_index_[def->id] = idx;
        stack_->addWidget(
            pipela::app::panels::settings::createPanelForDef(this, *def, panel_ctx_));
    }
}

void SettingsHubWidget::updateNavButtons() {
    if (nav_back_btn_ == nullptr || nav_forward_btn_ == nullptr || stack_ == nullptr) {
        return;
    }
    const bool on_hub = stack_->currentIndex() <= 0;
    nav_back_btn_->setEnabled(!on_hub || nav_pos_ > 0);
    nav_forward_btn_->setEnabled(nav_pos_ >= 0 && nav_pos_ + 1 < static_cast<int>(nav_hist_.size()));
}

void SettingsHubWidget::pushNavHistory(const std::string& panel_id) {
    if (nav_pos_ >= 0 && nav_pos_ < static_cast<int>(nav_hist_.size()) &&
        nav_hist_[static_cast<size_t>(nav_pos_)] == panel_id) {
        return;
    }
    if (nav_pos_ + 1 < static_cast<int>(nav_hist_.size())) {
        nav_hist_.erase(nav_hist_.begin() + nav_pos_ + 1, nav_hist_.end());
    }
    nav_hist_.push_back(panel_id);
    nav_pos_ = static_cast<int>(nav_hist_.size()) - 1;
    updateNavButtons();
}

void SettingsHubWidget::updateHeader() {
    if (header_title_ == nullptr || stack_ == nullptr) {
        return;
    }
    header_wrap_->show();
    const int idx = stack_->currentIndex();
    if (idx <= 0) {
        header_title_->setText(QString::fromUtf8("설정"));
        updateNavButtons();
        return;
    }
    const char* pid = currentPanelId();
    QString title = QString::fromUtf8("설정");
    if (pid != nullptr) {
        const auto it = panel_titles_.find(pid);
        title = it != panel_titles_.end() ? it->second : QString::fromUtf8(pid);
    }
    header_title_->setText(title);
    updateNavButtons();
}

bool SettingsHubWidget::openPanelById(const char* panel_id, bool push_history) {
    if (panel_id == nullptr || stack_ == nullptr) {
        return false;
    }
    const auto it = panel_id_to_stack_index_.find(panel_id);
    if (it == panel_id_to_stack_index_.end()) {
        return false;
    }
    stack_->setCurrentIndex(it->second);
    if (push_history) {
        pushNavHistory(panel_id);
    }
    updateHeader();
    flushSettingsLayout();
    return true;
}

void SettingsHubWidget::gotoHub() {
    if (stack_ == nullptr) {
        return;
    }
    stack_->setCurrentIndex(0);
    updateHeader();
    flushSettingsLayout();
}

bool SettingsHubWidget::navigateBack() {
    if (nav_pos_ > 0) {
        --nav_pos_;
        const std::string& pid = nav_hist_[static_cast<size_t>(nav_pos_)];
        if (pid.empty()) {
            gotoHub();
            return true;
        }
        return openPanelById(pid.c_str(), false);
    }
    if (stack_ != nullptr && stack_->currentIndex() > 0) {
        gotoHub();
        return true;
    }
    return false;
}

bool SettingsHubWidget::navigateForward() {
    if (nav_pos_ + 1 >= static_cast<int>(nav_hist_.size())) {
        return false;
    }
    ++nav_pos_;
    const std::string& pid = nav_hist_[static_cast<size_t>(nav_pos_)];
    if (pid.empty()) {
        gotoHub();
        return true;
    }
    return openPanelById(pid.c_str(), false);
}

bool SettingsHubWidget::handleMouseNavigation(Qt::MouseButton button) {
    if (button == Qt::BackButton) {
        return navigateBack();
    }
    if (button == Qt::ForwardButton) {
        return navigateForward();
    }
    return false;
}

void SettingsHubWidget::flushSettingsLayout() {
    applyHeaderChrome();
    if (hub_scroll_ != nullptr && hub_list_host_ != nullptr) {
        const int w = width() > 0 ? width() : 400;
        hub_list_host_->setMaximumWidth(pipela::ui::theme::scalePxH(360, w));
        hub_list_host_->updateGeometry();
        hub_scroll_->widget()->updateGeometry();
    }
    updateGeometry();
}

const char* SettingsHubWidget::currentPanelId() const {
    if (stack_ == nullptr) {
        return nullptr;
    }
    const int idx = stack_->currentIndex();
    if (idx <= 0) {
        return nullptr;
    }
    const int panel_row = idx - 1;
    if (panel_row < 0 || panel_row >= static_cast<int>(panel_ids_.size())) {
        return nullptr;
    }
    return panel_ids_[static_cast<size_t>(panel_row)].c_str();
}

}  // namespace pipela::ui::panels
