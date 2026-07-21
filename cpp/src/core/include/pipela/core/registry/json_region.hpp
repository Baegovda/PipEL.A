#pragma once

#include <array>
#include <optional>
#include <string>

namespace pipela::core::registry {

std::optional<std::array<double, 4>> parseRegionJson(const std::string& json_text);
std::string formatRegionJson(const std::array<double, 4>& region);

}  // namespace pipela::core::registry
