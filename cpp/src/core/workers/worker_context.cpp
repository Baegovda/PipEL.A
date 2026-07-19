#include "pipela/core/workers/worker_context.hpp"

#include "pipela/core/registry/store.hpp"
#include "pipela/core/win32/game_windows.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include <cstdlib>
#include <sstream>

namespace pipela::core::workers {

namespace {

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

WorkerContext::WorkerContext(std::atomic<bool>& stop, state::AppState& state)
    : stop_(stop), state_(state) {
    refreshRegistry();
}

void WorkerContext::refreshRegistry() { registry_ = registry::loadAllStringValues(); }

bool WorkerContext::registryBool(const std::string& key, bool fallback) const {
    const auto it = registry_.find(key);
    if (it == registry_.end()) {
        return fallback;
    }
    return registry::parseBool(it->second);
}

double WorkerContext::registryFloat(const std::string& key, double fallback) const {
    const auto it = registry_.find(key);
    if (it == registry_.end()) {
        return fallback;
    }
    try {
        return std::stod(it->second);
    } catch (...) {
        return fallback;
    }
}

int WorkerContext::registryInt(const std::string& key, int fallback) const {
    const auto it = registry_.find(key);
    if (it == registry_.end()) {
        return fallback;
    }
    try {
        return std::stoi(it->second);
    } catch (...) {
        return fallback;
    }
}

bool WorkerContext::running() const { return stateBool(state_, "running", true); }

bool WorkerContext::selectMode() const { return stateBool(state_, "select_mode", false); }

bool WorkerContext::flameTriggerActive() const {
    return stateBool(state_, "flame_trigger_active", false);
}

std::intptr_t WorkerContext::targetHwnd() const { return stateHwnd(state_); }

bool WorkerContext::powerSaveActive() const {
#ifdef _WIN32
    const auto hwnd = targetHwnd();
    if (!hwnd) {
        return true;
    }
    if (!win32::isWindow(hwnd)) {
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

}  // namespace pipela::core::workers
