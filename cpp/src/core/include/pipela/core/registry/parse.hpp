#pragma once

#include <string>

namespace pipela::core::registry {

bool parseBool(const std::string& value);
double clampMatchThreshold01(double value);

}  // namespace pipela::core::registry
