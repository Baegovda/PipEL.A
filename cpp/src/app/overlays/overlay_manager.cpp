#include "overlay_manager.hpp"

#include <QString>

namespace pipela::ui::overlays {

void OverlayManager::syncFromGameClient(std::intptr_t anchor_hwnd,
                                        int client_left,
                                        int client_top,
                                        int client_right,
                                        int client_bottom,
                                        int dock_w_log,
                                        double scale,
                                        bool kill_panel_visible,
                                        int panel_height_log_override) {
    syncDockChromeFromGameClient(
        dock_, strip_, kill_, anchor_hwnd, client_left, client_top, client_right, client_bottom,
        dock_w_log, scale, kill_panel_visible, panel_height_log_override);
}

QString OverlayManager::statusSummary() const {
    if (!dock_.visible) {
        return QString::fromUtf8("도크: 대기");
    }
    const auto& layout = dock_.last_layout;
    return QString::fromUtf8("도크 x=%1 y=%2 w=%3 | 스트립 우=%4 | KC %5")
        .arg(layout.x_log)
        .arg(layout.y_log)
        .arg(layout.w_log)
        .arg(strip_.strip_right_phys)
        .arg(kill_.visible ? QString::fromUtf8("표시") : QString::fromUtf8("숨김"));
}

}  // namespace pipela::ui::overlays
