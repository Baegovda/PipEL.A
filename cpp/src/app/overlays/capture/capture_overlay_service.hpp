#pragma once

#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>

#include <QString>

class QWidget;

#include "capture/capture_session.hpp"

namespace pipela::core::state {
class AppState;
}

namespace pipela::ui::overlays::capture {

class CaptureOverlayView;
class RegionPreviewView;

// AGENT: Unified capture / ROI / preview orchestrator — replaces legacy overlay trio.
class CaptureOverlayService {
public:
    enum class Mode { Idle, TemplateCapture, RegionSelect, RegionPreview };

    using LogFn = std::function<void(const QString&)>;

    CaptureOverlayService(QWidget* host, pipela::core::state::AppState* state);
    ~CaptureOverlayService();

    void setLog(LogFn log) { log_ = std::move(log); }

    Mode mode() const { return mode_; }

    bool isDragVisible() const;
    bool isTemplateCaptureActive(const std::string& capture_kind) const;
    bool isRegionSelectActive(const std::string& region_type) const;

    void startTemplateCapture(const std::string& capture_kind, std::intptr_t anchor_hwnd,
                              const QString& label, std::function<void()> on_applied);

    void startRegionSelect(const std::string& region_type, const std::string& region_registry_key,
                           std::intptr_t anchor_hwnd, const QString& label,
                           std::function<void()> on_applied);

    void toggleRegionPreview(const std::string& region_type,
                             const std::string& region_registry_key, std::intptr_t anchor_hwnd,
                             const QString& label);

    void closePreview();
    void closeDrag(bool cancelled);
    void closeAll();

private:
    enum class DragIntent { Template, Region };

    struct DragSession {
        DragIntent intent{DragIntent::Template};
        std::string capture_kind;
        std::string region_type;
        std::string region_registry_key;
        QString label;
        std::function<void()> on_applied;
    };

    void emitLog(const QString& msg) const;
    void beginDrag(DragSession session, std::intptr_t anchor_hwnd);
    void onDragComplete(int x, int y, int w, int h, int cw, int ch);
    void onDragCancelled();

    QWidget* host_{nullptr};
    pipela::core::state::AppState* state_{nullptr};
    LogFn log_;
    Mode mode_{Mode::Idle};
    std::unique_ptr<CaptureOverlayView> view_;
    std::unique_ptr<RegionPreviewView> preview_;
    std::optional<FreezeFrame> freeze_;
    std::optional<DragSession> drag_session_;
    std::intptr_t anchor_hwnd_{0};
};

}  // namespace pipela::ui::overlays::capture
