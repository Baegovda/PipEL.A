#include "widgets/template_path_connector_arrow.hpp"

#include <cmath>

#include <QEasingCurve>
#include <QVariantAnimation>

#include "theme/ui_adaptive.hpp"

namespace pipela::app::widgets {

namespace {

constexpr char kDimHex[] = "#7a808c";
constexpr char kAccentHex[] = "#6cff9a";

}  // namespace

QString TemplatePathConnectorArrow::connectorQss(const QString& color_hex) {
    const int pt = std::max(12, pipela::ui::theme::scalePxV(15, 720) * 72 / 96);
    return QString::fromUtf8("QLabel { color: %1; font-size: %2px; font-weight: 500; }")
        .arg(color_hex)
        .arg(pt);
}

TemplatePathConnectorArrow::TemplatePathConnectorArrow(QWidget* parent) : QLabel(QString::fromUtf8("↓"), parent) {
    setAlignment(Qt::AlignHCenter | Qt::AlignVCenter);
    anim_ = new QVariantAnimation(this);
    anim_->setDuration(1050);
    anim_->setStartValue(0.0);
    anim_->setEndValue(1.0);
    anim_->setEasingCurve(QEasingCurve::InOutSine);
    connect(anim_, &QVariantAnimation::valueChanged, this, &TemplatePathConnectorArrow::onPulseFrame);
    connect(anim_, &QVariantAnimation::finished, this, &TemplatePathConnectorArrow::onPulseFinished);
    refreshForScale();
}

void TemplatePathConnectorArrow::refreshForScale() {
    dim_ = QColor(kDimHex);
    accent_ = QColor(kAccentHex);
    muted_qss_ = connectorQss(kDimHex);
    if (!pulse_active_) {
        setStyleSheet(muted_qss_);
    }
}

void TemplatePathConnectorArrow::resetEdgeState() {
    primed_ = false;
    last_ok_ = false;
}

void TemplatePathConnectorArrow::feedThresholdEdge(double score, double threshold) {
    const bool ok = score >= threshold;
    if (!primed_) {
        primed_ = true;
        last_ok_ = ok;
        return;
    }
    if (ok && !last_ok_) {
        startPulse();
    }
    last_ok_ = ok;
}

void TemplatePathConnectorArrow::startPulse() {
    if (anim_->state() == QAbstractAnimation::Running) {
        anim_->stop();
    }
    pulse_active_ = true;
    anim_->start();
}

void TemplatePathConnectorArrow::onPulseFrame(const QVariant& value) {
    const double t = value.toDouble();
    const double u = std::max(0.0, std::min(1.0, std::sin(M_PI * t)));
    const auto mix = [&](int dim_c, int acc_c) {
        return static_cast<int>(dim_c + (acc_c - dim_c) * u);
    };
    const QColor c(mix(dim_.red(), accent_.red()), mix(dim_.green(), accent_.green()),
                   mix(dim_.blue(), accent_.blue()));
    applyConnectorColor(c.name());
}

void TemplatePathConnectorArrow::onPulseFinished() {
    pulse_active_ = false;
    setStyleSheet(muted_qss_);
}

void TemplatePathConnectorArrow::applyConnectorColor(const QString& color_hex) {
    setStyleSheet(connectorQss(color_hex));
}

}  // namespace pipela::app::widgets
