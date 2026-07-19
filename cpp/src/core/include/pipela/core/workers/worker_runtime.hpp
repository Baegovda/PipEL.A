#pragma once

#include <atomic>
#include <functional>
#include <memory>
#include <string>
#include <thread>
#include <vector>

#include "pipela/core/state/app_state.hpp"

namespace pipela::core::workers {

using WorkerFn = std::function<void(std::atomic<bool>& stop, state::AppState& state)>;

class WorkerRuntime {
public:
    explicit WorkerRuntime(state::AppState& state);
    ~WorkerRuntime();

    void startAll();
    void stopAll();
    bool running() const;

    static std::vector<std::pair<std::string, WorkerFn>> defaultWorkers();

private:
    state::AppState& state_;
    std::atomic<bool> stop_{false};
    std::vector<std::thread> threads_;
};

}  // namespace pipela::core::workers
