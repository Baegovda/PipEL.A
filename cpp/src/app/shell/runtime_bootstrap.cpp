#include "runtime_bootstrap.hpp"

#include <cstdio>
#include <iostream>

#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/snapshot.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/feature_trace_log.hpp"
#include "pipela/core/version.hpp"
#include "pipela/core/vision/ocr_tesseract.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/workers/worker_context.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::ui::shell {

namespace {

void attachParentConsole() {
#ifdef _WIN32
    if (AttachConsole(ATTACH_PARENT_PROCESS)) {
        FILE* dummy = nullptr;
        freopen_s(&dummy, "CONOUT$", "w", stdout);
        freopen_s(&dummy, "CONOUT$", "w", stderr);
        std::cout.clear();
        std::cerr.clear();
    }
#endif
}

void seedStateFromRegistry(pipela::core::state::AppState& state) {
    state.seedFromDefaults();
    const auto values = pipela::core::registry::loadAllStringValues();
    auto seed_bool = [&](const char* key, bool fallback) {
        const auto it = values.find(key);
        const bool v =
            it != values.end() ? pipela::core::registry::parseBool(it->second) : fallback;
        state.set(key, pipela::core::state::StateValue{v});
    };
    seed_bool("reload_active", true);
    seed_bool("ammo_restock_active", false);
    seed_bool("left_click_feature_enabled", true);
    seed_bool("right_hold_feature_enabled", true);
    seed_bool("kill_counter_enabled", true);
    seed_bool("flame_trigger_active", false);
    seed_bool("left_click_active", false);
    seed_bool("right_hold_active", false);

    int ammo_toggle = 0x75;
    const auto ammo_it = values.find("ammo_restock_toggle_key_code");
    if (ammo_it != values.end() && !ammo_it->second.empty()) {
        try {
            ammo_toggle = std::stoi(ammo_it->second);
        } catch (...) {
        }
    }
    state.set("ammo_restock_toggle_key_code",
              pipela::core::state::StateValue{ammo_toggle});
}

void wireNativeWorkerCallbacks(pipela::core::state::AppState& state) {
    pipela::core::workers::WorkerContext::setKillCounterOcrLoader(
        [](const unsigned char* bgr, int w, int h)
            -> std::optional<pipela::core::workers::KillCounterOcrResult> {
            const auto ocr = pipela::core::vision::readKillCounterDigitsBgr(bgr, w, h);
            if (!ocr) {
                return std::nullopt;
            }
            pipela::core::workers::KillCounterOcrResult out;
            if (!ocr->err.empty()) {
                out.poll_detail = ocr->err;
                out.skip = true;
                return out;
            }
            out.prog_txt = ocr->prog_txt;
            out.ok = !ocr->prog_txt.empty();
            return out;
        });

    pipela::core::workers::WorkerContext::setRefreshTargetHwndCallback([&state]() {
        std::intptr_t prev = 0;
        if (auto v = state.get("target_hwnd")) {
            if (const auto* i = std::get_if<int>(&*v)) {
                prev = *i;
            } else if (const auto* l = std::get_if<std::int64_t>(&*v)) {
                prev = static_cast<std::intptr_t>(*l);
            }
        }
        const std::intptr_t next = pipela::core::win32::refreshEternalcityHwndCached(prev);
        state.set("target_hwnd",
                  pipela::core::state::StateValue{static_cast<std::int64_t>(next)});
    });
}

}  // namespace

RuntimeBootstrap::RuntimeBootstrap() {
    attachParentConsole();
    seedStateFromRegistry(state_);
    state_.set("running", pipela::core::state::StateValue{true});
    const auto hwnd = pipela::core::win32::findEternalcityWindow();
    state_.set("target_hwnd",
               pipela::core::state::StateValue{static_cast<std::int64_t>(hwnd)});
}

RuntimeBootstrap::~RuntimeBootstrap() { stop(); }

void RuntimeBootstrap::start() {
    if (started_) {
        return;
    }
    pipela::core::workers::WorkerContext::setSnapshotProvider([]() {
        return pipela::core::registry::RegistrySnapshot::fromStringMap(
            pipela::core::registry::loadAllStringValues());
    });
    wireNativeWorkerCallbacks(state_);

    runtime_ = std::make_unique<pipela::core::workers::WorkerRuntime>(state_);
    runtime_->startAll();
    started_ = true;
    pipela::core::featureTraceEnsureSession();
    pipela::core::featureTraceRuntimeSnapshot(state_, "workers_start");

    std::cout << "[Pipela] C++ workers ON (native exe) — " << pipela::core::appVersion()
              << std::endl;
    if (targetHwnd()) {
        std::cout << "[Pipela] game window OK" << std::endl;
    } else {
        std::cout << "[Pipela] game window — (waiting)" << std::endl;
    }
}

void RuntimeBootstrap::stop() {
    if (!started_) {
        return;
    }
    if (runtime_) {
        runtime_->stopAll();
        runtime_.reset();
    }
    state_.set("running", pipela::core::state::StateValue{false});
    started_ = false;
}

bool RuntimeBootstrap::workersRunning() const {
    return runtime_ && runtime_->running();
}

void RuntimeBootstrap::refreshGameHwnd() {
    const std::intptr_t prev = targetHwnd();
    const std::intptr_t next = pipela::core::win32::refreshEternalcityHwndCached(prev);
    state_.set("target_hwnd", pipela::core::state::StateValue{static_cast<std::int64_t>(next)});
}

std::intptr_t RuntimeBootstrap::targetHwnd() const {
    if (auto v = state_.get("target_hwnd")) {
        if (const auto* i = std::get_if<std::int64_t>(&*v)) {
            return static_cast<std::intptr_t>(*i);
        }
        if (const auto* n = std::get_if<int>(&*v)) {
            return static_cast<std::intptr_t>(*n);
        }
    }
    return 0;
}

}  // namespace pipela::ui::shell
