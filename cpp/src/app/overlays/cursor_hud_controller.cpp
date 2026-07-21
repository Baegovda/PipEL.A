#include "overlays/cursor_hud_controller.hpp"

#include <chrono>
#include <cstdlib>

#include <QMetaObject>
#include <QString>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include "overlays/flame_hud_popup.hpp"
#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/native/dcomp_hud.hpp"

namespace pipela::ui::overlays {

namespace {

double monoNow() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

#ifdef _WIN32
bool capsLockOn() {
    return (GetKeyState(VK_CAPITAL) & 1) != 0;
}

bool tryCursorPos(int* x, int* y) {
    POINT pt{};
    if (!GetCursorPos(&pt)) {
        return false;
    }
    *x = static_cast<int>(pt.x);
    *y = static_cast<int>(pt.y);
    return true;
}
#endif

QString formatFlameRuntimeHms(double sec) {
    sec = std::max(0.0, sec);
    const int total = static_cast<int>(sec);
    const int s = total % 60;
    const int m = (total / 60) % 60;
    const int h = total / 3600;
    if (h > 0) {
        return QString::fromUtf8("%1:%2:%3")
            .arg(h)
            .arg(m, 2, 10, QChar('0'))
            .arg(s, 2, 10, QChar('0'));
    }
    return QString::fromUtf8("%1:%2").arg(m).arg(s, 2, 10, QChar('0'));
}

}  // namespace

CursorHudController::CursorHudController(pipela::native::DCompHud* hud,
                                         pipela::core::state::AppState* state, QObject* parent)
    : QObject(parent), hud_(hud), state_(state) {
    flame_popup_ = new FlameHudPopup();
    flame_timer_ = new QTimer(this);
    flame_timer_->setInterval(250);
    connect(flame_timer_, &QTimer::timeout, this, &CursorHudController::tickFlamePopupOnly);
    flame_timer_->start();
}

void CursorHudController::onHookCursorMove(int x_phys, int y_phys) {
    if (x_phys == 0 && y_phys == 0) {
        return;
    }
    hook_x_.store(x_phys, std::memory_order_relaxed);
    hook_y_.store(y_phys, std::memory_order_relaxed);
    hook_has_xy_.store(true, std::memory_order_release);

    if (icons_live_.load(std::memory_order_acquire) && hud_ != nullptr && hud_->ok()) {
        hud_->setPosition(x_phys, y_phys);
    }

    bool expected = false;
    if (!hook_sync_pending_.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) {
        return;
    }
    QMetaObject::invokeMethod(
        this,
        [this]() {
            hook_sync_pending_.store(false, std::memory_order_release);
            const int x = hook_x_.load(std::memory_order_relaxed);
            const int y = hook_y_.load(std::memory_order_relaxed);
            if (!hook_has_xy_.load(std::memory_order_acquire)) {
                return;
            }
            syncFromHook(x, y);
        },
        Qt::QueuedConnection);
}

void CursorHudController::onHookInputPulse() {
    bool expected = false;
    if (!hook_sync_pending_.compare_exchange_strong(expected, true, std::memory_order_acq_rel)) {
        return;
    }
    QMetaObject::invokeMethod(
        this,
        [this]() {
            hook_sync_pending_.store(false, std::memory_order_release);
            int x = hook_x_.load(std::memory_order_relaxed);
            int y = hook_y_.load(std::memory_order_relaxed);
            if (!hook_has_xy_.load(std::memory_order_acquire)) {
#ifdef _WIN32
                if (!tryCursorPos(&x, &y)) {
                    return;
                }
                hook_x_.store(x, std::memory_order_relaxed);
                hook_y_.store(y, std::memory_order_relaxed);
                hook_has_xy_.store(true, std::memory_order_release);
#else
                return;
#endif
            }
            syncFromHook(x, y);
        },
        Qt::QueuedConnection);
}

std::intptr_t CursorHudController::refreshTargetHwnd() {
    const double now = monoNow();
    if (cached_hwnd_ != 0 && (now - cached_hwnd_mono_) < 0.042) {
        if (pipela::core::win32::isWindow(cached_hwnd_)) {
            return cached_hwnd_;
        }
    }
    std::intptr_t prev = cached_hwnd_;
    if (state_ != nullptr) {
        if (auto v = state_->get("target_hwnd")) {
            if (const auto* i = std::get_if<int>(&*v)) {
                prev = *i;
            } else if (const auto* l = std::get_if<std::int64_t>(&*v)) {
                prev = static_cast<std::intptr_t>(*l);
            }
        }
    }
    const std::intptr_t next = pipela::core::win32::refreshEternalcityHwndCached(prev);
    cached_hwnd_ = next;
    cached_hwnd_mono_ = now;
    if (state_ != nullptr) {
        state_->set("target_hwnd",
                    pipela::core::state::StateValue{static_cast<std::int64_t>(next)});
    }
    return next;
}

bool CursorHudController::dcompEnabled() const {
    const char* raw = std::getenv("PIPELA_CURSOR_HUD_DCOMP");
    if (raw == nullptr || raw[0] == '\0') {
        return true;
    }
    const std::string v(raw);
    return !(v == "0" || v == "false" || v == "off" || v == "no");
}

bool CursorHudController::stateBool(const char* key, bool fallback) const {
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

double CursorHudController::stateDouble(const char* key, double fallback) const {
    if (state_ == nullptr) {
        return fallback;
    }
    if (auto v = state_->get(key)) {
        if (const auto* d = std::get_if<double>(&*v)) {
            return *d;
        }
        if (const auto* i = std::get_if<int>(&*v)) {
            return static_cast<double>(*i);
        }
    }
    return fallback;
}

int CursorHudController::stateInt(const char* key, int fallback) const {
    if (state_ == nullptr) {
        return fallback;
    }
    if (auto v = state_->get(key)) {
        if (const auto* i = std::get_if<int>(&*v)) {
            return *i;
        }
        if (const auto* l = std::get_if<std::int64_t>(&*v)) {
            return static_cast<int>(*l);
        }
    }
    return fallback;
}

bool CursorHudController::foregroundOk(std::intptr_t target_hwnd, int x, int y) const {
    if (!target_hwnd || !pipela::core::win32::isWindow(target_hwnd)) {
        return false;
    }
#ifdef _WIN32
    const HWND fg = GetForegroundWindow();
    if (fg != nullptr) {
        if (reinterpret_cast<std::intptr_t>(fg) == target_hwnd) {
            return true;
        }
    }
#endif
    return pipela::core::win32::isMouseInClientWindow(target_hwnd) ||
           (x != 0 || y != 0);
}

void CursorHudController::parkHidden() {
    icons_live_.store(false, std::memory_order_release);
    if (hud_ != nullptr && hud_->ok()) {
        hud_->setVisible(false);
    }
}

void CursorHudController::parkAllHidden() {
    parkHidden();
    if (flame_popup_ != nullptr) {
        flame_popup_->parkHidden();
    }
}

void CursorHudController::syncFlamePopup(std::intptr_t /*target_hwnd*/, int x, int y) {
    if (flame_popup_ == nullptr || state_ == nullptr) {
        return;
    }
    if (!stateBool("flame_trigger_active", false)) {
        flame_popup_->parkHidden();
        return;
    }
    const auto values = pipela::core::registry::loadAllStringValues();
    bool merc_on = false;
    const auto merc_it = values.find("merc_fire_enabled");
    if (merc_it != values.end()) {
        merc_on = pipela::core::registry::parseBool(merc_it->second);
    }
    const QString merc_label = merc_on ? QString::fromUtf8("ON") : QString::fromUtf8("OFF");
    const int press_cnt = stateInt("flame_trigger_press_count", 0);
    const double iv_sec = stateDouble("flame_trigger_last_press_interval_sec", 0.0);
    const int reload_cnt = stateInt("flame_trigger_session_reload_count", 0);
    const double trig_t = stateDouble("flame_trigger_last_reload_trigger_time", 0.0);
    const double elapsed = trig_t > 0.0 ? (monoNow() - trig_t) : 0.0;
    flame_popup_->setFlameLines(QString::fromUtf8("Flame Trigger 작동 중!"),
                                QString::fromUtf8("Merc Fire %1 : %2 : %3초")
                                    .arg(merc_label)
                                    .arg(press_cnt)
                                    .arg(iv_sec, 0, 'f', 1),
                                QString::fromUtf8("Reload : %1 (%2)")
                                    .arg(reload_cnt)
                                    .arg(formatFlameRuntimeHms(elapsed)));
    flame_popup_->placeAtCursorHotspot(x, y);
}

void CursorHudController::syncFromHook(int x, int y) {
    if (state_ == nullptr) {
        parkAllHidden();
        return;
    }
    if (!stateBool("running", true) || stateBool("select_mode", false)) {
        parkAllHidden();
        return;
    }
    const std::intptr_t hwnd = refreshTargetHwnd();
    if (!hwnd) {
        parkAllHidden();
        return;
    }
    if (x == 0 && y == 0) {
        return;
    }
    if (!foregroundOk(hwnd, x, y)) {
        parkAllHidden();
        return;
    }

    const bool move_on = stateBool("left_click_active", false);
    const bool fire_on = stateBool("right_hold_active", false);
#ifdef _WIN32
    const bool ride_on = capsLockOn();
#else
    const bool ride_on = false;
#endif
    const bool icons_on = move_on || fire_on || ride_on;

    if (hud_ != nullptr && dcompEnabled()) {
        if (hud_->ensureInit(static_cast<std::uintptr_t>(hwnd))) {
            hud_->setIcons(move_on, fire_on, ride_on);
            if (icons_on) {
                icons_live_.store(true, std::memory_order_release);
                hud_->setVisible(true);
                hud_->setPosition(x, y);
            } else {
                parkHidden();
            }
        } else {
            parkHidden();
        }
    } else {
        parkHidden();
    }
    syncFlamePopup(hwnd, x, y);
}

void CursorHudController::tickFlamePopupOnly() {
    if (state_ == nullptr || flame_popup_ == nullptr) {
        return;
    }
    if (!stateBool("flame_trigger_active", false)) {
        return;
    }
    const int x = hook_x_.load(std::memory_order_relaxed);
    const int y = hook_y_.load(std::memory_order_relaxed);
    if (!hook_has_xy_.load(std::memory_order_acquire)) {
        return;
    }
    syncFlamePopup(refreshTargetHwnd(), x, y);
}

}  // namespace pipela::ui::overlays
