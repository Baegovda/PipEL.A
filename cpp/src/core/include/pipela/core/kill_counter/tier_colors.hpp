#pragma once

#include <optional>
#include <string>

namespace pipela::core::kill_counter {

std::string honorificKey(const std::string& title);
std::optional<std::string> tierFgHexForRankTitle(const std::string& title);

}  // namespace pipela::core::kill_counter
