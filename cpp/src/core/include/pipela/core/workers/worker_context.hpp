#pragma once

#include <atomic>
#include <chrono>
#include <functional>
#include <optional>
#include <string>
#include <thread>
#include <vector>

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

struct KillCounterOcrResult {
    std::string prog_txt;
    std::string poll_phase;
    std::string poll_detail;
    std::string last_progress;
    bool ok{false};
    bool skip{false};
};

using SnapshotProviderFn = std::function<registry::RegistrySnapshot()>;
using TemplateBgrLoaderFn = std::function<std::optional<vision::BgrImage>(const std::string& registry_data_key)>;
using KillCounterOcrFn =
    std::function<std::optional<KillCounterOcrResult>(const unsigned char* bgr, int w, int h)>;
using VoidCallbackFn = std::function<void()>;
using LoopLogFn = std::function<void(const std::string&)>;

class WorkerContext {
public:
    WorkerContext(std::atomic<bool>& stop, state::AppState& state);

    static void setSnapshotProvider(SnapshotProviderFn provider);
    static void setTemplateBgrLoader(TemplateBgrLoaderFn loader);
    static void setKillCounterOcrLoader(KillCounterOcrFn loader);
    static void setRefreshTargetHwndCallback(VoidCallbackFn callback);
    static void setLoopLogCallback(LoopLogFn callback);

    void loopLog(const char* msg) const;
    void loopLog(const std::string& msg) const { loopLog(msg.c_str()); }

    bool stopRequested() const { return stop_.load(); }
    state::AppState& state() { return state_; }

    void refreshSnapshot();
    bool registryBool(const std::string& key, bool fallback = false) const;
    double registryFloat(const std::string& key, double fallback = 0.0) const;
    int registryInt(const std::string& key, int fallback = 0) const;
    std::optional<std::string> registryString(const std::string& key) const;
    // AGENT: Resolve template PNG path — registry override if file exists, else canonical templates dir.
    std::optional<std::string> resolveTemplatePath(const std::string& path_registry_key) const;

    bool running() const;
    bool selectMode() const;
    bool flameTriggerActive() const;
    bool otherAutomationSuppressesFlameTrigger() const;
    std::intptr_t targetHwnd() const;
    std::intptr_t refreshTargetHwnd();
    std::intptr_t refreshSmartUpdaterHwnd();
    void invalidateSmartUpdaterHwndCache();
    bool isStartGameLauncherEffective() const;

    bool powerSaveActive() const;
    void sleepMs(int ms) const;

    std::optional<vision::BgrImage> captureRegion(std::intptr_t hwnd, const double region[4]) const;
    MatchHit matchTemplate(const vision::BgrImage& screen,
                           const vision::BgrImage& templ,
                           double threshold,
                           const char* last_hit_kind = nullptr) const;
    std::optional<std::pair<int, int>> matchCenterToScreen(std::intptr_t hwnd,
                                                            const double region[4],
                                                            bool has_region,
                                                            int match_center_x,
                                                            int match_center_y) const;
    std::optional<KillCounterOcrResult> runKillCounterOcr(const vision::BgrImage& image) const;
    void clickScreen(int x, int y) const;
#if defined(PIPELA_HAS_OPENCV)
    std::optional<vision::BgrImage> loadTemplatePath(const std::string& path) const;
    std::optional<vision::BgrImage> loadTemplate(const std::string& path,
                                                 const std::string& registry_data_key) const;
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
