#pragma once

#include <any>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>

namespace pipela::core::state {

// AGENT: mirrors pipela_core.app_state AppState (phase-3 bridged keys).
class AppState {
public:
    bool has(const std::string& key) const;
    std::optional<std::any> get(const std::string& key) const;
    void set(const std::string& key, const std::any& value);
    int incrementInt(const std::string& key, int delta = 1);

    void seedDefaults();

private:
    mutable std::mutex mutex_;
    std::unordered_map<std::string, std::any> values_;
};

}  // namespace pipela::core::state
