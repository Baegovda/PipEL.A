#include "input/hooks_bridge.hpp"

#include <QMetaObject>
#include <QTimer>

#include <chrono>
#include <thread>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include "overlays/cursor_hud_controller.hpp"
#include "pipela/core/feature_trace_log.hpp"
#include "pipela/core/input/left_click_controller.hpp"
#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/input_synth.hpp"
#include "pipela/native/input_hooks.h"

namespace pipela::app::input {

namespace {

constexpr unsigned int kVkF5 = 0x74;
constexpr unsigned int kVkF8 = 0x77;
constexpr int kMouseButtonLeft = 1;
constexpr int kMouseButtonRight = 2;
constexpr int kMouseButtonMiddle = 3;
constexpr int kLeftOffArmDelayMs = 25;

#ifdef _WIN32
bool physicalLeftButtonDown() {
    return (GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0;
}
#else
bool physicalLeftButtonDown() { return false; }
#endif

bool isSyntheticMouseEvent(int button, unsigned hook_flags) {
    if (pipela::core::input::mouseHookFlagsIndicateSynthetic(hook_flags)) {
        return true;
    }
    if (button == kMouseButtonLeft && pipela::core::win32::synthIgnoreLeft()) {
        return true;
    }
    if (button == kMouseButtonRight && pipela::core::win32::synthIgnoreRight()) {
        return true;
    }
    return false;
}

}  // namespace

InputHooksBridge::InputHooksBridge(QObject* parent) : QObject(parent) {
    buildLeftClickController();
}

InputHooksBridge::~InputHooksBridge() { stop(); }

void InputHooksBridge::buildLeftClickController() {
    pipela::core::input::LeftClickControllerDeps deps;
    deps.stateBool = [this](const char* key, bool fallback) { return stateBool(key, fallback); };
    deps.setStateBool = [this](const char* key, bool value) { setStateBool(key, value); };
    deps.incrementInt = [this](const char* key, int delta) { return incrementInt(key, delta); };
    deps.stateInt = [this](const char* key, int fallback) { return stateInt(key, fallback); };
    deps.registryBool = [this](const char* key, bool fallback) { return registryBool(key, fallback); };
    deps.registryFloat = [this](const char* key, double fallback) { return registryFloat(key, fallback); };
    deps.mouseInGameClient = [this]() { return mouseInGameClient(); };
    deps.physicalLeftDown = []() { return physicalLeftButtonDown(); };
    deps.synthIgnoreLeft = []() { return pipela::core::win32::synthIgnoreLeft(); };
    deps.emitTerminalLine = [this](const std::string& line) {
        queueLine(QString::fromUtf8(line.c_str()));
    };
    deps.trace = [](const std::string& detail) {
        pipela::core::featureTraceLog("left_click", detail);
    };
    deps.scheduleHoldTimer = [this](int click_id, int hold_ms) {
        std::thread([this, click_id, hold_ms]() {
            std::this_thread::sleep_for(std::chrono::milliseconds(hold_ms));
            if (left_click_ != nullptr) {
                left_click_->onHoldTimerFired(click_id);
            }
        }).detach();
    };
    deps.scheduleDelayedOffArmTimer = [this](int arm_gen) {
        std::thread([this, arm_gen]() {
            std::this_thread::sleep_for(std::chrono::milliseconds(kLeftOffArmDelayMs));
            if (left_click_ != nullptr) {
                left_click_->onDelayedOffArmTimer(arm_gen);
            }
        }).detach();
    };
    left_click_ = std::make_unique<pipela::core::input::LeftClickController>(std::move(deps));
}

void InputHooksBridge::bindState(pipela::core::state::AppState* state) { state_ = state; }

void InputHooksBridge::setCursorHudController(
    pipela::ui::overlays::CursorHudController* controller) {
    cursor_hud_ = controller;
}

void InputHooksBridge::setQuitCallback(std::function<void()> callback) {
    quit_callback_ = std::move(callback);
}

bool InputHooksBridge::start() {
    if (started_) {
        return true;
    }
    pipela_input_hooks_set_mouse_callback(&InputHooksBridge::onMouse, this);
    pipela_input_hooks_set_keyboard_callback(&InputHooksBridge::onKeyboard, this);
    if (!pipela_input_hooks_start()) {
        return false;
    }
    started_ = true;
    pipela::core::featureTraceLog("hooks", "input_hooks started");
    return true;
}

void InputHooksBridge::stop() {
    if (!started_) {
        return;
    }
    pipela_input_hooks_stop();
    started_ = false;
    pipela::core::featureTraceLog("hooks", "input_hooks stopped");
}

void InputHooksBridge::onMouse(int x, int y, int button, int pressed, unsigned hook_flags,
                               void* user) {
    auto* self = static_cast<InputHooksBridge*>(user);
    if (self == nullptr) {
        return;
    }
    if (button == 0 && pressed == 0) {
        if (self->cursor_hud_ != nullptr) {
            self->cursor_hud_->onHookCursorMove(x, y);
        }
        QMetaObject::invokeMethod(
            self,
            [self, x, y]() { emit self->cursorMoved(x, y); },
            Qt::QueuedConnection);
        return;
    }
    if (button == 0) {
        return;
    }
    // AGENT: LeftClick toggle on hook thread — Qt queue caused press/release reorder + toggle misses.
    if (button == kMouseButtonLeft) {
        self->processLeftClick(x, y, pressed != 0, hook_flags);
        if (self->cursor_hud_ != nullptr) {
            self->cursor_hud_->onHookInputPulse();
        }
        return;
    }
    QMetaObject::invokeMethod(
        self,
        [self, x, y, button, pressed, hook_flags]() {
            self->processMouse(x, y, button, pressed, hook_flags);
        },
        Qt::QueuedConnection);
}

void InputHooksBridge::onKeyboard(unsigned int vk, int is_down, void* user) {
    auto* self = static_cast<InputHooksBridge*>(user);
    if (self == nullptr) {
        return;
    }
    if (self->cursor_hud_ != nullptr) {
        self->cursor_hud_->onHookInputPulse();
    }
    QMetaObject::invokeMethod(
        self,
        [self, vk, is_down]() { self->processKeyboard(vk, is_down); },
        Qt::QueuedConnection);
}

bool InputHooksBridge::registryBool(const char* key, bool fallback) const {
    const auto values = pipela::core::registry::loadAllStringValues();
    const auto it = values.find(key);
    if (it == values.end()) {
        return fallback;
    }
    return pipela::core::registry::parseBool(it->second);
}

double InputHooksBridge::registryFloat(const char* key, double fallback) const {
    const auto values = pipela::core::registry::loadAllStringValues();
    const auto it = values.find(key);
    if (it == values.end() || it->second.empty()) {
        return fallback;
    }
    try {
        return std::stod(it->second);
    } catch (...) {
        return fallback;
    }
}

bool InputHooksBridge::stateBool(const char* key, bool fallback) const {
    if (state_ == nullptr) {
        return fallback;
    }
    if (auto v = state_->get(key)) {
        if (const auto* b = std::get_if<bool>(&*v)) {
            return *b;
        }
    }
    return fallback;
}

void InputHooksBridge::setStateBool(const char* key, bool value) {
    if (state_ != nullptr) {
        state_->set(key, pipela::core::state::StateValue{value});
    }
}

int InputHooksBridge::stateInt(const char* key, int fallback) const {
    if (state_ == nullptr) {
        return fallback;
    }
    if (auto v = state_->get(key)) {
        if (const auto* i = std::get_if<int>(&*v)) {
            return *i;
        }
    }
    return fallback;
}

int InputHooksBridge::incrementInt(const char* key, int delta) {
    if (state_ == nullptr) {
        return 0;
    }
    return state_->incrementInt(key, delta);
}

std::intptr_t InputHooksBridge::targetHwnd() const {
    if (state_ == nullptr) {
        return 0;
    }
    if (auto v = state_->get("target_hwnd")) {
        if (const auto* i = std::get_if<int>(&*v)) {
            return *i;
        }
        if (const auto* l = std::get_if<std::int64_t>(&*v)) {
            return static_cast<std::intptr_t>(*l);
        }
    }
    return 0;
}

bool InputHooksBridge::mouseInGameClient() const {
    const auto hwnd = targetHwnd();
    if (!hwnd) {
        return false;
    }
    return pipela::core::win32::isMouseInClientWindow(hwnd);
}

void InputHooksBridge::pauseLcRhForFlameTrigger() {
    if (state_ == nullptr) {
        return;
    }
    if (left_click_ != nullptr) {
        left_click_->pauseForFlameTrigger();
    }
    if (stateBool("right_hold_active", false)) {
        setStateBool("right_hold_active", false);
        queueLine(QString::fromUtf8("[RightHold] 우클릭 유지 꺼짐 · 플레임 우선"));
    }
}

void InputHooksBridge::processLeftClick(int x, int y, bool is_down, unsigned hook_flags) {
    if (state_ == nullptr || left_click_ == nullptr) {
        return;
    }
    if (stateBool("select_mode", false) || !mouseInGameClient()) {
        return;
    }
    if (!registryBool("left_click_feature_enabled", true)) {
        left_click_->resetSessionState();
        return;
    }
    const bool injected = pipela::core::input::mouseHookFlagsIndicateSynthetic(hook_flags);
    if (!stateBool("left_click_active", false)) {
        if (injected) {
            return;
        }
        if (is_down && pipela::core::win32::synthIgnoreLeft()) {
            return;
        }
    }
    pipela::core::featureTraceLogAt(
        pipela::core::FeatureTraceDepth::Verbose,
        "input",
        std::string("left_click ") + (is_down ? "down" : "up") + " x=" + std::to_string(x) +
            " y=" + std::to_string(y) + " flags=0x" + std::to_string(hook_flags) +
            (injected ? " SYNTH" : " USER"));
    left_click_->onLeftButton(is_down, hook_flags, x, y);
}

void InputHooksBridge::processMouse(int x, int y, int button, int pressed, unsigned hook_flags) {
    if (state_ == nullptr) {
        return;
    }
    if (stateBool("select_mode", false) || !mouseInGameClient()) {
        return;
    }

    const bool is_down = pressed != 0;
    const bool synth = isSyntheticMouseEvent(button, hook_flags);
    pipela::core::featureTraceLogAt(
        pipela::core::FeatureTraceDepth::Verbose,
        "input",
        std::string("mouse btn=") + std::to_string(button) + (is_down ? " down" : " up") + " x=" +
            std::to_string(x) + " y=" + std::to_string(y) + " flags=0x" +
            std::to_string(hook_flags) + (synth ? " SYNTH" : " USER"));

    if (button == kMouseButtonRight) {
        if (isSyntheticMouseEvent(button, hook_flags)) {
            return;
        }
        if (!is_down) {
            return;
        }
        if (!registryBool("right_hold_feature_enabled", true)) {
            return;
        }
        if (stateBool("flame_trigger_active", false) && !stateBool("right_hold_active", false)) {
            return;
        }
        const bool next = !stateBool("right_hold_active", false);
        setStateBool("right_hold_active", next);
        pipela::core::featureTraceLog("right_hold", next ? "USER toggle ON" : "USER toggle OFF");
        queueLine(QString::fromUtf8("[RightHold] %1")
                      .arg(next ? QString::fromUtf8("우클릭 유지 켜짐")
                                : QString::fromUtf8("우클릭 유지 꺼짐")));
        return;
    }

    if (button == kMouseButtonMiddle && is_down) {
        if (isSyntheticMouseEvent(button, hook_flags)) {
            return;
        }
        if (!registryBool("flame_trigger_feature_enabled", false)) {
            return;
        }
        const bool next = !stateBool("flame_trigger_active", false);
        setStateBool("flame_trigger_active", next);
        if (next) {
            pauseLcRhForFlameTrigger();
        }
        pipela::core::featureTraceLog("flame_trigger", next ? "USER toggle ON" : "USER toggle OFF");
        queueLine(QString::fromUtf8("[Flame Trigger] %1")
                      .arg(next ? QString::fromUtf8("켜짐") : QString::fromUtf8("꺼짐")));
    }
}

void InputHooksBridge::processKeyboard(unsigned int vk, int is_down) {
    if (!is_down || state_ == nullptr) {
        return;
    }
    pipela::core::featureTraceLog("input", "key vk=0x" + std::to_string(vk) + " down");
    if (vk == kVkF8) {
        queueLine(QString::fromUtf8("[Pipela] 종료 · F8"));
        setStateBool("running", false);
        emit quitRequested();
        if (quit_callback_) {
            quit_callback_();
        }
        return;
    }
    if (vk == kVkF5) {
        const bool next = !stateBool("reload_active", true);
        setStateBool("reload_active", next);
        if (!next) {
            state_->set("reload_nobullet_arm_until_mono",
                        pipela::core::state::StateValue{0.0});
        }
        pipela::core::registry::saveBoolValue("reload_active", next);
        pipela::core::featureTraceLog("reload", next ? "USER F5 ON" : "USER F5 OFF");
        queueLine(QString::fromUtf8("[Reload] 기능 %1 · F5")
                      .arg(next ? QString::fromUtf8("켜짐") : QString::fromUtf8("꺼짐")));
        return;
    }

    int toggle_vk = 0x75;
    if (auto v = state_->get("ammo_restock_toggle_key_code")) {
        if (const auto* i = std::get_if<int>(&*v)) {
            toggle_vk = *i;
        }
    }
    if (static_cast<int>(vk & 0xFF) == (toggle_vk & 0xFF)) {
        const bool next = !stateBool("ammo_restock_active", false);
        setStateBool("ammo_restock_active", next);
        pipela::core::registry::saveBoolValue("ammo_restock_active", next);
        pipela::core::featureTraceLog("ammo_restock", next ? "USER key ON" : "USER key OFF");
        queueLine(QString::fromUtf8("[Ammo Restock] %1")
                      .arg(next ? QString::fromUtf8("켜짐") : QString::fromUtf8("꺼짐")));
    }
}

void InputHooksBridge::queueLine(const QString& line) {
    QMetaObject::invokeMethod(
        this,
        [this, line]() { emit inputEventQueued(line); },
        Qt::QueuedConnection);
}

}  // namespace pipela::app::input
