#pragma once

#include <optional>
#include <string>

namespace pipela::app::panels::settings {

struct TemplateProbeKeys {
    std::string image_path_key;
    std::string image_data_key;
    std::string region_key;
    std::string score_state_key;
    std::string capture_kind;
};

// One-shot template match for settings 「테스트」 button. Returns best score or nullopt.
std::optional<double> runTemplateProbeTest(std::intptr_t game_hwnd, const TemplateProbeKeys& keys);

}  // namespace pipela::app::panels::settings
