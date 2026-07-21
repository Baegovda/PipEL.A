#include "pipela/core/template/apply.hpp"

#include "pipela/core/registry/store.hpp"
#include "pipela/core/template/capture_catalog.hpp"

#include <filesystem>

namespace pipela::core::template_meta {

#if defined(PIPELA_HAS_OPENCV)
bool applyTemplateCapture(const std::string& capture_kind, const std::string& abs_png_path) {
    const auto meta = captureKindMeta(capture_kind);
    if (!meta || abs_png_path.empty() || !std::filesystem::is_regular_file(abs_png_path)) {
        return false;
    }
    // AGENT: Image bytes stay on disk only; registry keeps path pointer for UI/worker lookup.
    return pipela::core::registry::saveStringValue(meta->path_registry_key, abs_png_path);
}
#endif

bool clearMatchRegion(const std::string& region_registry_key) {
    if (region_registry_key.empty()) {
        return false;
    }
    return pipela::core::registry::saveStringValue(region_registry_key, std::string{});
}

}  // namespace pipela::core::template_meta
