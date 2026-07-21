#pragma once

#include <functional>
#include <string>

namespace pipela::core::input {

// AGENT: Win32 LL mouse hook flags (MSLLHOOKSTRUCT::flags).
constexpr unsigned kLlMouseHookFlagInjected = 0x00000001u;
constexpr unsigned kLlMouseHookFlagLowerIlInjected = 0x00000002u;

inline bool mouseHookFlagsIndicateSynthetic(unsigned flags) {
    return (flags & (kLlMouseHookFlagInjected | kLlMouseHookFlagLowerIlInjected)) != 0u;
}

struct LeftClickControllerDeps {
    std::function<bool(const char* key, bool fallback)> stateBool;
    std::function<void(const char* key, bool value)> setStateBool;
    std::function<int(const char* key, int delta)> incrementInt;
    std::function<int(const char* key, int fallback)> stateInt;
    std::function<bool(const char* key, bool fallback)> registryBool;
    std::function<double(const char* key, double fallback)> registryFloat;
    std::function<bool()> mouseInGameClient;
    std::function<bool()> physicalLeftDown;
    std::function<bool()> synthIgnoreLeft;
    std::function<void(const std::string& terminal_line)> emitTerminalLine;
    std::function<void(const std::string& detail)> trace;
    std::function<void(int click_id, int hold_ms)> scheduleHoldTimer;
    std::function<void(int arm_gen)> scheduleDelayedOffArmTimer;
};

// AGENT: LeftClick hold-to-arm + user-off state machine (core, no Qt).
class LeftClickController {
public:
    explicit LeftClickController(LeftClickControllerDeps deps);

    void resetSessionState();
    void pauseForFlameTrigger();

    // Returns true when the event was handled (caller may skip legacy paths).
    bool onLeftButton(bool pressed, unsigned hook_flags, int x_phys, int y_phys);

    void onHoldTimerFired(int click_id);
    void onDelayedOffArmTimer(int arm_gen);

    // Returns generation id for delayed OFF-arm timer (when synth press while active).
    int scheduleDelayedOffArm();

private:
    bool featureEnabled() const;
    bool active() const;
    bool flameActive() const;
    void setActive(bool on, const char* reason);
    void traceState(const char* event, const std::string& extra) const;
    bool isSynthetic(unsigned hook_flags) const;

    LeftClickControllerDeps deps_;
    bool user_left_pending_{false};
    int left_off_arm_gen_{0};
};

}  // namespace pipela::core::input
