#include "pipela/core/template/last_match_cache.hpp"

#include <mutex>
#include <unordered_map>

namespace pipela::core::template_meta {

namespace {

struct Entry {
    vision::BgrImage patch;
    double score{0.0};
};

std::mutex g_mutex;
std::unordered_map<std::string, Entry> g_cache;

}  // namespace

void storeLastMatch(const std::string& kind, const vision::BgrImage& patch_bgr, double score) {
    if (kind.empty() || patch_bgr.bytes.empty() || patch_bgr.width < 1 || patch_bgr.height < 1) {
        return;
    }
    std::lock_guard<std::mutex> lock(g_mutex);
    g_cache[kind] = Entry{patch_bgr, score};
}

std::optional<vision::BgrImage> getLastMatchPatchBgr(const std::string& kind) {
    std::lock_guard<std::mutex> lock(g_mutex);
    const auto it = g_cache.find(kind);
    if (it == g_cache.end()) {
        return std::nullopt;
    }
    return it->second.patch;
}

std::optional<double> getLastMatchScore(const std::string& kind) {
    std::lock_guard<std::mutex> lock(g_mutex);
    const auto it = g_cache.find(kind);
    if (it == g_cache.end()) {
        return std::nullopt;
    }
    return it->second.score;
}

}  // namespace pipela::core::template_meta
