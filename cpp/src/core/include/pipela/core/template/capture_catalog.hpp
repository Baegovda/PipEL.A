#pragma once

#include <optional>
#include <string>

namespace pipela::core::template_meta {

struct CaptureKindMeta {
    std::string filename;
    std::string image_data_registry_key;
    std::string path_registry_key;
};

std::optional<CaptureKindMeta> captureKindMeta(const std::string& capture_kind);
std::optional<std::string> captureOutputPathForKind(const std::string& capture_kind);
// AGENT: Canonical on-disk template path when registry path is unset (file-only image storage).
std::optional<std::string> defaultTemplatePathForPathRegistryKey(const std::string& path_registry_key);

}  // namespace pipela::core::template_meta
