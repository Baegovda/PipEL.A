#pragma once

#include <QString>
#include <vector>

#include "panels/settings/panel_context.hpp"

class QWidget;

namespace pipela::app::panels::settings {

struct TemplateSectionSpec {
    QString section_title;
    QString threshold_key;
    QString image_path_key;
    QString image_data_key;
    QString region_key;
    QString score_state_key;
    QString capture_kind;
};

struct WorkerSettingsSpec {
    QString panel_id;
    std::vector<TemplateSectionSpec> sections;
};

QWidget* createWorkerTemplatePanel(QWidget* parent, const WorkerSettingsSpec& spec,
                                   const SettingsPanelContext& ctx);
const WorkerSettingsSpec* workerSettingsSpecForId(const char* panel_id);

}  // namespace pipela::app::panels::settings
