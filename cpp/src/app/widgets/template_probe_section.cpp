#include "widgets/template_probe_section.hpp"

#include <algorithm>

#include "widgets/drag_spin_box.hpp"
#include <QFileInfo>
#include <QFrame>
#include <QLabel>
#include <QPixmap>
#include <QShowEvent>
#include <QTimer>
#include <QVBoxLayout>

#include "panels/settings/template_probe_test.hpp"
#include "overlays/template_overlay_controller.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/state/app_state.hpp"
#include "pipela/core/template/capture_catalog.hpp"
#include "pipela/core/template/path_resolve.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "theme/ui_adaptive.hpp"
#include "widgets/bgr_image_qt.hpp"
#include "widgets/settings_chrome.hpp"
#include "widgets/template_last_match_thumb.hpp"
#include "widgets/template_toolbar.hpp"

namespace pipela::app::widgets {

namespace {

double registryDouble(const QString& key, double fallback) {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(key.toStdString());
    if (it == all.end()) {
        return fallback;
    }
    return QString::fromStdString(it->second).toDouble();
}

std::intptr_t hwndFromState(pipela::core::state::AppState* state) {
    if (state == nullptr) {
        return 0;
    }
    const auto v = state->get("target_hwnd");
    if (!v) {
        return 0;
    }
    if (const auto* i = std::get_if<int>(&*v)) {
        return *i;
    }
    if (const auto* l = std::get_if<std::int64_t>(&*v)) {
        return static_cast<std::intptr_t>(*l);
    }
    return 0;
}

std::intptr_t probeAnchorHwnd(pipela::core::state::AppState* state, const QString& capture_kind) {
    if (capture_kind == QString::fromUtf8("start_game_launcher")) {
        return pipela::core::win32::findSmartUpdaterWindow();
    }
    return hwndFromState(state);
}

}  // namespace

TemplateProbeSection::TemplateProbeSection(QWidget* parent) : QWidget(parent) {
    timer_ = new QTimer(this);
    timer_->setInterval(200);
    connect(timer_, &QTimer::timeout, this, [this]() {
        refreshThumb();
        refreshScore();
        refreshLastMatch();
    });
}

void TemplateProbeSection::configure(
    const pipela::app::panels::settings::TemplateSectionSpec& spec,
    const pipela::app::panels::settings::SettingsPanelContext& ctx) {
    spec_ = spec;
    ctx_ = ctx;

    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(settingsRootVerticalSpacing());

    auto* frame = new QFrame(this);
    frame->setFrameShape(QFrame::StyledPanel);
    frame->setStyleSheet(
        "QFrame { background: #1a1d24; border: 1px solid #2e3340; border-radius: 6px; }");
    auto* inner = new QVBoxLayout(frame);
    inner->setContentsMargins(10, 10, 10, 10);
    inner->setSpacing(settingsRootVerticalSpacing());

    auto* heading = new QLabel(spec.section_title, frame);
    heading->setStyleSheet(settingsSectionHeadingStyle());
    settingsLabelAlignCenterH(heading);
    addSettingsCenteredWidget(inner, heading);

    thumb_ = new QLabel(frame);
    const int tw = pipela::ui::theme::scalePxH(120, 420);
    const int th = pipela::ui::theme::scalePxV(72, 720);
    thumb_->setMinimumSize(tw, th);
    thumb_->setAlignment(Qt::AlignCenter);
    thumb_->setStyleSheet("background: #12151a; border-radius: 4px; color: #6a7080;");
    thumb_->setText(QString::fromUtf8("없음"));
    last_match_row_ = createTemplateLastMatchThumbRow(frame, inner, thumb_);

    path_label_ = new QLabel(frame);
    path_label_->setWordWrap(true);
    path_label_->setStyleSheet(settingsCaptionStyle());
    settingsLabelAlignCenterH(path_label_);
    addSettingsCenteredWidget(inner, path_label_);

    score_ = new QLabel(QString::fromUtf8("실시간 점수: —"), frame);
    score_->setStyleSheet("color: #8ec8ff; font-size: 12px; font-weight: 600;");
    settingsLabelAlignCenterH(score_);
    addSettingsCenteredWidget(inner, score_);

    threshold_ = new pipela::app::widgets::DragDoubleSpinBox(frame);
    threshold_->setRange(0.1, 1.0);
    threshold_->setDecimals(2);
    threshold_->setSingleStep(0.01);
    threshold_->setMaximumWidth(pipela::ui::theme::scalePxH(88, 420));
    connect(threshold_, QOverload<double>::of(&pipela::app::widgets::DragDoubleSpinBox::valueChanged),
            this, &TemplateProbeSection::onThresholdChanged);
    addSettingsFieldRow(inner, QString::fromUtf8("유사도 임계값"), threshold_);

    pipela::app::widgets::TemplateToolbarCallbacks toolbar_cb;
    toolbar_cb.log = ctx.log;
    toolbar_cb.on_test = [this]() { runTestMatch(); };
    if (ctx.overlays != nullptr) {
        toolbar_cb.on_capture = [this]() {
            ctx_.overlays->startTemplateCapture(
                spec_.capture_kind, spec_, [this]() { reloadFromRegistry(); });
        };
        toolbar_cb.on_region = [this]() {
            ctx_.overlays->startRegionSelect(spec_.capture_kind, spec_,
                                             [this]() { reloadFromRegistry(); });
        };
        toolbar_cb.on_preview = [this]() {
            ctx_.overlays->toggleRegionPreview(spec_.capture_kind, spec_);
        };
        toolbar_cb.on_clear = [this]() {
            ctx_.overlays->clearMatchRegion(spec_);
            reloadFromRegistry();
        };
    }
    addTemplateToolbar(inner, spec.capture_kind, toolbar_cb);

    layout->addWidget(frame, 0, Qt::AlignHCenter);
}

void TemplateProbeSection::showEvent(QShowEvent* event) {
    QWidget::showEvent(event);
    reloadFromRegistry();
    timer_->start();
}

void TemplateProbeSection::reloadFromRegistry() {
    if (threshold_ == nullptr) {
        return;
    }
    if (!spec_.threshold_key.isEmpty()) {
        const double thr = std::clamp(registryDouble(spec_.threshold_key, 0.6), 0.1, 1.0);
        threshold_->blockSignals(true);
        threshold_->setValue(thr);
        threshold_->blockSignals(false);
    }
    refreshThumb();
    refreshScore();
}

void TemplateProbeSection::refreshThumb() {
    if (thumb_ == nullptr || path_label_ == nullptr) {
        return;
    }
    const auto lookup = [](const std::string& key) -> std::optional<std::string> {
        const auto all = pipela::core::registry::loadAllStringValues();
        const auto it = all.find(key);
        if (it == all.end() || it->second.empty()) {
            return std::nullopt;
        }
        return it->second;
    };
    const std::string capture_kind = spec_.capture_kind.toStdString();
    const std::string path_key = spec_.image_path_key.toStdString();
    const std::string display =
        pipela::core::template_meta::templateImagePathForDisplay(capture_kind, path_key, lookup);
    path_label_->setText(display.empty() ? QString::fromUtf8("(이미지 경로 없음)")
                                         : QString::fromStdString(display));

    const auto existing =
        pipela::core::template_meta::resolveExistingTemplateImagePath(capture_kind, path_key, lookup);
    if (!existing) {
        thumb_->setPixmap(QPixmap());
        thumb_->setText(QString::fromUtf8("없음"));
        return;
    }
    const int max_w = pipela::ui::theme::scalePxH(120, 420);
    const int max_h = pipela::ui::theme::scalePxV(72, 720);
    const QPixmap pm =
        pipela::app::widgets::pixmapFromTemplatePngPath(QString::fromStdString(*existing), max_w, max_h);
    if (pm.isNull()) {
        thumb_->setPixmap(QPixmap());
        thumb_->setText(QString::fromUtf8("로드 실패"));
        return;
    }
    thumb_->setText({});
    thumb_->setPixmap(pm);
}

void TemplateProbeSection::refreshScore() {
    if (score_ == nullptr || spec_.score_state_key.isEmpty() || ctx_.state == nullptr) {
        return;
    }
    const auto v = ctx_.state->get(spec_.score_state_key.toStdString());
    if (!v) {
        return;
    }
    if (const auto* d = std::get_if<double>(&*v)) {
        score_->setText(QString::fromUtf8("실시간 점수: %1").arg(*d, 0, 'f', 2));
    }
}

void TemplateProbeSection::onThresholdChanged(double value) {
    if (spec_.threshold_key.isEmpty()) {
        return;
    }
    const double clamped = std::clamp(value, 0.1, 1.0);
    pipela::core::registry::saveStringValue(spec_.threshold_key.toStdString(),
                                            QString::number(clamped, 'f', 2).toStdString());
}

void TemplateProbeSection::refreshLastMatch() {
    updateTemplateLastMatchThumbnail(last_match_row_, spec_.capture_kind, thumb_);
}

void TemplateProbeSection::runTestMatch() {
    pipela::app::panels::settings::TemplateProbeKeys keys{
        spec_.image_path_key.toStdString(), spec_.image_data_key.toStdString(),
        spec_.region_key.toStdString(), spec_.score_state_key.toStdString(),
        spec_.capture_kind.toStdString()};
    const auto score = pipela::app::panels::settings::runTemplateProbeTest(
        probeAnchorHwnd(ctx_.state, spec_.capture_kind), keys);
    if (!score) {
        if (ctx_.log) {
            ctx_.log(QString::fromUtf8("[%1] 테스트 실패 — 게임 HWND 또는 템플릿 없음")
                         .arg(spec_.capture_kind));
        }
        return;
    }
    if (score_ != nullptr) {
        score_->setText(QString::fromUtf8("테스트 점수: %1").arg(*score, 0, 'f', 2));
    }
    if (ctx_.log) {
        ctx_.log(QString::fromUtf8("[%1] 테스트 점수 %2")
                     .arg(spec_.capture_kind)
                     .arg(*score, 0, 'f', 2));
    }
    refreshLastMatch();
}

}  // namespace pipela::app::widgets
