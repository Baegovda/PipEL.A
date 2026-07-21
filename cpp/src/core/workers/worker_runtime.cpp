#include "pipela/core/workers/worker_runtime.hpp"

#include "pipela/core/feature_trace_log.hpp"
#include "pipela/core/workers/worker_context.hpp"

#include <chrono>
#include <string>

namespace pipela::core::workers {

WorkerRuntime::WorkerRuntime(state::AppState& state) : state_(state) {}

WorkerRuntime::~WorkerRuntime() { stopAll(); }

void WorkerRuntime::startAll() {
    stopAll();
    stop_.store(false);

    struct Spec {
        const char* name;
        void (*fn)(WorkerContext&);
    };
    static const Spec specs[] = {
        {"kill_counter_loop", killCounterWorkerLoop},
        {"reload_loop", reloadWorkerLoop},
        {"ammo_restock_loop", ammoRestockWorkerLoop},
        {"call_merc_loop", callMercWorkerLoop},
        {"ride_loop", rideWorkerLoop},
        {"hp_refill_loop", hpRefillWorkerLoop},
        {"left_click_loop", leftClickWorkerLoop},
        {"right_hold_loop", rightHoldWorkerLoop},
        {"flame_trigger_loop", flameTriggerWorkerLoop},
        {"start_game_launcher_loop", startGameLauncherWorkerLoop},
    };

    for (const auto& spec : specs) {
        const std::string name = spec.name;
        pipela::core::featureTraceLogAt(pipela::core::FeatureTraceDepth::Verbose, "workers",
                                        "thread_start name=" + name);
        threads_.emplace_back([this, fn = spec.fn, name]() {
            WorkerContext ctx(stop_, state_);
            fn(ctx);
            pipela::core::featureTraceLogAt(pipela::core::FeatureTraceDepth::Verbose, "workers",
                                            "thread_exit name=" + name);
        });
    }
    pipela::core::featureTraceLog("workers",
                                  "all_threads_started count=" + std::to_string(threads_.size()));
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
    return {};
}

}  // namespace pipela::core::workers
