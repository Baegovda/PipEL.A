#pragma once

#include <optional>
#include <string>
#include <vector>

namespace pipela::core::vision {

// AGENT: Optional native Tesseract (vcpkg tesseract). When PIPELA_HAS_TESSERACT=0, returns nullopt.
struct OcrSlashResult {
    std::string prog_txt;
    std::string err;
};

std::optional<OcrSlashResult> readKillCounterDigitsBgr(const unsigned char* bgr, int w, int h);

}  // namespace pipela::core::vision
