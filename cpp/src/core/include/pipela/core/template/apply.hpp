#pragma once

#include <string>

#include "pipela/core/vision/capture.hpp"

namespace pipela::core::template_meta {

#if defined(PIPELA_HAS_OPENCV)
bool applyTemplateCapture(const std::string& capture_kind, const std::string& abs_png_path);
#endif

bool clearMatchRegion(const std::string& region_registry_key);

}  // namespace pipela::core::template_meta
