#pragma once

#include <array>
#include <cstdint>

#include <QWidget>

#include <QMouseEvent>

#include "dock/dock_ui_phase.hpp"

class QLabel;
class QCheckBox;
class QPushButton;
class QTimer;
class QToolButton;

namespace pipela::ui::overlays {

// AGENT: MVP subset of pipela_qt/game_title_bar_overlay.QtGameTitleBarStrip.
class TitleStripWindow : public QWidget {
    Q_OBJECT
public:
    explicit TitleStripWindow(QWidget* parent = nullptr);

    void syncFromGeometry(std::intptr_t anchor_hwnd, int x_phys, int y_phys, int w_phys,
                          int h_phys);
    void setUiPhase(pipela::ui::dock::UiDockPhase phase);
    void setVersionText(const QString& version_text);
    void updateResolutionChrome(std::intptr_t anchor_hwnd, std::intptr_t game_hwnd,
                                std::intptr_t launcher_hwnd, pipela::ui::dock::UiDockPhase phase);
    void scheduleResolutionChrome(std::intptr_t anchor_hwnd, std::intptr_t game_hwnd,
                                  std::intptr_t launcher_hwnd, pipela::ui::dock::UiDockPhase phase);
    void setMainUiLeftPhys(int main_ui_left_phys);
    void setOverlayHwnd(std::intptr_t overlay_hwnd);
    void reassertZOrder(bool force_z_restack = true);
    void invalidateChromeLayout();
    void invalidateStripGeometry();

    std::intptr_t anchorHwnd() const { return anchor_hwnd_; }

signals:
    void launcherSettingsRequested();
    void launcherDebugChromeChanged(bool enabled);
    void killCounterTierRequested();
    void anchorMinimizeRequested();
    void anchorMaximizeRequested();
    void anchorCloseRequested();
    void anchorMovedByUser();

protected:
    bool eventFilter(QObject* watched, QEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;

private:
    bool isDragHandle(QObject* watched) const;
    bool isGameWindowCenterOnDetectEnabled() const;
    void beginAnchorDrag();
    void updateAnchorDrag();
    void endAnchorDrag();

    void wireCaptionButtons();
    void applyWin32AnchorBinding(bool set_owner, bool force_z_restack);
    void layoutResolutionStripLabelGeom();
    void layoutKillCounterStripButtonGeom();
    void layoutStripTitleClusterGeom();
    void applyStripAppIconPixmap();
    void runDeferredResolutionChrome();
    std::intptr_t resolutionRectHwnd() const;
    double resolutionAvailCssPx() const;

    std::intptr_t anchor_hwnd_{0};
    std::intptr_t overlay_hwnd_{0};
    std::intptr_t game_hwnd_{0};
    std::intptr_t launcher_hwnd_{0};
    int strip_left_phys_{0};
    int main_ui_left_phys_{0};
    std::array<int, 5> last_geom_sig_{};
    bool has_geom_sig_{false};
    bool resolution_chrome_scheduled_{false};
    QString last_res_html_;
    QString last_res_ck_;
    QString last_res_chrome_sig_;
    pipela::ui::dock::UiDockPhase phase_{pipela::ui::dock::UiDockPhase::Standby};
    pipela::ui::dock::UiDockPhase pending_chrome_phase_{pipela::ui::dock::UiDockPhase::Standby};
    bool launcher_debug_chrome_{false};
    bool anchor_drag_active_{false};
    int anchor_drag_origin_x_{0};
    int anchor_drag_origin_y_{0};
    int anchor_drag_start_x_{0};
    int anchor_drag_start_y_{0};

    QLabel* icon_label_{nullptr};
    QLabel* brand_label_{nullptr};
    QLabel* version_label_{nullptr};
    QLabel* res_label_{nullptr};
    QToolButton* kc_btn_{nullptr};
    QCheckBox* debug_chrome_cb_{nullptr};
    QPushButton* launcher_settings_btn_{nullptr};
    QPushButton* btn_min_{nullptr};
    QPushButton* btn_max_{nullptr};
    QPushButton* btn_close_{nullptr};
    QTimer* resolution_defer_timer_{nullptr};
};

}  // namespace pipela::ui::overlays
