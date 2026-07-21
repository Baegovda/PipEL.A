#include "pipela/core/template/path_resolve.hpp"

#include "pipela/core/template/capture_catalog.hpp"

#include <filesystem>
#include <vector>

namespace pipela::core::template_meta {

namespace {

bool isExistingFile(const std::string& path) {
    return !path.empty() && std::filesystem::is_regular_file(path);
}

void appendUnique(std::vector<std::string>& out, const std::string& path) {
    if (path.empty()) {
        return;
    }
    for (const std::string& existing : out) {
        if (existing == path) {
            return;
        }
    }
    out.push_back(path);
}

std::vector<std::string> candidatePaths(
    const std::string& capture_kind, const std::string& path_registry_key,
    const std::function<std::optional<std::string>(const std::string& key)>& lookup_registry) {
    std::vector<std::string> paths;
    if (!capture_kind.empty()) {
        if (auto canonical = captureOutputPathForKind(capture_kind)) {
            appendUnique(paths, *canonical);
        }
    }
    if (lookup_registry && !path_registry_key.empty()) {
        if (auto reg = lookup_registry(path_registry_key)) {
            appendUnique(paths, *reg);
        }
    }
    if (!path_registry_key.empty()) {
        if (auto canonical = defaultTemplatePathForPathRegistryKey(path_registry_key)) {
            appendUnique(paths, *canonical);
        }
    }
    return paths;
}

}  // namespace

std::optional<std::string> resolveExistingTemplateImagePath(
    const std::string& capture_kind, const std::string& path_registry_key,
    const std::function<std::optional<std::string>(const std::string& key)>& lookup_registry) {
    for (const std::string& path : candidatePaths(capture_kind, path_registry_key, lookup_registry)) {
        if (isExistingFile(path)) {
            return path;
        }
    }
    return std::nullopt;
}

std::string templateImagePathForDisplay(
    const std::string& capture_kind, const std::string& path_registry_key,
    const std::function<std::optional<std::string>(const std::string& key)>& lookup_registry) {
    if (auto existing = resolveExistingTemplateImagePath(capture_kind, path_registry_key, lookup_registry)) {
        return *existing;
    }
    if (!capture_kind.empty()) {
        if (auto canonical = captureOutputPathForKind(capture_kind)) {
            return *canonical;
        }
    }
    if (lookup_registry && !path_registry_key.empty()) {
        if (auto reg = lookup_registry(path_registry_key)) {
            return *reg;
        }
    }
    if (auto canonical = defaultTemplatePathForPathRegistryKey(path_registry_key)) {
        return *canonical;
    }
    return {};
}

}  // namespace pipela::core::template_meta
