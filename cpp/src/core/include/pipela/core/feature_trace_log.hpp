#pragma once

#include <cstdint>
#include <optional>
#include <string>

#include "pipela/core/state/app_state.hpp"

namespace pipela::core {

// AGENT: Append-only feature/input trace for agent diagnosis (%LOCALAPPDATA%/Pipela/feature_trace.log).
// Default ON at depth=deep; PIPELA_FEATURE_TRACE=0 disables; PIPELA_FEATURE_TRACE_DEPTH=normal|verbose|deep.

enum class FeatureTraceDepth {
    Off = 0,
    Normal = 1,
    Verbose = 2,
    Deep = 3,
};

bool featureTraceEnabled();

FeatureTraceDepth featureTraceDepth();

bool featureTraceAtLeast(FeatureTraceDepth min_depth);

std::string featureTraceLogPath();

void featureTraceEnsureSession();

uint64_t featureTraceMonoMs();

std::string featureTraceThreadTag();

void featureTraceLog(const char* category, const std::string& message);

void featureTraceLogAt(FeatureTraceDepth min_depth, const char* category, const std::string& message);

void featureTraceLogStateChange(const std::string& key,
                                const std::optional<state::StateValue>& old_value,
                                const state::StateValue& new_value);

void featureTraceRuntimeSnapshot(const state::AppState& state, const char* reason);

// AGENT: Throttle hot-path lines (e.g. loop idle skips, score ticks). interval_ms=0 → no throttle.
void featureTraceThrottle(const std::string& throttle_key,
                          int interval_ms,
                          FeatureTraceDepth min_depth,
                          const char* category,
                          const std::string& message);

inline void featureTraceLog(const char* category, const char* message) {
    if (message != nullptr) {
        featureTraceLog(category, std::string(message));
    }
}

inline void featureTraceLogAt(FeatureTraceDepth min_depth, const char* category, const char* message) {
    if (message != nullptr) {
        featureTraceLogAt(min_depth, category, std::string(message));
    }
}

}  // namespace pipela::core
