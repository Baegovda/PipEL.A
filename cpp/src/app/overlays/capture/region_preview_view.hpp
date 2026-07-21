#pragma once

#include <cstdint>
#include <functional>
#include <string>

#include <QString>
#include <QWidget>

namespace pipela::ui::overlays::capture {

// AGENT: Saved ROI pulse preview — top-level, shares anchor geometry helper.
class RegionPreviewView : public QWidget {
    Q_OBJECT
public:
    explicit RegionPreviewView(QWidget* parent = nullptr);

    void toggle(const std::string& region_type, const std::string& region_registry_key,
                std::intptr_t anchor_hwnd, const QString& label,
                const std::function<void(const QString&)>& log);

    void closePreview();
    bool isActive() const;
    const std::string& activeRegionType() const { return active_region_type_; }

protected:
    void paintEvent(QPaintEvent* event) override;
    void timerEvent(QTimerEvent* event) override;

private:
    void syncGeometry();
    void loadRoiPixels();
    QRect previewRectLogical() const;

    QWidget* parent_widget_{nullptr};
    std::string active_region_type_;
    std::string region_registry_key_;
    std::intptr_t anchor_hwnd_{0};
    QRect preview_rect_phys_;
    double dpi_scale_{1.0};
    int client_w_phys_{0};
    int client_h_phys_{0};
    int timer_id_{0};
    double anim_t_{0.0};
};

}  // namespace pipela::ui::overlays::capture
