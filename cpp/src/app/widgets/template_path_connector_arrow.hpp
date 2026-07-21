#pragma once

#include <QLabel>

class QVariantAnimation;

namespace pipela::app::widgets {

// AGENT: Section connector "↓" — accent pulse on score>=threshold rising edge (Python parity).
class TemplatePathConnectorArrow : public QLabel {
    Q_OBJECT

public:
    explicit TemplatePathConnectorArrow(QWidget* parent = nullptr);

    void feedThresholdEdge(double score, double threshold);
    void resetEdgeState();
    void refreshForScale();

private slots:
    void onPulseFrame(const QVariant& value);
    void onPulseFinished();

private:
    void startPulse();
    void applyConnectorColor(const QString& color_hex);
    static QString connectorQss(const QString& color_hex);

    bool primed_{false};
    bool last_ok_{false};
    bool pulse_active_{false};
    QColor dim_;
    QColor accent_;
    QString muted_qss_;
    QVariantAnimation* anim_{nullptr};
};

}  // namespace pipela::app::widgets
