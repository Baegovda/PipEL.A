#pragma once

#include <array>
#include <optional>
#include <string>

namespace pipela::core::registry {

std::optional<std::array<double, 4>> parseRegionJson(const std::string& json_text);

}  // namespace pipela::core::registry
