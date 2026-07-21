#pragma once

#include <functional>
#include <memory>

#include <QString>

#include "panels/settings/worker_template_panel.hpp"

namespace pipela::core::state {
class AppState;
}

namespace pipela::ui::overlays::capture {
class CaptureOverlayService;
}

namespace pipela::ui::overlays {

// AGENT: Thin facade over capture::CaptureOverlayService (template / ROI / preview).
class TemplateOverlayController {
public:
    enum class SelectMode { Idle, TemplateCapture, RegionSelect, RegionPreview };

    using LogFn = std::function<void(const QString&)>;
    using HwndResolver = std::function<std::intptr_t(const QString& capture_kind)>;

    TemplateOverlayController(QWidget* host, pipela::core::state::AppState* state, HwndResolver resolve_hwnd);

    void setLogCallback(LogFn log);

    void startTemplateCapture(const QString& capture_kind,
                              const pipela::app::panels::settings::TemplateSectionSpec& spec,
                              std::function<void()> on_applied);
    void startRegionSelect(const QString& capture_kind,
                           const pipela::app::panels::settings::TemplateSectionSpec& spec,
                           std::function<void()> on_applied);
    void toggleRegionPreview(const QString& capture_kind,
                             const pipela::app::panels::settings::TemplateSectionSpec& spec);
    void clearMatchRegion(const pipela::app::panels::settings::TemplateSectionSpec& spec);

    void startRegionSelectForType(const QString& region_type, const QString& region_registry_key,
                                  const QString& label, std::function<void()> on_applied = nullptr);
    void toggleRegionPreviewForType(const QString& region_type, const QString& region_registry_key,
                                    const QString& label);
    void clearMatchRegionForKey(const QString& region_registry_key, const QString& label);

    void closeAll();

    SelectMode selectMode() const { return select_mode_; }

    ~TemplateOverlayController();

private:
    void emitLog(const QString& msg) const;
    std::intptr_t resolveAnchor(const QString& capture_kind) const;
    QString labelFor(const pipela::app::panels::settings::TemplateSectionSpec& spec) const;

    QWidget* parent_widget_{nullptr};
    pipela::core::state::AppState* state_{nullptr};
    HwndResolver resolve_hwnd_;
    LogFn log_;
    SelectMode select_mode_{SelectMode::Idle};
    std::unique_ptr<capture::CaptureOverlayService> capture_service_;
};

}  // namespace pipela::ui::overlays
