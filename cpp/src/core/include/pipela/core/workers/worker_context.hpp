#pragma once

#include <atomic>
#include <chrono>
#include <functional>
#include <optional>
#include <string>
#include <thread>

#include "pipela/core/registry/snapshot.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/vision/capture.hpp"
#include "pipela/core/vision/template_match.hpp"

namespace pipela::core::workers {

struct MatchHit {
    double score{0.0};
    int center_x{0};
    int center_y{0};
    bool valid{false};
};

using SnapshotProviderFn = std::function<registry::RegistrySnapshot()>;

class WorkerContext {
public:
    WorkerContext(std::atomic<bool>& stop, state::AppState& state);

    static void setSnapshotProvider(SnapshotProviderFn provider);

    bool stopRequested() const { return stop_.load(); }
    state::AppState& state() { return state_; }

    void refreshSnapshot();
    bool registryBool(const std::string& key, bool fallback = false) const;
    double registryFloat(const std::string& key, double fallback = 0.0) const;
    int registryInt(const std::string& key, int fallback = 0) const;
    std::optional<std::string> registryString(const std::string& key) const;

    bool running() const;
    bool selectMode() const;
    bool flameTriggerActive() const;
    std::intptr_t targetHwnd() const;

    bool powerSaveActive() const;
    void sleepMs(int ms) const;

    std::optional<vision::BgrImage> captureRegion(std::intptr_t hwnd, const double region[4]) const;
    MatchHit matchTemplate(const vision::BgrImage& screen,
                           const vision::BgrImage& templ,
                           double threshold) const;
#if defined(PIPELA_HAS_OPENCV)
    std::optional<vision::BgrImage> loadTemplatePath(const std::string& path) const;
    std::optional<vision::BgrImage> rescaleTemplate(const vision::BgrImage& templ, double ratio) const;
#endif

private:
    std::atomic<bool>& stop_;
    state::AppState& state_;
    registry::RegistrySnapshot snapshot_;
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
