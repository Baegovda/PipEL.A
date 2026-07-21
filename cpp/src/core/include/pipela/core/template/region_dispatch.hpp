#pragma once

#include <optional>
#include <string>

namespace pipela::core::template_meta {

std::optional<std::string> captureKindToRegionType(const std::string& capture_kind);
std::optional<std::string> regionTypeToRegistryKey(const std::string& region_type);
bool regionTypeAllowsClear(const std::string& region_type);

}  // namespace pipela::core::template_meta
