#include "title_strip_window.hpp"

#include <algorithm>
#include <array>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

#include <QApplication>
#include <QCheckBox>
#include <QHBoxLayout>
#include <QLabel>
#include <QPixmap>
#include <QPushButton>
#include <QMouseEvent>
#include <QResizeEvent>
#include <QStyle>
#include <QTimer>
#include <QToolButton>
#include <QVariant>

#include "pipela/core/registry/parse.hpp"
#include "pipela/core/registry/store.hpp"
#include "pipela/core/version.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "pipela/core/win32/window_ops.hpp"
#include "theme/dpi_helpers.hpp"
#include "theme/resolution_chrome.hpp"
#include "theme/title_strip_styles.hpp"
#include "theme/ui_adaptive.hpp"
#include "dock/dock_z_stack.hpp"
#include "shell/dev_ui_mode.hpp"

namespace pipela::ui::overlays {

TitleStripWindow::TitleStripWindow(QWidget* parent) : QWidget(parent) {
    setWindowFlags(Qt::FramelessWindowHint | Qt::Tool);
    setAttribute(Qt::WA_ShowWithoutActivating, true);
    setObjectName(QString::fromUtf8("pipelaGameTitleStripRoot"));
    setStyleSheet(pipela::ui::theme::gameTitleStripQss());

    auto* layout = new QHBoxLayout(this);
    layout->setContentsMargins(6, 0, 6, 0);
    layout->setSpacing(6);

    icon_label_ = new QLabel(this);
    icon_label_->setObjectName(QString::fromUtf8("pipelaStripAppIcon"));
    icon_label_->setAlignment(Qt::AlignCenter);
    applyStripAppIconPixmap();

    brand_label_ = new QLabel(QString::fromUtf8("PIP EL.A"), this);
    brand_label_->setObjectName(QString::fromUtf8("pipelaStripBrand"));
    version_label_ = new QLabel(this);
    version_label_->setObjectName(QString::fromUtf8("pipelaStripVer"));
    setVersionText(QString::fromUtf8("v%1").arg(
        QString::fromStdString(pipela::core::stripDisplayVersion())));

    res_label_ = new QLabel(this);
    res_label_->setObjectName(QString::fromUtf8("pipelaStripRes"));
    res_label_->setTextFormat(Qt::RichText);
    res_label_->setWordWrap(false);
    res_label_->setStyleSheet("background: transparent; font-size: 9px;");
    res_label_->hide();
    // AGENT: Absolute geometry like Python — not in root QHBoxLayout (caption buttons only).
    for (QLabel* w : {icon_label_, brand_label_, version_label_, res_label_}) {
        if (w != nullptr) {
            w->setParent(this);
        }
    }

    kc_btn_ = new QToolButton(this);
    kc_btn_->setObjectName(QString::fromUtf8("pipelaStripKillCounterBtn"));
    kc_btn_->setText(QString::fromUtf8("Kill Counter"));
    kc_btn_->setToolTip(QString::fromUtf8("등급·몬스터킬 구간 표"));
    kc_btn_->setAutoRaise(true);
    kc_btn_->setCursor(Qt::PointingHandCursor);
    kc_btn_->hide();
    connect(kc_btn_, &QToolButton::clicked, this, &TitleStripWindow::killCounterTierRequested);

    debug_chrome_cb_ = new QCheckBox(QString::fromUtf8("디버그"), this);
    debug_chrome_cb_->setObjectName(QString::fromUtf8("pipelaStripLauncherDebug"));
    debug_chrome_cb_->setToolTip(
        QString::fromUtf8("런처에서도 메인창·킬 카운터를 좌우에 도킹합니다"));
    debug_chrome_cb_->setCursor(Qt::PointingHandCursor);
    debug_chrome_cb_->hide();
    connect(debug_chrome_cb_, &QCheckBox::toggled, this, [this](bool on) {
        pipela::ui::shell::setPipelaLauncherDebugChromeEnabled(on);
        launcher_debug_chrome_ = on;
        layoutStripTitleClusterGeom();
        emit launcherDebugChromeChanged(on);
    });

    launcher_settings_btn_ = new QPushButton(this);
    launcher_settings_btn_->setObjectName(QString::fromUtf8("pipelaStripCaptionBtn"));
    launcher_settings_btn_->setFlat(true);
    launcher_settings_btn_->setIcon(style()->standardIcon(QStyle::SP_FileDialogDetailedView));
    launcher_settings_btn_->setIconSize(QSize(14, 14));
    launcher_settings_btn_->setToolTip(QString::fromUtf8("설정 (런처 전용)"));
    launcher_settings_btn_->setCursor(Qt::PointingHandCursor);
    launcher_settings_btn_->hide();
    connect(launcher_settings_btn_, &QPushButton::clicked, this,
            &TitleStripWindow::launcherSettingsRequested);

    layout->addStretch(1);
    layout->addWidget(debug_chrome_cb_, 0, Qt::AlignVCenter);
    layout->addWidget(launcher_settings_btn_, 0, Qt::AlignVCenter);

    btn_min_ = new QPushButton(this);
    btn_min_->setObjectName(QString::fromUtf8("pipelaStripCaptionBtn"));
    btn_min_->setFlat(true);
    btn_min_->setIcon(style()->standardIcon(QStyle::SP_TitleBarMinButton));
    btn_min_->setIconSize(QSize(14, 14));
    btn_min_->setToolTip(QString::fromUtf8("최소화"));
    btn_max_ = new QPushButton(this);
    btn_max_->setObjectName(QString::fromUtf8("pipelaStripCaptionBtn"));
    btn_max_->setFlat(true);
    btn_max_->setIcon(style()->standardIcon(QStyle::SP_TitleBarMaxButton));
    btn_max_->setIconSize(QSize(14, 14));
    btn_max_->setToolTip(QString::fromUtf8("최대화"));
    btn_close_ = new QPushButton(this);
    btn_close_->setObjectName(QString::fromUtf8("pipelaStripCloseBtn"));
    btn_close_->setFlat(true);
    btn_close_->setIcon(style()->standardIcon(QStyle::SP_TitleBarCloseButton));
    btn_close_->setIconSize(QSize(14, 14));
    btn_close_->setToolTip(QString::fromUtf8("닫기 (게임/런처)"));

    layout->addWidget(btn_min_, 0, Qt::AlignVCenter);
    layout->addWidget(btn_max_, 0, Qt::AlignVCenter);
    layout->addWidget(btn_close_, 0, Qt::AlignVCenter);

    resolution_defer_timer_ = new QTimer(this);
    resolution_defer_timer_->setSingleShot(true);
    resolution_defer_timer_->setInterval(0);
    connect(resolution_defer_timer_, &QTimer::timeout, this,
            &TitleStripWindow::runDeferredResolutionChrome);

    wireCaptionButtons();

    const auto drag_children = findChildren<QWidget*>();
    for (QWidget* child : drag_children) {
        child->installEventFilter(this);
    }
    installEventFilter(this);
}

void TitleStripWindow::wireCaptionButtons() {
    connect(btn_min_, &QPushButton::clicked, this, &TitleStripWindow::anchorMinimizeRequested);
    connect(btn_max_, &QPushButton::clicked, this, &TitleStripWindow::anchorMaximizeRequested);
    connect(btn_close_, &QPushButton::clicked, this, &TitleStripWindow::anchorCloseRequested);
}

bool TitleStripWindow::isGameWindowCenterOnDetectEnabled() const {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find("game_window_center_on_detect_enabled");
    if (it == all.end()) {
        return true;
    }
    return pipela::core::registry::parseBool(it->second);
}

bool TitleStripWindow::isDragHandle(QObject* watched) const {
    if (watched == nullptr) {
        return false;
    }
    if (qobject_cast<QPushButton*>(watched) != nullptr || qobject_cast<QToolButton*>(watched) != nullptr ||
        qobject_cast<QCheckBox*>(watched) != nullptr) {
        return false;
    }
    return watched == this || watched == icon_label_ || watched == brand_label_ ||
           watched == version_label_ || watched == res_label_;
}

void TitleStripWindow::beginAnchorDrag() {
#ifdef _WIN32
    if (!anchor_hwnd_ || !pipela::core::win32::isWindow(anchor_hwnd_)) {
        return;
    }
    RECT wr{};
    if (!GetWindowRect(reinterpret_cast<HWND>(anchor_hwnd_), &wr)) {
        return;
    }
    POINT pt{};
    if (!GetCursorPos(&pt)) {
        return;
    }
    anchor_drag_origin_x_ = wr.left;
    anchor_drag_origin_y_ = wr.top;
    anchor_drag_start_x_ = pt.x;
    anchor_drag_start_y_ = pt.y;
    anchor_drag_active_ = true;
    setCursor(Qt::ClosedHandCursor);
    grabMouse();
#endif
}

void TitleStripWindow::updateAnchorDrag() {
#ifdef _WIN32
    if (!anchor_drag_active_ || !anchor_hwnd_) {
        return;
    }
    POINT pt{};
    if (!GetCursorPos(&pt)) {
        return;
    }
    const int dx = pt.x - anchor_drag_start_x_;
    const int dy = pt.y - anchor_drag_start_y_;
    pipela::core::win32::moveOuterWindow(anchor_hwnd_, anchor_drag_origin_x_ + dx,
                                         anchor_drag_origin_y_ + dy);
    has_geom_sig_ = false;
    emit anchorMovedByUser();
#endif
}

void TitleStripWindow::endAnchorDrag() {
    if (!anchor_drag_active_) {
        return;
    }
    anchor_drag_active_ = false;
    releaseMouse();
    unsetCursor();
}

bool TitleStripWindow::eventFilter(QObject* watched, QEvent* event) {
    if (phase_ != pipela::ui::dock::UiDockPhase::Client &&
        phase_ != pipela::ui::dock::UiDockPhase::Launcher) {
        return QWidget::eventFilter(watched, event);
    }
    if (!anchor_hwnd_ || isGameWindowCenterOnDetectEnabled() || !isDragHandle(watched)) {
        if (event->type() == QEvent::MouseButtonRelease) {
            endAnchorDrag();
        }
        return QWidget::eventFilter(watched, event);
    }
    switch (event->type()) {
        case QEvent::MouseButtonPress: {
            auto* me = static_cast<QMouseEvent*>(event);
            if (me->button() == Qt::LeftButton) {
                beginAnchorDrag();
            }
            break;
        }
        case QEvent::MouseMove:
            if (anchor_drag_active_) {
                updateAnchorDrag();
                return true;
            }
            break;
        case QEvent::MouseButtonRelease:
            if (anchor_drag_active_) {
                endAnchorDrag();
                return true;
            }
            break;
        default:
            break;
    }
    return QWidget::eventFilter(watched, event);
}

void TitleStripWindow::syncFromGeometry(std::intptr_t anchor_hwnd, int x_phys, int y_phys,
                                        int w_phys, int h_phys) {
    const bool anchor_changed = anchor_hwnd != anchor_hwnd_;
    anchor_hwnd_ = anchor_hwnd;
    if (!anchor_hwnd || w_phys < 8 || h_phys < 8) {
        has_geom_sig_ = false;
        strip_left_phys_ = 0;
        hide();
        return;
    }
    const std::array<int, 5> geom_sig = {x_phys, y_phys, w_phys, h_phys,
                                         static_cast<int>(anchor_hwnd)};
    if (has_geom_sig_ && geom_sig == last_geom_sig_) {
        if (!isVisible()) {
            show();
        }
        reassertZOrder(true);
        return;
    }
    last_geom_sig_ = geom_sig;
    has_geom_sig_ = true;
    strip_left_phys_ = x_phys;

    const QRect geom = pipela::ui::theme::win32PhysicalScreenRectToQtOverlayGeometry(
        anchor_hwnd, x_phys, y_phys, w_phys, h_phys);
    setGeometry(geom);
    applyWin32AnchorBinding(anchor_changed, true);
    last_res_chrome_sig_.clear();
    if (!isVisible()) {
        show();
    }
    layoutStripTitleClusterGeom();
    layoutResolutionStripLabelGeom();
    layoutKillCounterStripButtonGeom();
}

void TitleStripWindow::setOverlayHwnd(std::intptr_t overlay_hwnd) {
    overlay_hwnd_ = overlay_hwnd;
}

void TitleStripWindow::reassertZOrder(bool force_z_restack) {
    if (!anchor_hwnd_ || !isVisible()) {
        return;
    }
    const std::intptr_t strip_hwnd =
        static_cast<std::intptr_t>(static_cast<qintptr>(winId()));
    if (strip_hwnd != 0) {
        pipela::core::win32::showWindowNoActivate(strip_hwnd);
        if (force_z_restack) {
            pipela::ui::dock::clearDockedChromeZStackState(strip_hwnd);
        }
    }
    applyWin32AnchorBinding(false, force_z_restack);
    raise();
}

void TitleStripWindow::applyWin32AnchorBinding(bool set_owner, bool force_z_restack) {
    if (!anchor_hwnd_) {
        return;
    }
    const std::intptr_t strip_hwnd =
        static_cast<std::intptr_t>(static_cast<qintptr>(winId()));
    if (strip_hwnd != 0) {
        pipela::ui::dock::syncDockedChromeZOrder(strip_hwnd, anchor_hwnd_, overlay_hwnd_,
                                                 set_owner, force_z_restack);
    }
}

void TitleStripWindow::invalidateChromeLayout() {
    last_res_html_.clear();
    last_res_ck_.clear();
    last_res_chrome_sig_.clear();
    if (res_label_ != nullptr) {
        res_label_->setProperty("pipelaResFitCache", QVariant());
    }
}

void TitleStripWindow::invalidateStripGeometry() {
    has_geom_sig_ = false;
    strip_left_phys_ = 0;
}

std::intptr_t TitleStripWindow::resolutionRectHwnd() const {
    if (phase_ == pipela::ui::dock::UiDockPhase::Client && game_hwnd_ &&
        pipela::core::win32::isWindow(game_hwnd_)) {
        return game_hwnd_;
    }
    return anchor_hwnd_;
}

double TitleStripWindow::resolutionAvailCssPx() const {
    int right_edge = width();
    const QWidget* edge_widgets[] = {kc_btn_, debug_chrome_cb_, launcher_settings_btn_, btn_min_,
                                   btn_max_, btn_close_};
    for (const QWidget* w : edge_widgets) {
        if (w != nullptr && w->isVisible()) {
            right_edge = std::min(right_edge, w->geometry().x());
        }
    }
    const int left_hint = version_label_ != nullptr ? version_label_->geometry().right() + 6 : 0;
    return static_cast<double>(std::max(40, right_edge - left_hint));
}

void TitleStripWindow::setMainUiLeftPhys(int main_ui_left_phys) {
    if (main_ui_left_phys_ != main_ui_left_phys) {
        main_ui_left_phys_ = main_ui_left_phys;
        layoutStripTitleClusterGeom();
    }
}

void TitleStripWindow::applyStripAppIconPixmap() {
    if (icon_label_ == nullptr) {
        return;
    }
    const int cell = std::clamp(pipela::ui::theme::scalePxV(18, height() > 0 ? height() : 24), 14, 26);
    const int inset = std::max(1, pipela::ui::theme::scalePxV(2, cell));
    const int pm_side = std::max(10, cell - 2 * inset);
    const QIcon ic = QApplication::windowIcon();
    if (ic.isNull()) {
        icon_label_->clear();
        icon_label_->hide();
        return;
    }
    QPixmap pm = ic.pixmap(pm_side, pm_side);
    if (pm.isNull()) {
        icon_label_->clear();
        icon_label_->hide();
        return;
    }
    pm = pm.scaled(pm_side, pm_side, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    icon_label_->setPixmap(pm);
    icon_label_->setFixedSize(cell, cell);
    icon_label_->setScaledContents(false);
    icon_label_->show();
}

void TitleStripWindow::layoutStripTitleClusterGeom() {
    if (brand_label_ == nullptr || version_label_ == nullptr) {
        return;
    }
    const bool show_cluster =
        phase_ != pipela::ui::dock::UiDockPhase::Launcher || launcher_debug_chrome_;
    if (!show_cluster) {
        if (icon_label_ != nullptr) {
            icon_label_->hide();
        }
        brand_label_->hide();
        version_label_->hide();
        return;
    }
    const int mw = std::max(16, width());
    const int h_st = std::max(8, height());
    const int gap_ib = std::max(2, pipela::ui::theme::scalePxV(4, h_st));
    const int gap_bv = std::max(2, pipela::ui::theme::scalePxV(6, h_st));
    const int pad = std::max(0, pipela::ui::theme::scalePxV(6, h_st));

    int x_icon = pad;
    if (main_ui_left_phys_ > 0 && strip_left_phys_ > 0 && anchor_hwnd_) {
        const double sc = std::max(0.01, pipela::ui::theme::win32DpiScaleForHwnd(anchor_hwnd_));
        x_icon = static_cast<int>(std::lround(static_cast<double>(main_ui_left_phys_ - strip_left_phys_) / sc)) +
                 pad;
    }

    int x_after_ic = x_icon;
    if (icon_label_ != nullptr && icon_label_->isVisible()) {
        const QPixmap pm = icon_label_->pixmap(Qt::ReturnByValue);
        if (!pm.isNull()) {
            const int w_ic = std::max(8, icon_label_->width());
            const int h_ic = std::max(8, icon_label_->height());
            const int x_pl = std::clamp(x_icon, 0, std::max(0, mw - w_ic));
            icon_label_->move(x_pl, std::max(0, (h_st - h_ic) / 2));
            icon_label_->raise();
            x_after_ic = x_pl + w_ic + gap_ib;
        } else {
            icon_label_->hide();
        }
    } else if (icon_label_ != nullptr) {
        icon_label_->hide();
    }

    brand_label_->adjustSize();
    const int w_br = std::max(8, brand_label_->sizeHint().width());
    const int h_br = std::max(8, brand_label_->sizeHint().height());
    const int x_br = std::clamp(x_after_ic, 0, std::max(0, mw - w_br));
    brand_label_->move(x_br, std::max(0, (h_st - h_br) / 2));
    brand_label_->show();
    brand_label_->raise();

    version_label_->adjustSize();
    const int w_ver = std::max(8, version_label_->sizeHint().width());
    const int h_ver = std::max(8, version_label_->sizeHint().height());
    int x_ver = std::clamp(x_br + w_br + gap_bv, 0, std::max(0, mw - w_ver));
    version_label_->move(x_ver, std::max(0, (h_st - h_ver) / 2));
    version_label_->show();
    version_label_->raise();

    if (res_label_ != nullptr && res_label_->isVisible()) {
        for (QLabel* w : {icon_label_, brand_label_, version_label_}) {
            if (w != nullptr && w->isVisible()) {
                w->stackUnder(res_label_);
            }
        }
    }
}

void TitleStripWindow::layoutResolutionStripLabelGeom() {
    if (res_label_ == nullptr || !res_label_->isVisible()) {
        return;
    }
    if (strip_left_phys_ <= 0) {
        return;
    }
    const std::intptr_t rect_hwnd = resolutionRectHwnd();
    if (!rect_hwnd || !pipela::core::win32::isWindow(rect_hwnd)) {
        return;
    }
    const auto cr = pipela::core::win32::getClientRectScreen(rect_hwnd);
    const int cr_l = std::get<0>(cr);
    if (std::get<2>(cr) <= cr_l) {
        return;
    }
    const double sc = std::max(0.01, pipela::ui::theme::win32DpiScaleForHwnd(rect_hwnd));
    int x_left = static_cast<int>(std::lround(static_cast<double>(cr_l - strip_left_phys_) / sc));
    res_label_->adjustSize();
    const int bw = std::max(8, res_label_->sizeHint().width());
    const int bh = std::max(8, res_label_->sizeHint().height());
    const int h_st = std::max(8, height());
    const int y_top = std::max(0, (h_st - bh) / 2);
    const int mw = std::max(16, width());
    int min_x = 0;
    if (phase_ != pipela::ui::dock::UiDockPhase::Launcher || launcher_debug_chrome_) {
        if (version_label_ != nullptr && version_label_->isVisible()) {
            min_x = version_label_->geometry().right() +
                    std::max(4, pipela::ui::theme::scalePxV(6, h_st));
        } else if (brand_label_ != nullptr && brand_label_->isVisible()) {
            min_x = brand_label_->geometry().right() +
                    std::max(4, pipela::ui::theme::scalePxV(6, h_st));
        }
    }
    x_left = std::max(x_left, min_x);
    x_left = std::clamp(x_left, 0, std::max(0, mw - bw));
    res_label_->move(x_left, y_top);
    res_label_->raise();
    res_label_->show();
}

void TitleStripWindow::layoutKillCounterStripButtonGeom() {
    if (kc_btn_ == nullptr || !kc_btn_->isVisible()) {
        return;
    }
    if (strip_left_phys_ <= 0) {
        return;
    }
    if (!game_hwnd_ || !pipela::core::win32::isWindow(game_hwnd_)) {
        return;
    }
    const auto cr = pipela::core::win32::getClientRectScreen(game_hwnd_);
    const int cr_r = std::get<2>(cr);
    if (cr_r <= std::get<0>(cr)) {
        return;
    }
    double sc = pipela::ui::theme::win32DpiScaleForHwnd(game_hwnd_);
    if (sc <= 0.01) {
        sc = 1.0;
    }
    int x_left = static_cast<int>(std::lround(static_cast<double>(cr_r - strip_left_phys_) / sc));
    kc_btn_->adjustSize();
    const int bw = std::max(8, kc_btn_->sizeHint().width());
    const int bh = std::max(8, kc_btn_->sizeHint().height());
    const int h_st = std::max(8, height());
    const int y_top = std::max(0, (h_st - bh) / 2);
    const int mw = std::max(16, width());
    x_left = std::clamp(x_left, 0, std::max(0, mw - bw));
    if (btn_min_ != nullptr) {
        kc_btn_->stackUnder(btn_min_);
    }
    kc_btn_->move(x_left, y_top);
    kc_btn_->show();
}

void TitleStripWindow::scheduleResolutionChrome(std::intptr_t anchor_hwnd,
                                                std::intptr_t game_hwnd,
                                                std::intptr_t launcher_hwnd,
                                                pipela::ui::dock::UiDockPhase phase) {
    anchor_hwnd_ = anchor_hwnd;
    game_hwnd_ = game_hwnd;
    launcher_hwnd_ = launcher_hwnd;
    pending_chrome_phase_ = phase;
    if (resolution_chrome_scheduled_) {
        return;
    }
    resolution_chrome_scheduled_ = true;
    resolution_defer_timer_->start();
}

void TitleStripWindow::runDeferredResolutionChrome() {
    resolution_chrome_scheduled_ = false;
    updateResolutionChrome(anchor_hwnd_, game_hwnd_, launcher_hwnd_, pending_chrome_phase_);
}

void TitleStripWindow::updateResolutionChrome(std::intptr_t anchor_hwnd,
                                              std::intptr_t game_hwnd,
                                              std::intptr_t launcher_hwnd,
                                              pipela::ui::dock::UiDockPhase phase) {
    anchor_hwnd_ = anchor_hwnd;
    game_hwnd_ = game_hwnd;
    launcher_hwnd_ = launcher_hwnd;
    phase_ = phase;
    if (res_label_ == nullptr) {
        return;
    }
    const QString ck = pipela::ui::theme::resolutionChromeContentKey(
        anchor_hwnd, game_hwnd, launcher_hwnd, phase);
    if (ck == last_res_ck_ && !last_res_html_.isEmpty()) {
        layoutResolutionStripLabelGeom();
        return;
    }
    last_res_ck_ = ck;
    const QString html = pipela::ui::theme::stripResolutionBlockHtml(
        anchor_hwnd, game_hwnd, launcher_hwnd, phase);
    last_res_html_ = html;
    if (html.isEmpty()) {
        res_label_->hide();
        return;
    }
    if (html != last_res_chrome_sig_) {
        // AGENT: Strip uses fixed typography like Python game_title_bar_overlay (no fit loop).
        pipela::ui::theme::applyResolutionRichLabelFixed(res_label_, html, 0.66);
        last_res_chrome_sig_ = html;
    }
    res_label_->show();
    layoutStripTitleClusterGeom();
    layoutResolutionStripLabelGeom();
    layoutKillCounterStripButtonGeom();
}

void TitleStripWindow::setUiPhase(pipela::ui::dock::UiDockPhase phase) {
    phase_ = phase;
    const bool client = phase == pipela::ui::dock::UiDockPhase::Client;
    const bool launcher = phase == pipela::ui::dock::UiDockPhase::Launcher;
    launcher_debug_chrome_ =
        launcher && pipela::ui::shell::pipelaLauncherDebugChromeEnabled();
    if (debug_chrome_cb_ != nullptr) {
        debug_chrome_cb_->blockSignals(true);
        debug_chrome_cb_->setChecked(launcher_debug_chrome_);
        debug_chrome_cb_->blockSignals(false);
        debug_chrome_cb_->setVisible(launcher);
    }
    if (kc_btn_ != nullptr) {
        kc_btn_->setVisible(client);
    }
    if (launcher_settings_btn_ != nullptr) {
        launcher_settings_btn_->setVisible(launcher);
    }
    if (btn_max_ != nullptr) {
        btn_max_->setVisible(false);
    }
    const bool caption = client || launcher;
    for (QPushButton* btn : {btn_min_, btn_close_}) {
        if (btn != nullptr) {
            btn->setVisible(caption);
        }
    }
    last_res_chrome_sig_.clear();
    layoutStripTitleClusterGeom();
    layoutKillCounterStripButtonGeom();
}

void TitleStripWindow::setVersionText(const QString& version_text) {
    if (version_label_ != nullptr) {
        version_label_->setText(version_text);
        version_label_->setToolTip(
            QString::fromUtf8("릴리스 %1").arg(QString::fromStdString(pipela::core::appVersion())));
    }
}

void TitleStripWindow::resizeEvent(QResizeEvent* event) {
    QWidget::resizeEvent(event);
    last_res_chrome_sig_.clear();
    if (res_label_ != nullptr) {
        res_label_->setProperty("pipelaResFitCache", QVariant());
    }
    applyStripAppIconPixmap();
    layoutStripTitleClusterGeom();
    layoutResolutionStripLabelGeom();
    layoutKillCounterStripButtonGeom();
}

}  // namespace pipela::ui::overlays
