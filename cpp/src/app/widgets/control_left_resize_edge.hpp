#pragma once

#include <QWidget>

class PipelaMainWindow;

namespace pipela::ui::widgets {

// AGENT: control_main._ControlLeftResizeEdge — frameless dock width drag on left edge.
class ControlLeftResizeEdge : public QWidget {
    Q_OBJECT
public:
    explicit ControlLeftResizeEdge(PipelaMainWindow* main_window, QWidget* parent = nullptr);

protected:
    void mousePressEvent(QMouseEvent* event) override;
    void mouseMoveEvent(QMouseEvent* event) override;
    void mouseReleaseEvent(QMouseEvent* event) override;
    void mouseDoubleClickEvent(QMouseEvent* event) override;

private:
    PipelaMainWindow* main_window_{nullptr};
    bool drag_{false};
    int drag_start_global_x_{0};
    int drag_start_w_{420};
};

}  // namespace pipela::ui::widgets
