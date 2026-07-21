#pragma once

#include <QDoubleSpinBox>
#include <QSpinBox>

class QWheelEvent;

namespace pipela::app::widgets {

// AGENT: Drag-scrub numeric fields — custom line edit + optional coarse wheel stepping.
class DragSpinBox : public QSpinBox {
    Q_OBJECT

public:
    explicit DragSpinBox(QWidget* parent = nullptr, double scrub_pixels_scale = 1.0,
                         double pre_step_highlight_start = 0.0);

    void setWheelNotchesPerStep(int notches);
    int wheelNotchesPerStep() const { return wheel_notches_per_step_; }

protected:
    void wheelEvent(QWheelEvent* event) override;

private:
    int wheel_notches_per_step_{0};
    int wheel_accum_{0};
};

class DragDoubleSpinBox : public QDoubleSpinBox {
    Q_OBJECT

public:
    explicit DragDoubleSpinBox(QWidget* parent = nullptr, double scrub_pixels_scale = 1.0,
                               double pre_step_highlight_start = 0.0);

    void setWheelNotchesPerStep(int notches);
    int wheelNotchesPerStep() const { return wheel_notches_per_step_; }

protected:
    void wheelEvent(QWheelEvent* event) override;

private:
    int wheel_notches_per_step_{0};
    int wheel_accum_{0};
};

}  // namespace pipela::app::widgets
