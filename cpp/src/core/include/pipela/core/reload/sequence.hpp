#pragma once

#include <string>
#include <tuple>

namespace pipela::core::reload {

std::tuple<int, std::string> clampAmmoCount(int raw);

}  // namespace pipela::core::reload
