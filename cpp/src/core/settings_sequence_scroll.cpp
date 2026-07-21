#include "pipela/core/settings_sequence_scroll.hpp"

#include <mutex>
#include <unordered_map>

namespace pipela::core::settings {

namespace {

std::mutex g_mutex;
std::unordered_map<std::string, int> g_steps;

}  // namespace

void seqScrollSet(const std::string& feature, int step) {
    std::lock_guard<std::mutex> lock(g_mutex);
    g_steps[feature] = step;
}

int seqScrollGet(const std::string& feature, int default_step) {
    std::lock_guard<std::mutex> lock(g_mutex);
    const auto it = g_steps.find(feature);
    if (it == g_steps.end()) {
        return default_step;
    }
    return it->second;
}

}  // namespace pipela::core::settings
