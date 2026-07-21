#include "pipela/core/registry/json_region.hpp"

#include <nlohmann/json.hpp>

namespace pipela::core::registry {

std::optional<std::array<double, 4>> parseRegionJson(const std::string& json_text) {
    if (json_text.empty()) {
        return std::nullopt;
    }
    try {
        auto j = nlohmann::json::parse(json_text);
        if (!j.is_array() || j.size() < 4) {
            return std::nullopt;
        }
        return std::array<double, 4>{j[0].get<double>(), j[1].get<double>(), j[2].get<double>(),
                                     j[3].get<double>()};
    } catch (...) {
        return std::nullopt;
    }
}

std::string formatRegionJson(const std::array<double, 4>& region) {
    nlohmann::json j = nlohmann::json::array(
        {region[0], region[1], region[2], region[3]});
    return j.dump();
}

}  // namespace pipela::core::registry
