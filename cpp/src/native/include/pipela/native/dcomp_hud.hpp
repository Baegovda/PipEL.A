#pragma once

#include <cstdint>

namespace pipela::native {

// AGENT: C++ wrapper for cursor_hud_dcomp.dll (Phase 3 — replaces ctypes from C++ UI).
class DCompHud {
public:
    DCompHud();
    ~DCompHud();

    bool tryLoadAndInit(std::uintptr_t anchor_hwnd = 0);
    bool ensureInit(std::uintptr_t anchor_hwnd);
    void shutdown();

    void setVisible(bool visible);
    void setIcons(bool move_on, bool fire_on, bool ride_on);
    void setPosition(int x_phys, int y_phys);

    bool ok() const { return ok_; }

private:
    bool loadDll();
    void* dll_{nullptr};
    bool ok_{false};
    std::uintptr_t anchor_{0};
};

}  // namespace pipela::native
