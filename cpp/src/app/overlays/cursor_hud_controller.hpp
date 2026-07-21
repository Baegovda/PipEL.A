#pragma once

#include <QObject>
#include <QTimer>

#include <atomic>

namespace pipela::core::state {
class AppState;
}
namespace pipela::native {
class DCompHud;
}

namespace pipela::ui::overlays {
class FlameHudPopup;

// AGENT: Hook-driven DComp cursor HUD — parity with pipela_qt/cursor_hud.py QtCursorHud.
class CursorHudController : public QObject {
    Q_OBJECT
public:
    explicit CursorHudController(pipela::native::DCompHud* hud,
                                 pipela::core::state::AppState* state,
                                 QObject* parent = nullptr);

    // Hook thread — coalesced position + schedules Qt sync (no timer polling).
    void onHookCursorMove(int x_phys, int y_phys);
    void onHookInputPulse();

    std::intptr_t refreshTargetHwnd();

private:
    bool dcompEnabled() const;
    bool stateBool(const char* key, bool fallback) const;
    bool foregroundOk(std::intptr_t target_hwnd, int x, int y) const;
    void parkHidden();
    void parkAllHidden();
    void syncFlamePopup(std::intptr_t target_hwnd, int x, int y);
    double stateDouble(const char* key, double fallback) const;
    int stateInt(const char* key, int fallback) const;
    void syncFromHook(int x, int y);
    void tickFlamePopupOnly();

    pipela::native::DCompHud* hud_{nullptr};
    pipela::core::state::AppState* state_{nullptr};
    QTimer* flame_timer_{nullptr};
    std::atomic<int> hook_x_{0};
    std::atomic<int> hook_y_{0};
    std::atomic<bool> hook_has_xy_{false};
    std::atomic<bool> hook_sync_pending_{false};
    std::atomic<bool> icons_live_{false};
    std::intptr_t cached_hwnd_{0};
    double cached_hwnd_mono_{0.0};
    FlameHudPopup* flame_popup_{nullptr};
};

}  // namespace pipela::ui::overlays
