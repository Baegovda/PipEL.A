#include "template_overlay_controller.hpp"

#include "capture/capture_overlay_service.hpp"
#include "pipela/core/template/apply.hpp"
#include "pipela/core/template/region_dispatch.hpp"

namespace pipela::ui::overlays {

TemplateOverlayController::TemplateOverlayController(QWidget* parent,
                                                     pipela::core::state::AppState* state,
                                                     HwndResolver resolve_hwnd)
    : parent_widget_(parent), state_(state), resolve_hwnd_(std::move(resolve_hwnd)) {
    capture_service_ = std::make_unique<capture::CaptureOverlayService>(parent, state);
}

TemplateOverlayController::~TemplateOverlayController() = default;

void TemplateOverlayController::setLogCallback(LogFn log) {
    log_ = std::move(log);
    if (capture_service_ && log_) {
        capture_service_->setLog(log_);
    }
}

void TemplateOverlayController::emitLog(const QString& msg) const {
    if (log_) {
        log_(msg);
    }
}

std::intptr_t TemplateOverlayController::resolveAnchor(const QString& capture_kind) const {
    if (resolve_hwnd_) {
        return resolve_hwnd_(capture_kind);
    }
    return 0;
}

QString TemplateOverlayController::labelFor(
    const pipela::app::panels::settings::TemplateSectionSpec& spec) const {
    return spec.section_title.isEmpty() ? spec.capture_kind : spec.section_title;
}

void TemplateOverlayController::closeAll() {
    select_mode_ = SelectMode::Idle;
    if (capture_service_) {
        capture_service_->closeAll();
    }
}

void TemplateOverlayController::startTemplateCapture(
    const QString& capture_kind, const pipela::app::panels::settings::TemplateSectionSpec& spec,
    std::function<void()> on_applied) {
    const std::intptr_t hwnd = resolveAnchor(capture_kind);
    if (!hwnd) {
        if (capture_kind == QString::fromUtf8("start_game_launcher")) {
            emitLog(QString::fromUtf8("[%1] 스마트업데이터 창 없음 — 런처를 연 뒤 다시 시도")
                        .arg(labelFor(spec)));
        } else {
            emitLog(QString::fromUtf8("[%1] 게임 HWND 없음").arg(labelFor(spec)));
        }
        return;
    }
    if (capture_service_) {
        select_mode_ = SelectMode::TemplateCapture;
        capture_service_->startTemplateCapture(capture_kind.toStdString(), hwnd, labelFor(spec),
                                               std::move(on_applied));
        if (capture_service_->mode() == capture::CaptureOverlayService::Mode::Idle) {
            select_mode_ = SelectMode::Idle;
        }
    }
}

void TemplateOverlayController::startRegionSelect(
    const QString& capture_kind, const pipela::app::panels::settings::TemplateSectionSpec& spec,
    std::function<void()> on_applied) {
    const auto region_type = pipela::core::template_meta::captureKindToRegionType(
        capture_kind.toStdString());
    if (!region_type) {
        emitLog(QString::fromUtf8("[%1] 영역 선택 미지원 kind").arg(labelFor(spec)));
        return;
    }
    const std::string region_key =
        spec.region_key.isEmpty() ? *pipela::core::template_meta::regionTypeToRegistryKey(*region_type)
                                  : spec.region_key.toStdString();
    const std::intptr_t hwnd = resolveAnchor(capture_kind);
    if (!hwnd) {
        emitLog(QString::fromUtf8("[%1] 게임 HWND 없음").arg(labelFor(spec)));
        return;
    }
    if (capture_service_) {
        select_mode_ = SelectMode::RegionSelect;
        capture_service_->startRegionSelect(*region_type, region_key, hwnd, labelFor(spec),
                                            std::move(on_applied));
        if (capture_service_->mode() == capture::CaptureOverlayService::Mode::Idle) {
            select_mode_ = SelectMode::Idle;
        }
    }
}

void TemplateOverlayController::toggleRegionPreview(
    const QString& capture_kind, const pipela::app::panels::settings::TemplateSectionSpec& spec) {
    const auto region_type = pipela::core::template_meta::captureKindToRegionType(
        capture_kind.toStdString());
    if (!region_type) {
        emitLog(QString::fromUtf8("[%1] 미리보기 미지원 kind").arg(labelFor(spec)));
        return;
    }
    const std::string region_key =
        spec.region_key.isEmpty() ? *pipela::core::template_meta::regionTypeToRegistryKey(*region_type)
                                  : spec.region_key.toStdString();
    const std::intptr_t hwnd = resolveAnchor(capture_kind);
    if (!hwnd) {
        emitLog(QString::fromUtf8("[%1] 게임 HWND 없음").arg(labelFor(spec)));
        return;
    }
    if (capture_service_) {
        capture_service_->toggleRegionPreview(*region_type, region_key, hwnd, labelFor(spec));
        select_mode_ = capture_service_->mode() == capture::CaptureOverlayService::Mode::RegionPreview
                           ? SelectMode::RegionPreview
                           : SelectMode::Idle;
    }
}

void TemplateOverlayController::clearMatchRegion(
    const pipela::app::panels::settings::TemplateSectionSpec& spec) {
    const std::string region_key = spec.region_key.toStdString();
    if (region_key.empty()) {
        return;
    }
    pipela::core::template_meta::clearMatchRegion(region_key);
    if (capture_service_) {
        capture_service_->closePreview();
    }
    select_mode_ = SelectMode::Idle;
    emitLog(QString::fromUtf8("[%1] ROI 해제").arg(labelFor(spec)));
}

void TemplateOverlayController::startRegionSelectForType(
    const QString& region_type, const QString& region_registry_key, const QString& label,
    std::function<void()> on_applied) {
    const std::intptr_t hwnd = resolveAnchor(QString{});
    if (!hwnd) {
        emitLog(QString::fromUtf8("[%1] 게임 HWND 없음").arg(label));
        return;
    }
    if (capture_service_) {
        select_mode_ = SelectMode::RegionSelect;
        capture_service_->startRegionSelect(region_type.toStdString(),
                                            region_registry_key.toStdString(), hwnd, label,
                                            std::move(on_applied));
        if (capture_service_->mode() == capture::CaptureOverlayService::Mode::Idle) {
            select_mode_ = SelectMode::Idle;
        }
    }
}

void TemplateOverlayController::toggleRegionPreviewForType(
    const QString& region_type, const QString& region_registry_key, const QString& label) {
    const std::intptr_t hwnd = resolveAnchor(QString{});
    if (!hwnd) {
        emitLog(QString::fromUtf8("[%1] 게임 HWND 없음").arg(label));
        return;
    }
    if (capture_service_) {
        capture_service_->toggleRegionPreview(region_type.toStdString(),
                                              region_registry_key.toStdString(), hwnd, label);
        select_mode_ = capture_service_->mode() == capture::CaptureOverlayService::Mode::RegionPreview
                           ? SelectMode::RegionPreview
                           : SelectMode::Idle;
    }
}

void TemplateOverlayController::clearMatchRegionForKey(const QString& region_registry_key,
                                                       const QString& label) {
    const std::string key = region_registry_key.toStdString();
    if (key.empty()) {
        return;
    }
    pipela::core::template_meta::clearMatchRegion(key);
    if (capture_service_) {
        capture_service_->closePreview();
    }
    select_mode_ = SelectMode::Idle;
    emitLog(QString::fromUtf8("[%1] ROI 해제").arg(label));
}

}  // namespace pipela::ui::overlays
