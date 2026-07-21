#include "pipela/core/kill_counter/tier_colors.hpp"

#include <cctype>
#include <unordered_map>

namespace pipela::core::kill_counter {

namespace {

const std::unordered_map<std::string, std::string>& honorificFgHex() {
    static const std::unordered_map<std::string, std::string> kMap = {
        {"견습생", "#9ca3af"}, {"초보자", "#e5e7eb"}, {"숙련자", "#4ade80"},
        {"전문가", "#60a5fa"}, {"장인", "#c084fc"},   {"달인", "#e879f9"},
        {"대가", "#fb923c"},   {"명인", "#fde047"},   {"명장", "#e07c4c"},
        {"거장", "#ea580c"},   {"귀인", "#22d3ee"},   {"초인", "#f87171"},
    };
    return kMap;
}

}  // namespace

std::string honorificKey(const std::string& title) {
    std::string t = title;
    while (!t.empty() && std::isspace(static_cast<unsigned char>(t.back()))) {
        t.pop_back();
    }
    while (!t.empty() && std::isspace(static_cast<unsigned char>(t.front()))) {
        t.erase(t.begin());
    }
    const auto digit_pos = t.find_first_of("0123456789");
    if (digit_pos != std::string::npos) {
        return t.substr(0, digit_pos);
    }
    return t;
}

std::optional<std::string> tierFgHexForRankTitle(const std::string& title) {
    const auto it = honorificFgHex().find(honorificKey(title));
    if (it == honorificFgHex().end()) {
        return std::nullopt;
    }
    return it->second;
}

}  // namespace pipela::core::kill_counter
