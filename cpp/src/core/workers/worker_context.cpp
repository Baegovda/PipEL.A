#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/registry/store.hpp"
#include "pipela/core/vision/roi.hpp"
#include "pipela/core/win32/game_windows.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::core::workers {

namespace {

SnapshotProviderFn& snapshotProvider() {
    static SnapshotProviderFn provider;
    return provider;
}

TemplateBgrLoaderFn& templateBgrLoader() {
    static TemplateBgrLoaderFn loader;
    return loader;
}

bool stateBool(const state::AppState& s, const char* key, bool fallback) {
    if (auto v = s.get(key)) {
        if (const auto* b = std::get_if<bool>(&*v)) {
            return *b;
        }
    }
    return fallback;
}

std::intptr_t stateHwnd(const state::AppState& s) {
    if (auto v = s.get("target_hwnd")) {
        if (const auto* i = std::get_if<int>(&*v)) {
            return *i;
        }
        if (const auto* l = std::get_if<std::int64_t>(&*v)) {
            return static_cast<std::intptr_t>(*l);
        }
    }
    return 0;
}

}  // namespace

void WorkerContext::setSnapshotProvider(SnapshotProviderFn provider) {
    snapshotProvider() = std::move(provider);
}

void WorkerContext::setTemplateBgrLoader(TemplateBgrLoaderFn loader) {
    templateBgrLoader() = std::move(loader);
}

WorkerContext::WorkerContext(std::atomic<bool>& stop, state::AppState& state)
    : stop_(stop), state_(state) {
    refreshSnapshot();
}

void WorkerContext::refreshSnapshot() {
    if (snapshotProvider()) {
        snapshot_ = snapshotProvider()();
        return;
    }
    snapshot_ = registry::RegistrySnapshot::fromStringMap(registry::loadAllStringValues());
}

bool WorkerContext::registryBool(const std::string& key, bool fallback) const {
    return snapshot_.snapshotBool(key, fallback);
}

double WorkerContext::registryFloat(const std::string& key, double fallback) const {
    return snapshot_.snapshotFloat(key, fallback);
}

int WorkerContext::registryInt(const std::string& key, int fallback) const {
    return snapshot_.snapshotInt(key, fallback);
}

std::optional<std::string> WorkerContext::registryString(const std::string& key) const {
    return snapshot_.snapshotString(key);
}

bool WorkerContext::running() const { return stateBool(state_, "running", true); }

bool WorkerContext::selectMode() const { return stateBool(state_, "select_mode", false); }

bool WorkerContext::flameTriggerActive() const {
    return stateBool(state_, "flame_trigger_active", false);
}

bool WorkerContext::otherAutomationSuppressesFlameTrigger() const {
    return stateBool(state_, "nobullet_detected", false) ||
           stateBool(state_, "ammo_restock_sequence_busy", false) ||
           stateBool(state_, "call_merc_sequence_busy", false);
}

std::intptr_t WorkerContext::targetHwnd() const { return stateHwnd(state_); }

bool WorkerContext::powerSaveActive() const {
#ifdef _WIN32
    const auto hwnd = targetHwnd();
    if (!hwnd || !win32::isWindow(hwnd)) {
        return true;
    }
    return IsIconic(reinterpret_cast<HWND>(hwnd)) != FALSE;
#else
    return false;
#endif
}

void WorkerContext::sleepMs(int ms) const {
    for (int i = 0; i < ms && !stop_.load(); i += 20) {
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
}

std::optional<vision::BgrImage> WorkerContext::captureRegion(std::intptr_t hwnd,
                                                             const double region[4]) const {
    auto full = vision::captureClientBgr(hwnd);
    if (!full) {
        return std::nullopt;
    }
    if (!region) {
        return full;
    }
    auto px = vision::regionPixels(full->width, full->height, region);
    if (!px) {
        return full;
    }
    return vision::sliceBgr(*full, (*px)[0], (*px)[1], (*px)[2], (*px)[3]);
}

MatchHit WorkerContext::matchTemplate(const vision::BgrImage& screen,
                                    const vision::BgrImage& templ,
                                    double threshold) const {
    MatchHit hit;
    const int sstride = screen.width * 3;
    const int tstride = templ.width * 3;
    auto result = vision::matchTemplateCcoeffNormedMax(
        screen.bytes.data(), screen.width, screen.height, sstride, templ.bytes.data(), templ.width,
        templ.height, tstride);
    hit.score = result.score;
    hit.valid = result.valid && result.score >= threshold;
    if (hit.valid) {
        hit.center_x = result.top_left_x + templ.width / 2;
        hit.center_y = result.top_left_y + templ.height / 2;
    }
    return hit;
}

#if defined(PIPELA_HAS_OPENCV)
std::optional<vision::BgrImage> WorkerContext::loadTemplatePath(const std::string& path) const {
    return vision::loadBgrFromPath(path);
}

std::optional<vision::BgrImage> WorkerContext::loadTemplate(const std::string& path,
                                                            const std::string& registry_data_key) const {
    if (!path.empty()) {
        if (auto from_path = loadTemplatePath(path)) {
            return from_path;
        }
    }
    if (templateBgrLoader() && !registry_data_key.empty()) {
        return templateBgrLoader()(registry_data_key);
    }
    return std::nullopt;
}

std::optional<vision::BgrImage> WorkerContext::rescaleTemplate(const vision::BgrImage& templ,
                                                               double ratio) const {
    return vision::scaleBgr(templ, ratio);
}
#endif

}  // namespace pipela::core::workers
