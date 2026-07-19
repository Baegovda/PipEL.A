#include "pipela/core/registry/snapshot.hpp"

#include "pipela/core/paths.hpp"
#include "pipela/core/registry/parse.hpp"

#include <fstream>
#include <nlohmann/json.hpp>
#include <sstream>

namespace pipela::core::registry {

void RegistrySnapshot::clear() { values_.clear(); }

void RegistrySnapshot::set(const std::string& key, const std::string& value) { values_[key] = value; }

void RegistrySnapshot::setBool(const std::string& key, bool value) { values_[key] = value ? "1" : "0"; }

void RegistrySnapshot::setInt(const std::string& key, int value) { values_[key] = std::to_string(value); }

void RegistrySnapshot::setDouble(const std::string& key, double value) {
    values_[key] = std::to_string(value);
}

bool RegistrySnapshot::has(const std::string& key) const { return values_.count(key) > 0; }

bool RegistrySnapshot::snapshotBool(const std::string& key, bool fallback) const {
    const auto it = values_.find(key);
    if (it == values_.end()) {
        return fallback;
    }
    return parseBool(it->second);
}

int RegistrySnapshot::snapshotInt(const std::string& key, int fallback) const {
    const auto it = values_.find(key);
    if (it == values_.end()) {
        return fallback;
    }
    try {
        return std::stoi(it->second);
    } catch (...) {
        return fallback;
    }
}

double RegistrySnapshot::snapshotFloat(const std::string& key, double fallback) const {
    const auto it = values_.find(key);
    if (it == values_.end()) {
        return fallback;
    }
    try {
        return std::stod(it->second);
    } catch (...) {
        return fallback;
    }
}

std::optional<std::string> RegistrySnapshot::snapshotString(const std::string& key) const {
    const auto it = values_.find(key);
    if (it == values_.end()) {
        return std::nullopt;
    }
    return it->second;
}

std::vector<std::string> RegistrySnapshot::builtinKeyNames() {
    std::vector<std::string> keys;
    const std::string path = resolveRepoRoot() + "/registry/snapshot_keys.json";
    std::ifstream in(path);
    if (!in) {
        return keys;
    }
    nlohmann::json j;
    in >> j;
    if (j.contains("keys") && j["keys"].is_array()) {
        for (const auto& k : j["keys"]) {
            if (k.is_string()) {
                keys.push_back(k.get<std::string>());
            }
        }
    }
    return keys;
}

RegistrySnapshot RegistrySnapshot::fromStringMap(const std::map<std::string, std::string>& in) {
    RegistrySnapshot out;
    out.values_ = in;
    return out;
}

}  // namespace pipela::core::registry
