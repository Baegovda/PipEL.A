#include "pipela/core/vision/registry_image_loader.hpp"

#include "pipela/core/registry/store.hpp"

#if defined(PIPELA_HAS_OPENCV)

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <wincrypt.h>
#endif

#include <fstream>
#include <vector>

#include <opencv2/imgcodecs.hpp>

namespace pipela::core::vision {

namespace {

#ifdef _WIN32
std::vector<unsigned char> decodeBase64Windows(const std::string& b64) {
    if (b64.empty()) {
        return {};
    }
    DWORD out_len = 0;
    if (!CryptStringToBinaryA(b64.c_str(), 0, CRYPT_STRING_BASE64, nullptr, &out_len, nullptr,
                              nullptr)) {
        return {};
    }
    std::vector<unsigned char> out(static_cast<size_t>(out_len));
    if (!CryptStringToBinaryA(b64.c_str(), 0, CRYPT_STRING_BASE64, out.data(), &out_len, nullptr,
                              nullptr)) {
        return {};
    }
    out.resize(static_cast<size_t>(out_len));
    return out;
}

std::optional<std::string> encodeBase64Windows(const std::vector<unsigned char>& bytes) {
    if (bytes.empty()) {
        return std::nullopt;
    }
    DWORD out_len = 0;
    if (!CryptBinaryToStringA(bytes.data(), static_cast<DWORD>(bytes.size()), CRYPT_STRING_BASE64,
                              nullptr, &out_len)) {
        return std::nullopt;
    }
    std::string out(static_cast<size_t>(out_len), '\0');
    if (!CryptBinaryToStringA(bytes.data(), static_cast<DWORD>(bytes.size()), CRYPT_STRING_BASE64,
                              out.data(), &out_len)) {
        return std::nullopt;
    }
    while (!out.empty() && (out.back() == '\0' || out.back() == '\r' || out.back() == '\n')) {
        out.pop_back();
    }
    return out;
}
#endif

}  // namespace

std::optional<BgrImage> loadBgrFromRegistryBase64(const std::string& base64_text) {
#ifdef _WIN32
    const std::vector<unsigned char> png_bytes = decodeBase64Windows(base64_text);
    if (png_bytes.empty()) {
        return std::nullopt;
    }
    cv::Mat buf(1, static_cast<int>(png_bytes.size()), CV_8UC1,
                const_cast<unsigned char*>(png_bytes.data()));
    cv::Mat img = cv::imdecode(buf, cv::IMREAD_COLOR);
    if (img.empty()) {
        return std::nullopt;
    }
    BgrImage out;
    out.width = img.cols;
    out.height = img.rows;
    out.bytes.assign(img.data, img.data + img.total() * img.elemSize());
    return out;
#else
    (void)base64_text;
    return std::nullopt;
#endif
}

std::optional<std::string> encodeBgrToRegistryBase64(const BgrImage& image) {
#ifdef _WIN32
    if (image.width < 1 || image.height < 1 || image.bytes.empty()) {
        return std::nullopt;
    }
    const int stride = image.width * 3;
    cv::Mat mat(image.height, image.width, CV_8UC3, const_cast<unsigned char*>(image.bytes.data()),
                stride);
    std::vector<unsigned char> png;
    if (!cv::imencode(".png", mat, png)) {
        return std::nullopt;
    }
    return encodeBase64Windows(png);
#else
    (void)image;
    return std::nullopt;
#endif
}

bool writeBgrToPng(const BgrImage& image, const std::string& abs_path) {
    if (image.width < 1 || image.height < 1 || image.bytes.empty()) {
        return false;
    }
    const int stride = image.width * 3;
    cv::Mat mat(image.height, image.width, CV_8UC3, const_cast<unsigned char*>(image.bytes.data()),
                stride);
    return cv::imwrite(abs_path, mat);
}

bool saveImageFileToRegistry(const std::string& abs_png_path, const std::string& registry_key) {
#ifdef _WIN32
    std::ifstream in(abs_png_path, std::ios::binary);
    if (!in) {
        return false;
    }
    const std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(in)),
                                           std::istreambuf_iterator<char>());
    if (bytes.empty()) {
        return false;
    }
    const auto b64 = encodeBase64Windows(bytes);
    if (!b64) {
        return false;
    }
    return pipela::core::registry::saveStringValue(registry_key, *b64);
#else
    (void)abs_png_path;
    (void)registry_key;
    return false;
#endif
}

}  // namespace pipela::core::vision

#endif  // PIPELA_HAS_OPENCV
