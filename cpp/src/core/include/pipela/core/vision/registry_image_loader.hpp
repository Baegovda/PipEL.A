#pragma once

#include <optional>
#include <string>

#include "pipela/core/vision/capture.hpp"

namespace pipela::core::vision {

// AGENT: Decode HKCU\Software\Pipela REG_SZ base64 PNG blobs (pipela_core.image_registry parity).
#if defined(PIPELA_HAS_OPENCV)
std::optional<BgrImage> loadBgrFromRegistryBase64(const std::string& base64_text);
std::optional<std::string> encodeBgrToRegistryBase64(const BgrImage& image);
bool writeBgrToPng(const BgrImage& image, const std::string& abs_path);
bool saveImageFileToRegistry(const std::string& abs_png_path, const std::string& registry_key);
#endif

}  // namespace pipela::core::vision
