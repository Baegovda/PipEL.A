#pragma once

#include <QWidget>

#include "panels/settings/panel_context.hpp"

namespace pipela::ui::panels {
struct SettingsPanelDef;
}

namespace pipela::app::panels::settings {

QWidget* createPanelForDef(QWidget* parent, const pipela::ui::panels::SettingsPanelDef& def,
                             const SettingsPanelContext& ctx);

}  // namespace pipela::app::panels::settings
