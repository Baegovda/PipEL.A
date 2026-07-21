#pragma once

#include <functional>

#include <QPixmap>
#include <QPoint>
#include <QRect>
#include <QWidget>

namespace pipela::core::state {
class AppState;
}

namespace pipela::ui::overlays::capture {

// AGENT: Full-screen capture drag overlay — single instance, modern chrome, mouse grab.
class CaptureOverlayView : public QWidget {
    Q_OBJECT
public:
    using DragCompleteFn =
        std::function<void(int x, int y, int w, int h, int client_w, int client_h)>;
    using VoidFn = std::function<void()>;
    using LogFn = std::function<void(const QString&)>;

    explicit CaptureOverlayView(QWidget* parent = nullptr);

    void beginSession(std::intptr_t anchor_hwnd, pipela::core::state::AppState* state,
                      const QString& log_label, const QPixmap& freeze_pixmap, DragCompleteFn on_complete,
                      VoidFn on_cancelled, LogFn log = nullptr);

    void endSession(bool cancelled);

protected:
    void paintEvent(QPaintEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;
    void mouseMoveEvent(QMouseEvent* event) override;
    void mouseReleaseEvent(QMouseEvent* event) override;
    void keyPressEvent(QKeyEvent* event) override;
    void timerEvent(QTimerEvent* event) override;

private:
    void raiseTopmost();
    QPoint clampToClient(const QPoint& p) const;
    QRect normalizedSelection() const;
    void finishDragRelease(const QPoint& release_pos);
    QString selectionSizeLabel(const QRect& r) const;

    std::intptr_t anchor_hwnd_{0};
    pipela::core::state::AppState* state_{nullptr};
    QString log_label_;
    QString hint_text_;
    DragCompleteFn on_complete_;
    VoidFn on_cancelled_;
    LogFn log_;
    QPixmap freeze_pixmap_;
    QPoint drag_origin_;
    QRect selection_;
    bool dragging_{false};
    int client_w_{0};
    int client_h_{0};
    int anim_timer_id_{0};
    double anim_phase_{0.0};
};

}  // namespace pipela::ui::overlays::capture
