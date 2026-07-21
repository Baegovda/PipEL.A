#pragma once

#include <optional>
#include <string>

#include "pipela/core/vision/capture.hpp"

namespace pipela::core::template_meta {

void storeLastMatch(const std::string& kind, const vision::BgrImage& patch_bgr, double score);

std::optional<vision::BgrImage> getLastMatchPatchBgr(const std::string& kind);

std::optional<double> getLastMatchScore(const std::string& kind);

}  // namespace pipela::core::template_meta
