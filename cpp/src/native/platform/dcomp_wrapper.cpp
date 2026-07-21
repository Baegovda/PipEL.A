#include "pipela/native/dcomp_hud.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include <filesystem>

namespace pipela::native {

namespace {

using HudInitFn = int (*)(unsigned long long);
using HudVoidFn = void (*)();
using HudIconsFn = void (*)(int, int, int);
using HudPosFn = void (*)(int, int);

std::filesystem::path exeAdjacentDll(const wchar_t* dll_name) {
    wchar_t buf[MAX_PATH];
    const DWORD n = GetModuleFileNameW(nullptr, buf, MAX_PATH);
    if (n == 0 || n >= MAX_PATH) {
        return {};
    }
    return std::filesystem::path(buf).parent_path() / dll_name;
}

}  // namespace

DCompHud::DCompHud() = default;

DCompHud::~DCompHud() { shutdown(); }

bool DCompHud::loadDll() {
#ifdef _WIN32
    if (dll_) {
        return true;
    }
    const std::filesystem::path candidates[] = {
        exeAdjacentDll(L"cursor_hud_dcomp.dll"),
        std::filesystem::path("cpp/src/native/hud_dcomp/build/cursor_hud_dcomp.dll"),
        std::filesystem::path("cpp/build/cpp-release/src/native/hud_dcomp/cursor_hud_dcomp.dll"),
        std::filesystem::path("cpp/build/release/src/native/hud_dcomp/cursor_hud_dcomp.dll"),
    };
    for (const auto& p : candidates) {
        if (p.empty() || !std::filesystem::exists(p)) {
            continue;
        }
        dll_ = LoadLibraryW(p.wstring().c_str());
        if (dll_) {
            return true;
        }
    }
#endif
    return false;
}

bool DCompHud::tryLoadAndInit(std::uintptr_t anchor_hwnd) {
#ifdef _WIN32
    if (!loadDll()) {
        return false;
    }
    auto init = reinterpret_cast<HudInitFn>(GetProcAddress(static_cast<HMODULE>(dll_), "hud_init"));
    if (!init) {
        return false;
    }
    if (init(static_cast<unsigned long long>(anchor_hwnd)) != 1) {
        return false;
    }
    ok_ = true;
    anchor_ = anchor_hwnd;
    return true;
#else
    (void)anchor_hwnd;
    return false;
#endif
}

bool DCompHud::ensureInit(std::uintptr_t anchor_hwnd) {
    if (anchor_hwnd == 0) {
        return ok_;
    }
    if (ok_ && anchor_ == anchor_hwnd) {
        return true;
    }
    shutdown();
    return tryLoadAndInit(anchor_hwnd);
}

void DCompHud::shutdown() {
#ifdef _WIN32
    if (ok_ && dll_) {
        if (auto fn = reinterpret_cast<HudVoidFn>(GetProcAddress(static_cast<HMODULE>(dll_), "hud_shutdown"))) {
            fn();
        }
    }
#endif
    ok_ = false;
    anchor_ = 0;
}

void DCompHud::setVisible(bool visible) {
#ifdef _WIN32
    if (!ok_ || !dll_) {
        return;
    }
    using Fn = void (*)(int);
    if (auto fn = reinterpret_cast<Fn>(GetProcAddress(static_cast<HMODULE>(dll_), "hud_set_visible"))) {
        fn(visible ? 1 : 0);
    }
#endif
}

void DCompHud::setIcons(bool move_on, bool fire_on, bool ride_on) {
#ifdef _WIN32
    if (!ok_ || !dll_) {
        return;
    }
    if (auto fn = reinterpret_cast<HudIconsFn>(GetProcAddress(static_cast<HMODULE>(dll_), "hud_set_icons"))) {
        fn(move_on ? 1 : 0, fire_on ? 1 : 0, ride_on ? 1 : 0);
    }
#endif
}

void DCompHud::setPosition(int x_phys, int y_phys) {
#ifdef _WIN32
    if (!ok_ || !dll_) {
        return;
    }
    if (auto fn = reinterpret_cast<HudPosFn>(GetProcAddress(static_cast<HMODULE>(dll_), "hud_set_position"))) {
        fn(x_phys, y_phys);
    }
#endif
}

}  // namespace pipela::native
