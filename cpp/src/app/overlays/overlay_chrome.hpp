#pragma once

#include <QPainter>
#include <QRect>
#include <QString>

namespace pipela::ui::overlays {

// Legacy helpers (region preview pulse).
void paintOverlayDim(QPainter& painter, const QRect& bounds);
void paintSelectionDragRect(QPainter& painter, const QRect& rect);
void paintRegionPreviewBox(QPainter& painter, const QRect& rect, double t_sec);

// AGENT: Modern capture overlay chrome — dim around hole, bracket handles, size badge.
void paintCaptureDimAroundSelection(QPainter& painter, const QRect& bounds, const QRect& selection);
void paintCaptureSelectionChrome(QPainter& painter, const QRect& bounds, const QRect& selection,
                                 double pulse_phase, const QString& size_label);
void paintCaptureHintBar(QPainter& painter, const QRect& bounds, const QString& hint);

}  // namespace pipela::ui::overlays
