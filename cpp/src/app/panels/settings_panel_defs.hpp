#pragma once

#include <QString>
#include <vector>

namespace pipela::ui::panels {

struct SettingsPanelDef {
    const char* id;
    const char* title_ko;
    const char* registry_prefix;  // empty = placeholder only
};

const std::vector<SettingsPanelDef>& allSettingsPanelDefs();

}  // namespace pipela::ui::panels
