#pragma once

#include <string>

#include "pipela/core/feature_trace_log.hpp"

namespace pipela::core::workers {

// AGENT: Per-worker loop tracing — events, throttled skips, deep iteration detail.
class WorkerLoopTracer {
public:
    explicit WorkerLoopTracer(const char* loop_name);

    void event(const std::string& detail) const;
    void action(const std::string& detail) const;
    void deep(const std::string& detail) const;
    void skip(const char* reason) const;

private:
    const char* loop_;
};

}  // namespace pipela::core::workers
