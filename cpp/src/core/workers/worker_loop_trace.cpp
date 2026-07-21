#include "pipela/core/workers/worker_loop_trace.hpp"

#include <sstream>

namespace pipela::core::workers {

WorkerLoopTracer::WorkerLoopTracer(const char* loop_name) : loop_(loop_name ? loop_name : "?") {}

void WorkerLoopTracer::event(const std::string& detail) const {
    featureTraceLogAt(FeatureTraceDepth::Normal, loop_, detail);
}

void WorkerLoopTracer::action(const std::string& detail) const {
    featureTraceLogAt(FeatureTraceDepth::Verbose, loop_, detail);
}

void WorkerLoopTracer::deep(const std::string& detail) const {
    featureTraceLogAt(FeatureTraceDepth::Deep, loop_, detail);
}

void WorkerLoopTracer::skip(const char* reason) const {
    if (reason == nullptr) {
        return;
    }
    const std::string key = std::string(loop_) + "/skip/" + reason;
    const int interval = featureTraceDepth() == FeatureTraceDepth::Deep ? 500 : 2500;
    featureTraceThrottle(key, interval, FeatureTraceDepth::Verbose, loop_,
                         std::string("skip ") + reason);
}

}  // namespace pipela::core::workers
