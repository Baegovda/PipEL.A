#pragma once

#include <cstdint>
#include <optional>
#include <tuple>

namespace pipela::core::win32 {

// Hide top-level Qt windows from taskbar / Alt+Tab (WS_EX_TOOLWINDOW).
void forceToolwindowExstyle(std::intptr_t hwnd);

void setWindowOwner(std::intptr_t hwnd_owned, std::intptr_t hwnd_owner);
void windowRestoreNormal(std::intptr_t hwnd);
void windowMinimize(std::intptr_t hwnd);
void windowMaximizeOrRestore(std::intptr_t hwnd);
void windowPostClose(std::intptr_t hwnd);

// Monitor work area in screen coords (rcWork). Empty on failure.
std::optional<std::tuple<int, int, int, int>> getMonitorWorkRectPhys(std::intptr_t hwnd);

// SetWindowPos outer rect after Qt geometry (Python win32_set_window_outer_rect).
void setWindowOuterRect(std::intptr_t hwnd, int x, int y, int w, int h);

// Move outer window without resizing (screen physical coords).
void moveOuterWindow(std::intptr_t hwnd, int x_phys, int y_phys);

void showWindowNoActivate(std::intptr_t hwnd);

void setWindowTopmost(std::intptr_t hwnd, bool topmost);

void setWindowZOrderDirectlyAbove(std::intptr_t hwnd_above, std::intptr_t hwnd_below, bool force = false);

std::tuple<int, int, int, int> dockOuterRectTouchClientLeft(std::intptr_t hwnd_anchor,
                                                            int client_left_phys,
                                                            int y,
                                                            int w_phys,
                                                            int h_phys);

std::tuple<int, int, int, int> dockOuterRectTouchClientRight(std::intptr_t hwnd_anchor,
                                                             int client_right_phys,
                                                             int y,
                                                             int w_phys,
                                                             int h_phys);

// Center outer window on its monitor work area (Python center_outer_window_on_monitor_work_area).
bool centerOuterWindowOnMonitorWorkArea(std::intptr_t hwnd);

}  // namespace pipela::core::win32
