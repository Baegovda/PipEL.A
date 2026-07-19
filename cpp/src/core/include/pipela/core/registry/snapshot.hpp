#pragma once

#include <map>
#include <optional>
#include <string>
#include <vector>

namespace pipela::core::registry {

// AGENT: mirrors pipela_core.registry_config_snapshot + registry_snapshot_read.
class RegistrySnapshot {
public:
    void clear();
    void set(const std::string& key, const std::string& value);
    void setBool(const std::string& key, bool value);
    void setInt(const std::string& key, int value);
    void setDouble(const std::string& key, double value);

    bool has(const std::string& key) const;
    bool snapshotBool(const std::string& key, bool fallback = false) const;
    int snapshotInt(const std::string& key, int fallback = 0) const;
    double snapshotFloat(const std::string& key, double fallback = 0.0) const;
    std::optional<std::string> snapshotString(const std::string& key) const;

    const std::map<std::string, std::string>& values() const { return values_; }

    static std::vector<std::string> builtinKeyNames();
    static RegistrySnapshot fromStringMap(const std::map<std::string, std::string>& in);

private:
    std::map<std::string, std::string> values_;
};

}  // namespace pipela::core::registry
