#pragma once

#include <string>
#include <unordered_map>
#include <vector>

#include <QScrollArea>
#include <QWidget>

#include "panels/settings/panel_context.hpp"

class QLabel;
class QPushButton;
class QStackedWidget;
class QVBoxLayout;

namespace pipela::ui::panels {

// AGENT: Settings hub — single-column category list (index 0) + stacked detail panels.
class SettingsHubWidget : public QWidget {
    Q_OBJECT
public:
    explicit SettingsHubWidget(const pipela::app::panels::settings::SettingsPanelContext& ctx,
                               QWidget* parent = nullptr);

    bool openPanelById(const char* panel_id, bool push_history = true);
    void gotoHub();
    const char* currentPanelId() const;
    bool navigateBack();
    bool navigateForward();
    bool handleMouseNavigation(Qt::MouseButton button);
    void flushSettingsLayout();

private:
    void buildHubPage();
    void buildPanels();
    void updateHeader();
    void updateNavButtons();
    void pushNavHistory(const std::string& panel_id);
    void applyHeaderChrome();
    QPushButton* makeCategoryRow(QWidget* parent, const char* panel_id, const QString& title);
    void addSectionLabel(QVBoxLayout* layout, const QString& text, QWidget* parent);

    pipela::app::panels::settings::SettingsPanelContext panel_ctx_;
    QWidget* header_wrap_{nullptr};
    QPushButton* nav_back_btn_{nullptr};
    QPushButton* nav_forward_btn_{nullptr};
    QLabel* header_title_{nullptr};
    QStackedWidget* stack_{nullptr};
    QScrollArea* hub_scroll_{nullptr};
    QWidget* hub_list_host_{nullptr};
    std::vector<std::string> panel_ids_;
    std::unordered_map<std::string, int> panel_id_to_stack_index_;
    std::unordered_map<std::string, QString> panel_titles_;
    std::vector<std::string> nav_hist_;
    int nav_pos_{-1};
};

}  // namespace pipela::ui::panels
