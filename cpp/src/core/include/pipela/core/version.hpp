#pragma once

#include <string>

namespace pipela::core {

constexpr const char* kRegistryPath = "Software\\Pipela";
constexpr const char* kAppDisplayName = "Pipela";

std::string appVersion();
std::string stripDisplayVersion();

}  // namespace pipela::core
