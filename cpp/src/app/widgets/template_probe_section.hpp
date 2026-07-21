#pragma once

#include <QWidget>

class QLabel;
class QTimer;

namespace pipela::app::widgets {
class DragDoubleSpinBox;
}

#include "panels/settings/panel_context.hpp"
#include "panels/settings/worker_template_panel.hpp"

#include "widgets/template_last_match_thumb.hpp"

namespace pipela::app::widgets {

class TemplateProbeSection : public QWidget {
    Q_OBJECT
public:
    explicit TemplateProbeSection(QWidget* parent = nullptr);

    void configure(const pipela::app::panels::settings::TemplateSectionSpec& spec,
                   const pipela::app::panels::settings::SettingsPanelContext& ctx);

protected:
    void showEvent(QShowEvent* event) override;

private:
    void reloadFromRegistry();
    void refreshThumb();
    void refreshScore();
    void refreshLastMatch();
    void onThresholdChanged(double value);
    void runTestMatch();

    pipela::app::panels::settings::TemplateSectionSpec spec_;
    pipela::app::panels::settings::SettingsPanelContext ctx_;
    QLabel* thumb_{nullptr};
    QLabel* score_{nullptr};
    QLabel* path_label_{nullptr};
    TemplateLastMatchThumbRow last_match_row_{};
    pipela::app::widgets::DragDoubleSpinBox* threshold_{nullptr};
    class QTimer* timer_{nullptr};
};

}  // namespace pipela::app::widgets
