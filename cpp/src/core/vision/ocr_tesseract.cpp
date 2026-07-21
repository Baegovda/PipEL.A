#include "pipela/core/vision/ocr_tesseract.hpp"

#include <cstring>
#include <regex>
#include <string>
#include <vector>

#if defined(PIPELA_HAS_TESSERACT)
#include <tesseract/baseapi.h>
#endif

namespace pipela::core::vision {

namespace {

std::string extractSlashText(const std::string& raw) {
    static const std::regex slash_re(R"((\d+)\s*/\s*(\d+))");
    std::smatch m;
    if (std::regex_search(raw, m, slash_re)) {
        return m.str();
    }
    return {};
}

#if defined(PIPELA_HAS_TESSERACT)
std::vector<unsigned char> bgrToRgb(const unsigned char* bgr, int w, int h) {
    std::vector<unsigned char> rgb(static_cast<size_t>(w) * static_cast<size_t>(h) * 3);
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            const size_t i = (static_cast<size_t>(y) * static_cast<size_t>(w) + static_cast<size_t>(x)) * 3;
            rgb[i] = bgr[i + 2];
            rgb[i + 1] = bgr[i + 1];
            rgb[i + 2] = bgr[i];
        }
    }
    return rgb;
}

std::optional<OcrSlashResult> runTesseractOnBgr(const unsigned char* bgr, int w, int h) {
    if (bgr == nullptr || w < 1 || h < 1) {
        return std::nullopt;
    }
    const std::vector<unsigned char> rgb = bgrToRgb(bgr, w, h);
    tesseract::TessBaseAPI api;
    if (api.Init(nullptr, "eng") != 0) {
        return OcrSlashResult{"", "Tesseract init failed"};
    }
    api.SetVariable("tessedit_char_whitelist", "0123456789/");
    const tesseract::PageSegMode modes[] = {tesseract::PSM_SINGLE_LINE, tesseract::PSM_SINGLE_BLOCK};
    std::string prog_txt;
    for (const auto mode : modes) {
        api.SetPageSegMode(mode);
        api.SetImage(rgb.data(), w, h, 3, w * 3);
        const char* out = api.GetUTF8Text();
        if (out != nullptr) {
            prog_txt = extractSlashText(std::string(out));
            delete[] out;
        }
        if (!prog_txt.empty()) {
            break;
        }
    }
    if (prog_txt.empty()) {
        return OcrSlashResult{"", "slash digit pattern not found"};
    }
    return OcrSlashResult{prog_txt, ""};
}
#endif

}  // namespace

std::optional<OcrSlashResult> readKillCounterDigitsBgr(const unsigned char* bgr, int w, int h) {
#if defined(PIPELA_HAS_TESSERACT)
    return runTesseractOnBgr(bgr, w, h);
#else
    (void)bgr;
    (void)w;
    (void)h;
    return std::nullopt;
#endif
}

}  // namespace pipela::core::vision
