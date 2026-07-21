#include "capture/region_preview_view.hpp"

#include <cmath>

#include <QPaintEvent>
#include <QPainter>
#include <QTimerEvent>

#include "capture/anchor_overlay_geometry.hpp"
#include "overlay_chrome.hpp"
#include "pipela/core/registry/json_region.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/vision/roi.hpp"
#include "pipela/core/win32/game_windows.hpp"

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pipela::ui::overlays::capture {

RegionPreviewView::RegionPreviewView(QWidget* parent) : QWidget(nullptr), parent_widget_(parent) {
    setWindowFlags(Qt::Tool | Qt::FramelessWindowHint | Qt::WindowStaysOnTopHint |
                   Qt::NoDropShadowWindowHint);
    setAttribute(Qt::WA_TranslucentBackground, false);
    setAttribute(Qt::WA_ShowWithoutActivating, true);
    setAttribute(Qt::WA_TransparentForMouseEvents, true);
}

void RegionPreviewView::toggle(const std::string& region_type,
                               const std::string& region_registry_key,
                               std::intptr_t anchor_hwnd, const QString& label,
                               const std::function<void(const QString&)>& log) {
    if (isActive() && active_region_type_ == region_type) {
        closePreview();
        if (log) {
            log(QString::fromUtf8("[%1] preview OFF").arg(label));
        }
        return;
    }
    closePreview();
    active_region_type_ = region_type;
    region_registry_key_ = region_registry_key;
    anchor_hwnd_ = anchor_hwnd;
    loadRoiPixels();
    if (preview_rect_phys_.width() < 1 || preview_rect_phys_.height() < 1) {
        if (log) {
            log(QString::fromUtf8("[%1] ROI 없음").arg(label));
        }
        active_region_type_.clear();
        return;
    }
    syncGeometry();
    anim_t_ = 0.0;
    if (timer_id_ == 0) {
        timer_id_ = startTimer(40);
    }
    show();
#ifdef _WIN32
    const auto wid = static_cast<HWND>(reinterpret_cast<void*>(winId()));
    if (wid) {
        SetWindowPos(wid, HWND_TOPMOST, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    }
#endif
    if (log) {
        log(QString::fromUtf8("[%1] preview ON").arg(label));
    }
}

void RegionPreviewView::closePreview() {
    if (timer_id_ != 0) {
        killTimer(timer_id_);
        timer_id_ = 0;
    }
    hide();
    active_region_type_.clear();
    region_registry_key_.clear();
    anchor_hwnd_ = 0;
    preview_rect_phys_ = QRect();
}

bool RegionPreviewView::isActive() const {
    return isVisible() && !active_region_type_.empty();
}

void RegionPreviewView::syncGeometry() {
    if (!anchor_hwnd_) {
        return;
    }
    const auto geom = syncWidgetToAnchor(this, anchor_hwnd_);
    dpi_scale_ = geom.dpi_scale;
    const auto cr = pipela::core::win32::getClientRectScreen(anchor_hwnd_);
    client_w_phys_ = std::get<2>(cr) - std::get<0>(cr);
    client_h_phys_ = std::get<3>(cr) - std::get<1>(cr);
}

QRect RegionPreviewView::previewRectLogical() const {
    if (!preview_rect_phys_.isValid()) {
        return {};
    }
    const double sc = dpi_scale_ > 0.01 ? dpi_scale_ : 1.0;
    return QRect(static_cast<int>(std::lround(preview_rect_phys_.x() / sc)),
                 static_cast<int>(std::lround(preview_rect_phys_.y() / sc)),
                 static_cast<int>(std::lround(preview_rect_phys_.width() / sc)),
                 static_cast<int>(std::lround(preview_rect_phys_.height() / sc)));
}

void RegionPreviewView::loadRoiPixels() {
    preview_rect_phys_ = QRect();
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(region_registry_key_);
    if (it == all.end() || it->second.empty()) {
        return;
    }
    const auto region = pipela::core::registry::parseRegionJson(it->second);
    if (!region || !anchor_hwnd_) {
        return;
    }
    if (client_w_phys_ < 1 || client_h_phys_ < 1) {
        const auto cr = pipela::core::win32::getClientRectScreen(anchor_hwnd_);
        client_w_phys_ = std::get<2>(cr) - std::get<0>(cr);
        client_h_phys_ = std::get<3>(cr) - std::get<1>(cr);
    }
    const auto px = pipela::core::vision::regionPixels(client_w_phys_, client_h_phys_, region->data());
    if (!px) {
        return;
    }
    preview_rect_phys_ = QRect((*px)[0], (*px)[1], (*px)[2], (*px)[3]);
}

void RegionPreviewView::paintEvent(QPaintEvent* event) {
    Q_UNUSED(event);
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing, true);
    const QRect logical = previewRectLogical();
    if (logical.isValid()) {
        paintRegionPreviewBox(painter, logical, anim_t_);
    }
}

void RegionPreviewView::timerEvent(QTimerEvent* event) {
    if (event->timerId() == timer_id_) {
        anim_t_ += 0.05;
        if (anchor_hwnd_) {
            syncGeometry();
            loadRoiPixels();
        }
        update();
    }
    QWidget::timerEvent(event);
}

}  // namespace pipela::ui::overlays::capture
