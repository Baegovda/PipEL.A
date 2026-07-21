#pragma once

#include <cstdint>
#include <optional>
#include <string>

#include <QPixmap>

#include "pipela/core/vision/capture.hpp"

namespace pipela::ui::overlays::capture {

// AGENT: Freeze snapshot + crop + persist — no QWidget (testable core).
struct FreezeFrame {
    pipela::core::vision::BgrImage bgr;
    QPixmap pixmap;
};

std::optional<FreezeFrame> takeFreezeFrame(std::intptr_t anchor_hwnd);

std::optional<pipela::core::vision::BgrImage> cropDragSelection(
    const FreezeFrame* freeze, std::intptr_t anchor_hwnd, int x, int y, int w, int h, int client_w,
    int client_h);

bool saveTemplateCapture(const std::string& capture_kind,
                         const pipela::core::vision::BgrImage& cropped);

bool saveRegionSelection(const std::string& region_registry_key, int x, int y, int w, int h,
                         int client_w, int client_h);

}  // namespace pipela::ui::overlays::capture
