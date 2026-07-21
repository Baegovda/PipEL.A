#pragma once

#include <QString>

#include "overlay_placeholders.hpp"

namespace pipela::ui::overlays {

// AGENT: Holds dock chrome state; sync from game client rect (pipela_qt/qt_side_dock.py parity).
class OverlayManager {
public:
    void syncFromGameClient(std::intptr_t anchor_hwnd,
                            int client_left,
                            int client_top,
                            int client_right,
                            int client_bottom,
                            int dock_w_log,
                            double scale,
                            bool kill_panel_visible,
                            int panel_height_log_override = 0);

    const DockOverlayPlaceholder& dock() const { return dock_; }
    const TitleStripPlaceholder& titleStrip() const { return strip_; }
    const KillCounterFloaterPlaceholder& killFloater() const { return kill_; }

    QString statusSummary() const;

private:
    DockOverlayPlaceholder dock_{};
    TitleStripPlaceholder strip_{};
    KillCounterFloaterPlaceholder kill_{};
};

}  // namespace pipela::ui::overlays
