#pragma once

#include <functional>

#include <QString>

namespace pipela::core::state {
class AppState;
}
namespace pipela::ui::overlays {
class TemplateOverlayController;
}
namespace pipela::app::update {
class UpdateController;
}

namespace pipela::app::panels::settings {

struct SettingsPanelContext {
    pipela::core::state::AppState* state{nullptr};
    std::function<void(const QString&)> log;
    pipela::ui::overlays::TemplateOverlayController* overlays{nullptr};
    std::function<void()> sync_console_time;
    std::function<void()> apply_console_retention;
    std::function<void(int)> apply_font_pt;
    pipela::app::update::UpdateController* update{nullptr};
};

}  // namespace pipela::app::panels::settings
