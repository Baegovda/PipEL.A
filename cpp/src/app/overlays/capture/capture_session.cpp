#include "capture/capture_session.hpp"

#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/template/apply.hpp"
#include "pipela/core/template/capture_catalog.hpp"
#include "pipela/core/vision/registry_image_loader.hpp"
#include "pipela/core/vision/roi.hpp"
#include "widgets/bgr_image_qt.hpp"

namespace pipela::ui::overlays::capture {

std::optional<FreezeFrame> takeFreezeFrame(std::intptr_t anchor_hwnd) {
    if (!anchor_hwnd) {
        return std::nullopt;
    }
    auto bgr = pipela::core::vision::captureClientBgr(anchor_hwnd);
    if (!bgr || bgr->width < 2 || bgr->height < 2) {
        return std::nullopt;
    }
    FreezeFrame out;
    out.bgr = std::move(*bgr);
    out.pixmap = pipela::app::widgets::pixmapFromBgr(out.bgr, 0, 0);
    return out;
}

std::optional<pipela::core::vision::BgrImage> cropDragSelection(
    const FreezeFrame* freeze, std::intptr_t anchor_hwnd, int x, int y, int w, int h, int client_w,
    int client_h) {
    if (freeze != nullptr) {
        if (auto cropped = pipela::core::vision::cropBgrFromDragRect(freeze->bgr, x, y, w, h,
                                                                     client_w, client_h)) {
            return cropped;
        }
    }
    auto live = pipela::core::vision::captureClientBgr(anchor_hwnd);
    if (!live) {
        return std::nullopt;
    }
    return pipela::core::vision::cropBgrFromDragRect(*live, x, y, w, h, client_w, client_h);
}

bool saveTemplateCapture(const std::string& capture_kind,
                         const pipela::core::vision::BgrImage& cropped) {
    const auto out_path = pipela::core::template_meta::captureOutputPathForKind(capture_kind);
    if (!out_path) {
        return false;
    }
#if defined(PIPELA_HAS_OPENCV)
    if (!pipela::core::vision::writeBgrToPng(cropped, *out_path)) {
        return false;
    }
    return pipela::core::template_meta::applyTemplateCapture(capture_kind, *out_path);
#else
    (void)capture_kind;
    (void)cropped;
    return false;
#endif
}

bool saveRegionSelection(const std::string& region_registry_key, int x, int y, int w, int h,
                         int client_w, int client_h) {
    if (region_registry_key.empty()) {
        return false;
    }
    const auto norm =
        pipela::core::vision::normalizedRoiFromDragRect(x, y, w, h, client_w, client_h);
    const std::string json = pipela::core::registry::formatRegionJson(norm);
    pipela::core::registry::saveStringValue(region_registry_key, json);
    return true;
}

}  // namespace pipela::ui::overlays::capture
