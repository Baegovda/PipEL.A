#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/window_ops.hpp"

#include <algorithm>
#include <chrono>
#include <map>
#include <tuple>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::core::win32 {

void forceToolwindowExstyle(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    constexpr int kGwlExstyle = -20;
    constexpr LONG kWsExToolwindow = 0x00000080L;
    constexpr LONG kWsExAppwindow = 0x00040000L;
    const LONG style = GetWindowLongW(who, kGwlExstyle);
    const LONG new_style = (style | kWsExToolwindow) & ~kWsExAppwindow;
    if (new_style == style) {
        return;
    }
    SetWindowLongW(who, kGwlExstyle, new_style);
    constexpr UINT kSwpFlags =
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED;
    SetWindowPos(who, nullptr, 0, 0, 0, 0, kSwpFlags);
#else
    (void)hwnd;
#endif
}

void setWindowOwner(std::intptr_t hwnd_owned, std::intptr_t hwnd_owner) {
#ifdef _WIN32
    if (!hwnd_owned || !isWindow(hwnd_owned)) {
        return;
    }
    HWND owned = reinterpret_cast<HWND>(hwnd_owned);
    HWND owner = nullptr;
    if (hwnd_owner != 0) {
        if (!isWindow(hwnd_owner)) {
            return;
        }
        owner = reinterpret_cast<HWND>(hwnd_owner);
    }
    constexpr int kGwlHwndparent = -8;
    if (owner != nullptr) {
        SetWindowLongPtrW(owned, kGwlHwndparent, reinterpret_cast<LONG_PTR>(owner));
    } else {
        SetWindowLongPtrW(owned, kGwlHwndparent, 0);
    }
    constexpr UINT kSwpFlags =
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED;
    SetWindowPos(owned, nullptr, 0, 0, 0, 0, kSwpFlags);
#else
    (void)hwnd_owned;
    (void)hwnd_owner;
#endif
}

void windowRestoreNormal(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return;
    }
    ShowWindow(reinterpret_cast<HWND>(hwnd), SW_RESTORE);
#else
    (void)hwnd;
#endif
}

void windowMinimize(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return;
    }
    ShowWindow(reinterpret_cast<HWND>(hwnd), SW_MINIMIZE);
#else
    (void)hwnd;
#endif
}

void windowMaximizeOrRestore(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    if (IsZoomed(who)) {
        ShowWindow(who, SW_RESTORE);
    } else {
        ShowWindow(who, SW_MAXIMIZE);
    }
#else
    (void)hwnd;
#endif
}

void windowPostClose(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return;
    }
    PostMessageW(reinterpret_cast<HWND>(hwnd), WM_CLOSE, 0, 0);
#else
    (void)hwnd;
#endif
}

std::optional<std::tuple<int, int, int, int>> getMonitorWorkRectPhys(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return std::nullopt;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    HMONITOR mon = MonitorFromWindow(who, MONITOR_DEFAULTTONEAREST);
    if (!mon) {
        return std::nullopt;
    }
    MONITORINFO mi{};
    mi.cbSize = sizeof(mi);
    if (!GetMonitorInfoW(mon, &mi)) {
        return std::nullopt;
    }
    return std::make_tuple(static_cast<int>(mi.rcWork.left),
                           static_cast<int>(mi.rcWork.top),
                           static_cast<int>(mi.rcWork.right),
                           static_cast<int>(mi.rcWork.bottom));
#else
    (void)hwnd;
    return std::nullopt;
#endif
}

void setWindowOuterRect(std::intptr_t hwnd, int x, int y, int w, int h) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd) || w < 1 || h < 1) {
        return;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    constexpr UINT kFlags = SWP_NOZORDER | SWP_NOACTIVATE;
    SetWindowPos(who, nullptr, x, y, w, h, kFlags);
#else
    (void)hwnd;
    (void)x;
    (void)y;
    (void)w;
    (void)h;
#endif
}

void moveOuterWindow(std::intptr_t hwnd, int x_phys, int y_phys) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    constexpr UINT kFlags = SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE;
    SetWindowPos(who, nullptr, x_phys, y_phys, 0, 0, kFlags);
#else
    (void)hwnd;
    (void)x_phys;
    (void)y_phys;
#endif
}

void setWindowTopmost(std::intptr_t hwnd, bool topmost) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    HWND insert_after = topmost ? HWND_TOPMOST : HWND_NOTOPMOST;
    constexpr UINT kFlags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE;
    SetWindowPos(who, insert_after, 0, 0, 0, 0, kFlags);
#else
    (void)hwnd;
    (void)topmost;
#endif
}

void showWindowNoActivate(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    if (IsIconic(who)) {
        ShowWindow(who, SW_RESTORE);
    }
    ShowWindow(who, SW_SHOWNA);
#else
    (void)hwnd;
#endif
}

namespace {

constexpr double kSwpZorderPairMinSec = 0.012;
std::map<std::pair<std::intptr_t, std::intptr_t>, double>& swposZLastMono() {
    static std::map<std::pair<std::intptr_t, std::intptr_t>, double> cache;
    return cache;
}

double monotonicSeconds() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

}  // namespace

void setWindowZOrderDirectlyAbove(std::intptr_t hwnd_above, std::intptr_t hwnd_below, bool force) {
#ifdef _WIN32
    if (!hwnd_above || !hwnd_below || hwnd_above == hwnd_below) {
        return;
    }
    if (!isWindow(hwnd_above) || !isWindow(hwnd_below)) {
        return;
    }
    const auto pair = std::make_pair(hwnd_above, hwnd_below);
    const double now = monotonicSeconds();
    auto& cache = swposZLastMono();
    const auto it = cache.find(pair);
    if (!force && it != cache.end() && now - it->second < kSwpZorderPairMinSec) {
        return;
    }
    HWND above = reinterpret_cast<HWND>(hwnd_above);
    HWND below = reinterpret_cast<HWND>(hwnd_below);
    constexpr UINT kFlags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE;
    SetWindowPos(above, below, 0, 0, 0, 0, kFlags);
    cache[pair] = now;
    while (cache.size() > 64) {
        cache.erase(cache.begin());
    }
#else
    (void)hwnd_above;
    (void)hwnd_below;
    (void)force;
#endif
}

namespace {

std::tuple<int, int, int, int> dockOuterTouchWorkBounds(std::intptr_t hwnd_anchor) {
    constexpr int kHuge = 1000000000;
    int wl = 0;
    int wt = 0;
    int wr = kHuge;
    int wb = kHuge;
    if (const auto work = getMonitorWorkRectPhys(hwnd_anchor)) {
        wl = std::get<0>(*work);
        wt = std::get<1>(*work);
        wr = std::get<2>(*work);
        wb = std::get<3>(*work);
    }
    return {wl, wt, wr, wb};
}

}  // namespace

std::tuple<int, int, int, int> dockOuterRectTouchClientLeft(std::intptr_t hwnd_anchor,
                                                            int client_left_phys,
                                                            int y,
                                                            int w_phys,
                                                            int h_phys) {
    const auto [wl, wt, wr, wb] = dockOuterTouchWorkBounds(hwnd_anchor);
    const int snap = client_left_phys;
    int w_t = std::max(8, w_phys);
    int h = std::max(1, h_phys);
    h = std::min(h, std::max(1, wb - wt));
    y = std::max(wt, std::min(y, wb - h));
    int x = std::max(wl, snap - w_t);
    int w = snap - x;
    if (w < 8) {
        w = 8;
        x = snap - w;
        if (x < wl) {
            x = wl;
            w = snap - x;
        }
    }
    if (x + w > wr) {
        w = std::max(8, wr - x);
    }
    return {x, y, w, h};
}

std::tuple<int, int, int, int> dockOuterRectTouchClientRight(std::intptr_t hwnd_anchor,
                                                             int client_right_phys,
                                                             int y,
                                                             int w_phys,
                                                             int h_phys) {
    const auto [wl, wt, wr, wb] = dockOuterTouchWorkBounds(hwnd_anchor);
    const int snap = client_right_phys;
    const int w_t = std::max(8, w_phys);
    int h = std::max(1, h_phys);
    h = std::min(h, std::max(1, wb - wt));
    y = std::max(wt, std::min(y, wb - h));
    int x = std::max(wl, snap);
    const int avail = wr - x;
    int w = 0;
    if (avail >= 8) {
        w = std::max(8, std::min(w_t, avail));
    } else if (avail > 0) {
        w = std::max(1, std::min(w_t, avail));
    } else {
        w = std::min(w_t, 8);
    }
    if (x + w > wr) {
        w = std::max(1, wr - x);
    }
    return {x, y, w, h};
}

bool centerOuterWindowOnMonitorWorkArea(std::intptr_t hwnd) {
#ifdef _WIN32
    if (!hwnd || !isWindow(hwnd)) {
        return false;
    }
    if (isWindowMinimized(hwnd)) {
        return false;
    }
    HWND who = reinterpret_cast<HWND>(hwnd);
    if (IsZoomed(who)) {
        return true;
    }
    RECT wr{};
    if (!GetWindowRect(who, &wr)) {
        return false;
    }
    const int ww = wr.right - wr.left;
    const int wh = wr.bottom - wr.top;
    if (ww < 8 || wh < 8) {
        return false;
    }
    const auto work = getMonitorWorkRectPhys(hwnd);
    if (!work) {
        return false;
    }
    const int wl = std::get<0>(*work);
    const int wt = std::get<1>(*work);
    const int wrx = std::get<2>(*work);
    const int wry = std::get<3>(*work);
    const int avail_w = wrx - wl;
    const int avail_h = wry - wt;
    int new_x = wl + std::max(0, (avail_w - ww) / 2);
    int new_y = wt + std::max(0, (avail_h - wh) / 2);
    new_x = std::max(wl, std::min(new_x, wrx - ww));
    new_y = std::max(wt, std::min(new_y, wry - wh));
    constexpr UINT kFlags = SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE;
    SetWindowPos(who, nullptr, new_x, new_y, 0, 0, kFlags);
    return true;
#else
    (void)hwnd;
    return false;
#endif
}

}  // namespace pipela::core::win32
