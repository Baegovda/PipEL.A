#include "pipela/core/workers/worker_runtime.hpp"

#include <any>
#include <chrono>

namespace pipela::core::workers {

namespace {

void sleepTick(std::atomic<bool>& stop) {
    for (int i = 0; i < 50 && !stop.load(); ++i) {
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
}

void makeIdleWorker(const char* name, WorkerFn& out) {
    out = [name](std::atomic<bool>& stop, state::AppState& state) {
        (void)name;
        while (!stop.load()) {
            if (auto v = state.get("running"); v.has_value()) {
                try {
                    if (!std::any_cast<bool>(*v)) {
                        sleepTick(stop);
                        continue;
                    }
                } catch (...) {
                }
            }
            sleepTick(stop);
        }
    };
}

}  // namespace

WorkerRuntime::WorkerRuntime(state::AppState& state) : state_(state) {}

WorkerRuntime::~WorkerRuntime() { stopAll(); }

void WorkerRuntime::startAll() {
    stopAll();
    stop_.store(false);
    for (const auto& [name, fn] : defaultWorkers()) {
        (void)name;
        threads_.emplace_back([this, fn]() { fn(stop_, state_); });
    }
}

void WorkerRuntime::stopAll() {
    stop_.store(true);
    for (auto& t : threads_) {
        if (t.joinable()) {
            t.join();
        }
    }
    threads_.clear();
    stop_.store(false);
}

bool WorkerRuntime::running() const { return !threads_.empty(); }

std::vector<std::pair<std::string, WorkerFn>> WorkerRuntime::defaultWorkers() {
    std::vector<std::pair<std::string, WorkerFn>> out;
    const char* names[] = {"kill_counter_loop",
                           "reload_loop",
                           "ammo_restock_loop",
                           "call_merc_loop",
                           "ride_loop",
                           "hp_refill_loop",
                           "left_click_loop",
                           "right_hold_loop",
                           "flame_trigger_loop",
                           "start_game_launcher_loop"};
    for (const char* n : names) {
        WorkerFn fn;
        makeIdleWorker(n, fn);
        out.emplace_back(n, std::move(fn));
    }
    return out;
}

}  // namespace pipela::core::workers
