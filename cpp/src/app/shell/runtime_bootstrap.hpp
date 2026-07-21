#pragma once

#include <memory>

#include "pipela/core/state/app_state.hpp"
#include "pipela/core/workers/worker_runtime.hpp"

namespace pipela::ui::shell {

// AGENT: C++ exe worker bootstrap — registry snapshot + WorkerRuntime (no Python).
class RuntimeBootstrap {
public:
    RuntimeBootstrap();
    ~RuntimeBootstrap();

    RuntimeBootstrap(const RuntimeBootstrap&) = delete;
    RuntimeBootstrap& operator=(const RuntimeBootstrap&) = delete;

    void start();
    void stop();

    pipela::core::state::AppState& state() { return state_; }
    bool workersRunning() const;

    void refreshGameHwnd();
    std::intptr_t targetHwnd() const;

private:
    pipela::core::state::AppState state_;
    std::unique_ptr<pipela::core::workers::WorkerRuntime> runtime_;
    bool started_{false};
};

}  // namespace pipela::ui::shell
