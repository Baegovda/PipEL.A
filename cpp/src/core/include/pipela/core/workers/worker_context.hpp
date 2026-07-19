#pragma once

#include <atomic>
#include <chrono>
#include <map>
#include <string>
#include <thread>

#include "pipela/core/registry/parse.hpp"
#include "pipela/core/state/app_state.hpp"

namespace pipela::core::workers {

// AGENT: per-thread context shared by all worker loops (Phase 2).
class WorkerContext {
public:
    WorkerContext(std::atomic<bool>& stop, state::AppState& state);

    bool stopRequested() const { return stop_.load(); }
    state::AppState& state() { return state_; }

    void refreshRegistry();
    bool registryBool(const std::string& key, bool fallback = false) const;
    double registryFloat(const std::string& key, double fallback = 0.0) const;
    int registryInt(const std::string& key, int fallback = 0) const;

    bool running() const;
    bool selectMode() const;
    bool flameTriggerActive() const;
    std::intptr_t targetHwnd() const;

    bool powerSaveActive() const;
    void sleepMs(int ms) const;

private:
    std::atomic<bool>& stop_;
    state::AppState& state_;
    std::map<std::string, std::string> registry_;
};

void killCounterWorkerLoop(WorkerContext& ctx);
void reloadWorkerLoop(WorkerContext& ctx);
void ammoRestockWorkerLoop(WorkerContext& ctx);
void callMercWorkerLoop(WorkerContext& ctx);
void rideWorkerLoop(WorkerContext& ctx);
void hpRefillWorkerLoop(WorkerContext& ctx);
void leftClickWorkerLoop(WorkerContext& ctx);
void rightHoldWorkerLoop(WorkerContext& ctx);
void flameTriggerWorkerLoop(WorkerContext& ctx);
void startGameLauncherWorkerLoop(WorkerContext& ctx);

}  // namespace pipela::core::workers
