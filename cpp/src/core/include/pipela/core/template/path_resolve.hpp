#pragma once

#include <functional>
#include <optional>
#include <string>

namespace pipela::core::template_meta {

// AGENT: File-only templates — pick first existing PNG among canonical + registry paths.
std::optional<std::string> resolveExistingTemplateImagePath(
    const std::string& capture_kind, const std::string& path_registry_key,
    const std::function<std::optional<std::string>(const std::string& key)>& lookup_registry);

// AGENT: Best path string for UI labels (canonical when capture_kind known).
std::string templateImagePathForDisplay(const std::string& capture_kind,
                                        const std::string& path_registry_key,
                                        const std::function<std::optional<std::string>(const std::string& key)>&
                                            lookup_registry);

}  // namespace pipela::core::template_meta
