#include "pipela/core/registry/parse.hpp"

#include <algorithm>
#include <cctype>

namespace pipela::core::registry {

namespace {

std::string lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return s;
}

}  // namespace

bool parseBool(const std::string& value) {
    const std::string s = lower(value);
    if (s == "1" || s == "true" || s == "yes" || s == "y" || s == "on") {
        return true;
    }
    if (s == "0" || s == "false" || s == "no" || s == "n" || s == "off" || s.empty()) {
        return false;
    }
    return false;
}

double clampMatchThreshold01(double v) {
    if (v < 0.1) {
        return 0.1;
    }
    if (v > 1.0) {
        return 1.0;
    }
    return v;
}

}  // namespace pipela::core::registry
