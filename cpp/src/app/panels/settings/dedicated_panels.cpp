#include "panels/settings/dedicated_panels.hpp"

#include "panels/settings/panel_context.hpp"
#include "panels/settings/update_settings_panel.hpp"

#include <algorithm>

#include <QCheckBox>
#include <QClipboard>
#include <QFileDialog>
#include <QFrame>
#include <QGuiApplication>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QTextEdit>
#include <QVBoxLayout>

#include "panels/settings/panel_context.hpp"
#include "pipela/core/console_log_retention.hpp"
#include "pipela/core/kill_counter_install_help.hpp"
#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/version.hpp"
#include "theme/ui_adaptive.hpp"
#include "widgets/drag_spin_box.hpp"
#include "widgets/key_capture_row.hpp"
#include "widgets/settings_binary_toggle.hpp"
#include "widgets/settings_chrome.hpp"

namespace pipela::app::panels::settings {

namespace {

std::string registryString(const char* key, const std::string& fallback) {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find(key);
    if (it != all.end()) {
        return it->second;
    }
    return fallback;
}

int registryInt(const char* key, int fallback) {
    return QString::fromStdString(registryString(key, std::to_string(fallback))).toInt();
}

}  // namespace

QWidget* createInterfacePanel(QWidget* parent, const SettingsPanelContext& ctx) {
    auto* page = new QWidget(parent);
    auto* lay = pipela::app::widgets::createSettingsPageLayout(page);

    auto* heading = new QLabel(QString::fromUtf8("글꼴"), page);
    heading->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(heading);
    pipela::app::widgets::addSettingsCenteredWidget(lay, heading);

    auto* spin = new pipela::app::widgets::DragSpinBox(page, 2.5, 0.70);
    spin->setRange(8, 24);
    spin->setValue(registryInt("pipela_ui_font_pt", 11));
    spin->setWheelNotchesPerStep(2);
    spin->setMaximumWidth(pipela::ui::theme::scalePxH(88, 420));
    QObject::connect(spin, QOverload<int>::of(&pipela::app::widgets::DragSpinBox::valueChanged), page,
                     [&ctx](int v) {
                         const int clamped = std::max(8, std::min(24, v));
                         pipela::core::registry::saveStringValue("pipela_ui_font_pt",
                                                                 std::to_string(clamped));
                         if (ctx.apply_font_pt) {
                             ctx.apply_font_pt(clamped);
                         }
                     });
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("UI 글꼴 크기 (pt)"), spin);

    auto* game_heading = new QLabel(QString::fromUtf8("게임 창"), page);
    game_heading->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle(8));
    pipela::app::widgets::settingsLabelAlignCenterH(game_heading);
    pipela::app::widgets::addSettingsCenteredWidget(lay, game_heading);

    auto* center_toggle = new pipela::ui::widgets::SettingsBinaryToggle(
        QString::fromUtf8("게임 창 화면 중앙 정렬"), "game_window_center_on_detect_enabled", page,
        true);
    pipela::app::widgets::addSettingsCenteredWidget(lay, center_toggle);

    auto* center_hint = new QLabel(
        QString::fromUtf8(
            "켜면 이터널시티 창을 모니터 작업 영역 정중앙에 맞춥니다. "
            "끄면 상단 스트립을 드래그해 게임/런처 창을 자유롭게 옮길 수 있습니다. "
            "템플릿·영역 캡처 중에는 중앙 정렬을 하지 않습니다."),
        page);
    center_hint->setWordWrap(true);
    center_hint->setStyleSheet(pipela::app::widgets::settingsCaptionStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(center_hint);
    pipela::app::widgets::addSettingsProseLabel(lay, center_hint);

    auto* body = new QLabel(
        QString::fromUtf8(
            "8~24pt 범위에서 조절합니다. 숫자 칸을 드래그하면 값이 변하고, 한 단계 전에 필드가 살짝 강조됩니다. "
            "휠은 두 톱니에 한 번씩만 변합니다. Shift·Ctrl로 드래그 민감도를 조절할 수 있습니다. "
            "적용 즉시 제어창·타이틀 스트립·킬 패널 등에 반영되며 설정에 저장됩니다."),
        page);
    body->setWordWrap(true);
    body->setStyleSheet(pipela::app::widgets::settingsCaptionStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(body);
    pipela::app::widgets::addSettingsProseLabel(lay, body);
    lay->addStretch(1);
    return page;
}

QWidget* createConsolePanel(QWidget* parent, const SettingsPanelContext& ctx) {
    auto* page = new QWidget(parent);
    auto* lay = pipela::app::widgets::createSettingsPageLayout(page);

    auto* t2 = new QLabel(QString::fromUtf8("시간 표시 방식"), page);
    t2->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(t2);
    pipela::app::widgets::addSettingsCenteredWidget(lay, t2);

    auto* rel = new QCheckBox(QString::fromUtf8("상대 시간 표시"), page);
    const std::string mode = registryString("console_log_time_display_mode", "absolute");
    rel->setChecked(mode == "relative");
    QObject::connect(rel, &QCheckBox::toggled, page, [&ctx](bool on) {
        pipela::core::registry::saveStringValue("console_log_time_display_mode",
                                                on ? "relative" : "absolute");
        if (ctx.sync_console_time) {
            ctx.sync_console_time();
        }
    });
    pipela::app::widgets::addSettingsCheckboxRow(lay, rel);

    auto* t3 = new QLabel(QString::fromUtf8("로그 자동 숨김"), page);
    t3->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle(4));
    pipela::app::widgets::settingsLabelAlignCenterH(t3);
    pipela::app::widgets::addSettingsCenteredWidget(lay, t3);

    const int total = pipela::core::consoleLogRetentionTotalSec(
        registryInt("console_log_retention_minutes", 30),
        registryInt("console_log_retention_seconds", 0));
    const auto [init_h, init_m, init_s] = pipela::core::consoleLogRetentionSplitTotalToHms(total);

    auto* hour_spin = new pipela::app::widgets::DragSpinBox(page);
    hour_spin->setRange(0, pipela::core::kConsoleLogRetentionUiMaxHours);
    hour_spin->setValue(init_h);
    hour_spin->setMaximumWidth(pipela::ui::theme::scalePxH(72, 420));

    auto* min_spin = new pipela::app::widgets::DragSpinBox(page);
    min_spin->setRange(0, pipela::core::kConsoleLogRetentionUiMaxClockMinute);
    min_spin->setValue(init_m);
    min_spin->setMaximumWidth(pipela::ui::theme::scalePxH(72, 420));

    auto* sec_spin = new pipela::app::widgets::DragSpinBox(page);
    sec_spin->setRange(0, pipela::core::kConsoleLogRetentionMaxSeconds);
    sec_spin->setValue(init_s);
    sec_spin->setMaximumWidth(pipela::ui::theme::scalePxH(72, 420));

    auto commit_retention = [hour_spin, min_spin, sec_spin, &ctx]() {
        const int total_sec = pipela::core::consoleLogRetentionTotalSecFromHms(
            hour_spin->value(), min_spin->value(), sec_spin->value());
        const auto [mm, ss] = pipela::core::consoleLogRetentionSplitTotal(total_sec);
        const auto [hh, mi, se] = pipela::core::consoleLogRetentionSplitTotalToHms(total_sec);
        hour_spin->blockSignals(true);
        min_spin->blockSignals(true);
        sec_spin->blockSignals(true);
        hour_spin->setValue(hh);
        min_spin->setValue(mi);
        sec_spin->setValue(se);
        hour_spin->blockSignals(false);
        min_spin->blockSignals(false);
        sec_spin->blockSignals(false);
        pipela::core::registry::saveStringValue("console_log_retention_minutes",
                                                std::to_string(mm));
        pipela::core::registry::saveStringValue("console_log_retention_seconds",
                                                std::to_string(ss));
        if (ctx.apply_console_retention) {
            ctx.apply_console_retention();
        }
    };

    QObject::connect(hour_spin, QOverload<int>::of(&pipela::app::widgets::DragSpinBox::valueChanged),
                     page, commit_retention);
    QObject::connect(min_spin, QOverload<int>::of(&pipela::app::widgets::DragSpinBox::valueChanged),
                     page, commit_retention);
    QObject::connect(sec_spin, QOverload<int>::of(&pipela::app::widgets::DragSpinBox::valueChanged),
                     page, commit_retention);

    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("시간"), hour_spin);
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("분"), min_spin);
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("초"), sec_spin);

    auto* t4 = new QLabel(QString::fromUtf8("로그 줄 수 제한"), page);
    t4->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle(4));
    pipela::app::widgets::settingsLabelAlignCenterH(t4);
    pipela::app::widgets::addSettingsCenteredWidget(lay, t4);

    auto* max_lines_spin = new pipela::app::widgets::DragSpinBox(page);
    max_lines_spin->setRange(pipela::core::kConsoleLogMaxLinesMin,
                             pipela::core::kConsoleLogMaxLinesMax);
    max_lines_spin->setValue(pipela::core::clampConsoleLogMaxLines(
        registryInt("console_log_max_lines", pipela::core::kConsoleLogMaxLinesDefault)));
    max_lines_spin->setMaximumWidth(pipela::ui::theme::scalePxH(88, 420));
    QObject::connect(max_lines_spin,
                     QOverload<int>::of(&pipela::app::widgets::DragSpinBox::valueChanged), page,
                     [&ctx](int v) {
                         const int clamped = pipela::core::clampConsoleLogMaxLines(v);
                         pipela::core::registry::saveStringValue("console_log_max_lines",
                                                                 std::to_string(clamped));
                         if (ctx.apply_console_retention) {
                             ctx.apply_console_retention();
                         }
                     });
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("최대 줄 수"), max_lines_spin);

    auto* cap_hint = new QLabel(
        QString::fromUtf8(
            "메모리·페이드·스크롤 아카이브 합산 상한입니다. "
            "초과분은 가장 오래된 줄부터 삭제됩니다. "
            "값을 낮출수록 터미널이 가볍게 유지됩니다."),
        page);
    cap_hint->setWordWrap(true);
    cap_hint->setStyleSheet(pipela::app::widgets::settingsCaptionStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(cap_hint);
    pipela::app::widgets::addSettingsProseLabel(lay, cap_hint);

    lay->addStretch(1);
    return page;
}

QWidget* createFlameTriggerPanel(QWidget* parent) {
    auto* page = new QWidget(parent);
    auto* lay = pipela::app::widgets::createSettingsPageLayout(page);

    auto* heading = new QLabel(QString::fromUtf8("Merc Fire · 연사 키"), page);
    heading->setStyleSheet(pipela::app::widgets::settingsSectionHeadingStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(heading);
    pipela::app::widgets::addSettingsCenteredWidget(lay, heading);

    auto* enabled = new pipela::ui::widgets::SettingsBinaryToggle(
        QString::fromUtf8("Merc Fire 활성화"), "merc_fire_enabled", page);
    pipela::app::widgets::addSettingsCenteredWidget(lay, enabled);

    auto* key_row = new pipela::app::widgets::KeyCaptureRow(QString::fromUtf8("연사 키"), page);
    key_row->setRegistryKey("merc_fire_key_code");
    key_row->setVk(registryInt("merc_fire_key_code", 49));
    pipela::app::widgets::addSettingsCenteredWidget(lay, key_row);

    auto* min_spin = new pipela::app::widgets::DragDoubleSpinBox(page);
    min_spin->setRange(0.001, 1000.0);
    min_spin->setDecimals(3);
    min_spin->setSingleStep(0.001);
    const double lo_ms = QString::fromStdString(registryString("merc_fire_random_min_ms", "50"))
                             .toDouble();
    min_spin->setValue(lo_ms / 1000.0);
    QObject::connect(min_spin,
                     QOverload<double>::of(&pipela::app::widgets::DragDoubleSpinBox::valueChanged),
                     page, [](double sec) {
                         pipela::core::registry::saveStringValue(
                             "merc_fire_random_min_ms", std::to_string(sec * 1000.0));
                     });
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("최소 간격(초)"), min_spin);

    auto* max_spin = new pipela::app::widgets::DragDoubleSpinBox(page);
    max_spin->setRange(0.001, 1000.0);
    max_spin->setDecimals(3);
    max_spin->setSingleStep(0.001);
    const double hi_ms = QString::fromStdString(registryString("merc_fire_random_max_ms", "120"))
                             .toDouble();
    max_spin->setValue(hi_ms / 1000.0);
    QObject::connect(max_spin,
                     QOverload<double>::of(&pipela::app::widgets::DragDoubleSpinBox::valueChanged),
                     page, [](double sec) {
                         pipela::core::registry::saveStringValue(
                             "merc_fire_random_max_ms", std::to_string(sec * 1000.0));
                     });
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("최대 간격(초)"), max_spin);

    lay->addStretch(1);
    return page;
}

QWidget* createUpdatePanel(QWidget* parent,
                           const pipela::app::panels::settings::SettingsPanelContext& ctx) {
    return createUpdateSettingsPanel(ctx.update, parent);
}

QWidget* createTesseractPanel(QWidget* parent) {
    auto* page = new QWidget(parent);
    auto* lay = pipela::app::widgets::createSettingsPageLayout(page);

    auto* path_edit = new QLineEdit(page);
    path_edit->setText(QString::fromStdString(registryString("tesseract_exe_path", "")));
    path_edit->setPlaceholderText(QString::fromUtf8("tesseract.exe 경로 (비우면 PATH 탐색)"));
    QObject::connect(path_edit, &QLineEdit::editingFinished, page, [path_edit]() {
        pipela::core::registry::saveStringValue("tesseract_exe_path",
                                                path_edit->text().trimmed().toStdString());
    });
    auto* browse = new QPushButton(QString::fromUtf8("찾아보기…"), page);
    QObject::connect(browse, &QPushButton::clicked, page, [path_edit, parent]() {
        const QString p = QFileDialog::getOpenFileName(parent, QString::fromUtf8("Tesseract 실행 파일"),
                                                       {}, QString::fromUtf8("*.exe"));
        if (!p.isEmpty()) {
            path_edit->setText(p);
            pipela::core::registry::saveStringValue("tesseract_exe_path", p.toStdString());
        }
    });
    pipela::app::widgets::addSettingsFieldRow(lay, QString::fromUtf8("실행 파일"), path_edit);
    pipela::app::widgets::addSettingsCenteredWidget(lay, browse);

    auto* callout = new QFrame(page);
    callout->setObjectName(QString::fromUtf8("helpCallout"));
    const int br = std::max(1, pipela::ui::theme::scalePxV(3, 720));
    const int pad = pipela::ui::theme::scalePxV(14, 720);
    callout->setStyleSheet(QString::fromUtf8(
        "QFrame#helpCallout { background: #1a1d24; border: 1px solid #2a2f3a; "
        "border-left: %1px solid #6cff9a; border-radius: 6px; padding: %2px; }")
                               .arg(br)
                               .arg(pad));

    auto* card = new QVBoxLayout(callout);
    card->setSpacing(pipela::ui::theme::scalePxV(10, 720));

    auto* badge = new QLabel(QString::fromUtf8("도움말"), callout);
    badge->setStyleSheet(QString::fromUtf8(
        "color: #6cff9a; font-weight: 700; font-size: 11px; background: rgba(108,255,154,0.12); "
        "border-radius: 10px; padding: 4px 10px;"));
    pipela::app::widgets::settingsLabelAlignCenterH(badge);
    card->addWidget(badge, 0, Qt::AlignHCenter);

    auto* body_frame = new QFrame(callout);
    body_frame->setObjectName(QString::fromUtf8("helpBody"));
    body_frame->setStyleSheet(QString::fromUtf8(
        "QFrame#helpBody { background: #121417; border: 1px solid #2a2f3a; border-radius: 6px; "
        "padding: 8px; }"));
    auto* body_lay = new QVBoxLayout(body_frame);
    auto* txt = new QTextEdit(body_frame);
    txt->setReadOnly(true);
    txt->setPlainText(QString::fromUtf8(pipela::core::killCounterInstallHelpText().data()));
    txt->setMinimumHeight(pipela::ui::theme::scalePxV(220, 720));
    txt->setStyleSheet(
        QString::fromUtf8("color: #9aa0ac; background: transparent; border: none; font-size: 11px;"));
    body_lay->addWidget(txt, 1);
    card->addWidget(body_frame, 1);

    auto* hint = new QLabel(QString::fromUtf8("설치 후에도 인식이 안 되면 이 블록을 그대로 공유해 주세요."),
                            callout);
    hint->setWordWrap(true);
    hint->setStyleSheet(pipela::app::widgets::settingsCaptionStyle());
    pipela::app::widgets::settingsLabelAlignCenterH(hint);
    pipela::app::widgets::addSettingsProseLabel(card, hint);

    auto* foot = new QHBoxLayout();
    foot->addStretch(1);
    auto* copy_btn = new QPushButton(QString::fromUtf8("안내 전체 복사"), callout);
    copy_btn->setCursor(Qt::PointingHandCursor);
    copy_btn->setStyleSheet(QString::fromUtf8(
        "QPushButton { color: #6cff9a; background: transparent; border: 1px solid #6cff9a; "
        "border-radius: 6px; padding: 8px 14px; font-weight: 600; text-align: center; }"
        "QPushButton:hover { background: rgba(108,255,154,0.12); }"));
    QObject::connect(copy_btn, &QPushButton::clicked, page,
                     [txt]() { QGuiApplication::clipboard()->setText(txt->toPlainText()); });
    foot->addWidget(copy_btn, 0, Qt::AlignHCenter);
    foot->addStretch(1);
    card->addLayout(foot);

    pipela::app::widgets::addSettingsCenteredWidget(lay, callout, 1);
    lay->addStretch(1);
    return page;
}

}  // namespace pipela::app::panels::settings
