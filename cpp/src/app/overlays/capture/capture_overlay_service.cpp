#include "capture/capture_overlay_service.hpp"

#include "capture/capture_confirm_card.hpp"
#include "capture/capture_overlay_view.hpp"
#include "capture/capture_session.hpp"
#include "capture/region_preview_view.hpp"

namespace pipela::ui::overlays::capture {

CaptureOverlayService::CaptureOverlayService(QWidget* host, pipela::core::state::AppState* state)
    : host_(host), state_(state) {
    view_ = std::make_unique<CaptureOverlayView>(nullptr);
    preview_ = std::make_unique<RegionPreviewView>(host);
}

CaptureOverlayService::~CaptureOverlayService() = default;

bool CaptureOverlayService::isDragVisible() const {
    return view_ != nullptr && view_->isVisible();
}

bool CaptureOverlayService::isTemplateCaptureActive(const std::string& capture_kind) const {
    return isDragVisible() && drag_session_ && drag_session_->intent == DragIntent::Template &&
           drag_session_->capture_kind == capture_kind;
}

bool CaptureOverlayService::isRegionSelectActive(const std::string& region_type) const {
    return isDragVisible() && drag_session_ && drag_session_->intent == DragIntent::Region &&
           drag_session_->region_type == region_type;
}

void CaptureOverlayService::emitLog(const QString& msg) const {
    if (log_) {
        log_(msg);
    }
}

void CaptureOverlayService::closePreview() {
    if (preview_) {
        preview_->closePreview();
    }
    if (mode_ == Mode::RegionPreview) {
        mode_ = Mode::Idle;
    }
}

void CaptureOverlayService::closeDrag(bool cancelled) {
    if (view_ && view_->isVisible()) {
        view_->endSession(cancelled);
    }
    freeze_.reset();
    drag_session_.reset();
    anchor_hwnd_ = 0;
    if (mode_ == Mode::TemplateCapture || mode_ == Mode::RegionSelect) {
        mode_ = Mode::Idle;
    }
}

void CaptureOverlayService::closeAll() {
    closeDrag(true);
    closePreview();
    mode_ = Mode::Idle;
}

void CaptureOverlayService::beginDrag(DragSession session, std::intptr_t anchor_hwnd) {
    closeDrag(true);
    closePreview();

    anchor_hwnd_ = anchor_hwnd;
    drag_session_ = std::move(session);
    freeze_ = takeFreezeFrame(anchor_hwnd_);

    QPixmap freeze_px;
    if (freeze_) {
        freeze_px = freeze_->pixmap;
    }

    mode_ = drag_session_->intent == DragIntent::Template ? Mode::TemplateCapture
                                                          : Mode::RegionSelect;

    view_->beginSession(
        anchor_hwnd_, state_, drag_session_->label, freeze_px,
        [this](int x, int y, int w, int h, int cw, int ch) { onDragComplete(x, y, w, h, cw, ch); },
        [this]() { onDragCancelled(); },
        [this](const QString& m) { emitLog(m); });
}

void CaptureOverlayService::onDragCancelled() {
    freeze_.reset();
    drag_session_.reset();
    anchor_hwnd_ = 0;
    mode_ = Mode::Idle;
}

void CaptureOverlayService::onDragComplete(int x, int y, int w, int h, int cw, int ch) {
    if (!drag_session_) {
        mode_ = Mode::Idle;
        freeze_.reset();
        return;
    }

    DragSession session = std::move(*drag_session_);
    const std::intptr_t hwnd = anchor_hwnd_;
    const FreezeFrame* freeze_ptr = freeze_ ? &*freeze_ : nullptr;

    if (session.intent == DragIntent::Region) {
        drag_session_.reset();
        freeze_.reset();
        anchor_hwnd_ = 0;
        mode_ = Mode::Idle;
        if (saveRegionSelection(session.region_registry_key, x, y, w, h, cw, ch)) {
            emitLog(QString::fromUtf8("[%1] 영역 저장 OK").arg(session.label));
            if (session.on_applied) {
                session.on_applied();
            }
        } else {
            emitLog(QString::fromUtf8("[%1] 영역 저장 실패").arg(session.label));
        }
        return;
    }

    auto cropped = cropDragSelection(freeze_ptr, hwnd, x, y, w, h, cw, ch);
    drag_session_.reset();
    freeze_.reset();
    anchor_hwnd_ = 0;
    mode_ = Mode::Idle;

    if (!cropped) {
        emitLog(QString::fromUtf8("[%1] 캡처 실패 — crop").arg(session.label));
        return;
    }

    const pipela::core::vision::BgrImage preview = *cropped;
    const std::string capture_kind = session.capture_kind;
    const QString label = session.label;
    auto on_applied = std::move(session.on_applied);

    showCaptureConfirmCard(
        host_, label, preview, hwnd,
        [this, capture_kind, label, preview, on_applied = std::move(on_applied)](bool accepted) {
            if (!accepted) {
                emitLog(QString::fromUtf8("[%1] 캡처 취소됨").arg(label));
                return;
            }
            if (!saveTemplateCapture(capture_kind, preview)) {
                emitLog(QString::fromUtf8("[%1] 템플릿 저장 실패").arg(label));
                return;
            }
            emitLog(QString::fromUtf8("[%1] 템플릿 저장 OK").arg(label));
            if (on_applied) {
                on_applied();
            }
        });
}

void CaptureOverlayService::startTemplateCapture(const std::string& capture_kind,
                                                 std::intptr_t anchor_hwnd, const QString& label,
                                                 std::function<void()> on_applied) {
    if (isTemplateCaptureActive(capture_kind)) {
        emitLog(QString::fromUtf8("[%1] 캡처 취소").arg(label));
        closeDrag(true);
        return;
    }
    DragSession session;
    session.intent = DragIntent::Template;
    session.capture_kind = capture_kind;
    session.label = label;
    session.on_applied = std::move(on_applied);
    beginDrag(std::move(session), anchor_hwnd);
    emitLog(QString::fromUtf8("[%1] 드래그로 캡처 영역 지정 (Esc 취소)").arg(label));
}

void CaptureOverlayService::startRegionSelect(const std::string& region_type,
                                              const std::string& region_registry_key,
                                              std::intptr_t anchor_hwnd, const QString& label,
                                              std::function<void()> on_applied) {
    if (isRegionSelectActive(region_type)) {
        emitLog(QString::fromUtf8("[%1] 선택 취소").arg(label));
        closeDrag(true);
        return;
    }
    DragSession session;
    session.intent = DragIntent::Region;
    session.region_type = region_type;
    session.region_registry_key = region_registry_key;
    session.label = label;
    session.on_applied = std::move(on_applied);
    beginDrag(std::move(session), anchor_hwnd);
    emitLog(QString::fromUtf8("[%1] 드래그로 영역 지정 (Esc 취소)").arg(label));
}

void CaptureOverlayService::toggleRegionPreview(const std::string& region_type,
                                                const std::string& region_registry_key,
                                                std::intptr_t anchor_hwnd, const QString& label) {
    closeDrag(true);
    if (preview_) {
        preview_->toggle(region_type, region_registry_key, anchor_hwnd, label,
                         [this](const QString& m) { emitLog(m); });
        mode_ = preview_->isActive() ? Mode::RegionPreview : Mode::Idle;
    }
}

}  // namespace pipela::ui::overlays::capture
