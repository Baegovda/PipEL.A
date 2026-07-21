#include "pipela/core/input/left_click_controller.hpp"

#include <algorithm>
#include <sstream>

namespace pipela::core::input {

namespace {

constexpr double kDefaultHoldSec = 0.15;

std::string boolStr(bool v) { return v ? "1" : "0"; }

}  // namespace

LeftClickController::LeftClickController(LeftClickControllerDeps deps) : deps_(std::move(deps)) {}

void LeftClickController::resetSessionState() {
    user_left_pending_ = false;
    ++left_off_arm_gen_;
    deps_.setStateBool("left_pressed", false);
    deps_.setStateBool("left_click_active", false);
    traceState("reset", "feature_disabled_or_cleared");
}

void LeftClickController::pauseForFlameTrigger() {
    if (!active()) {
        return;
    }
    user_left_pending_ = false;
    ++left_off_arm_gen_;
    setActive(false, "flame_priority");
    deps_.emitTerminalLine("[LeftClick] 자동 클릭 꺼짐 · 플레임 우선");
}

bool LeftClickController::featureEnabled() const {
    return deps_.registryBool("left_click_feature_enabled", true);
}

bool LeftClickController::active() const {
    return deps_.stateBool("left_click_active", false);
}

bool LeftClickController::flameActive() const {
    return deps_.stateBool("flame_trigger_active", false);
}

bool LeftClickController::isSynthetic(unsigned hook_flags) const {
    return mouseHookFlagsIndicateSynthetic(hook_flags);
}

void LeftClickController::traceState(const char* event, const std::string& extra) const {
    if (!deps_.trace) {
        return;
    }
    std::ostringstream oss;
    oss << "event=" << (event ? event : "?") << " feat=" << boolStr(featureEnabled())
        << " active=" << boolStr(active()) << " left_pressed=" << boolStr(deps_.stateBool("left_pressed", false))
        << " user_off_pending=" << boolStr(user_left_pending_) << " " << extra;
    deps_.trace(oss.str());
}

void LeftClickController::setActive(bool on, const char* reason) {
    deps_.setStateBool("left_click_active", on);
    std::ostringstream oss;
    oss << "reason=" << (reason ? reason : "?");
    traceState(on ? "active_on" : "active_off", oss.str());
    if (on) {
        deps_.emitTerminalLine("[LeftClick] 자동 클릭 켜짐");
    }
}

int LeftClickController::scheduleDelayedOffArm() {
    const int arm_gen = ++left_off_arm_gen_;
    traceState("delayed_off_arm_scheduled", "gen=" + std::to_string(arm_gen));
    return arm_gen;
}

bool LeftClickController::onLeftButton(bool pressed, unsigned hook_flags, int x_phys, int y_phys) {
    (void)x_phys;
    (void)y_phys;
    const bool synth = isSynthetic(hook_flags);
    const std::string src = synth ? "SYNTH" : "USER";
    traceState(pressed ? "mouse_down" : "mouse_up",
               "src=" + src + " flags=0x" + std::to_string(hook_flags));

    if (!featureEnabled()) {
        return false;
    }

    if (pressed) {
        if (active()) {
            if (synth) {
                if (deps_.scheduleDelayedOffArmTimer) {
                    deps_.scheduleDelayedOffArmTimer(scheduleDelayedOffArm());
                }
                return true;
            }
            user_left_pending_ = true;
            traceState("user_off_arm", "pending=1");
            return true;
        }
        if (synth) {
            return true;
        }
        if (flameActive()) {
            return false;
        }
        deps_.setStateBool("left_pressed", true);
        const int click_id = deps_.incrementInt("left_click_id", 1);
        traceState("hold_arm_start", "click_id=" + std::to_string(click_id));
        if (deps_.scheduleHoldTimer) {
            const double hold_sec = deps_.registryFloat("left_click_hold_sec", kDefaultHoldSec);
            const int hold_ms = std::max(1, static_cast<int>(hold_sec * 1000.0));
            deps_.scheduleHoldTimer(click_id, hold_ms);
        }
        return true;
    }

    deps_.setStateBool("left_pressed", false);
    if (user_left_pending_) {
        user_left_pending_ = false;
        setActive(false, "user_release_off");
        deps_.emitTerminalLine("[LeftClick] 자동 클릭 꺼짐");
        return true;
    }
    return false;
}

void LeftClickController::onHoldTimerFired(int click_id) {
    if (!featureEnabled()) {
        traceState("hold_timer", "skip feat_off click_id=" + std::to_string(click_id));
        return;
    }
    if (!deps_.stateBool("left_pressed", false)) {
        traceState("hold_timer", "skip not_pressed click_id=" + std::to_string(click_id));
        return;
    }
    const int current_id = deps_.stateInt("left_click_id", 0);
    if (click_id != current_id) {
        traceState("hold_timer", "skip stale click_id=" + std::to_string(click_id) +
                                      " current=" + std::to_string(current_id));
        return;
    }
    if (active() || flameActive()) {
        traceState("hold_timer", "skip already_active_or_flame");
        return;
    }
    deps_.setStateBool("left_pressed", false);
    setActive(true, "hold_timer");
}

void LeftClickController::onDelayedOffArmTimer(int arm_gen) {
    if (arm_gen != left_off_arm_gen_) {
        traceState("delayed_off_arm", "skip stale gen=" + std::to_string(arm_gen));
        return;
    }
    if (!deps_.stateBool("running", true)) {
        return;
    }
    if (!active() || !featureEnabled()) {
        return;
    }
    if (deps_.stateBool("select_mode", false) || !deps_.mouseInGameClient()) {
        return;
    }
    if (deps_.physicalLeftDown && deps_.physicalLeftDown()) {
        user_left_pending_ = true;
        traceState("delayed_off_arm", "user_off_pending=1 physical_down");
    }
}

}  // namespace pipela::core::input
