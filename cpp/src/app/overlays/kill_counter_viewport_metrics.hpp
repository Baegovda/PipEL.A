#pragma once

#include <QWidget>

namespace pipela::app::overlays::kc_metrics {

constexpr int kBodyRefWidth = 440;
constexpr int kBodyRefHeight = 740;

std::pair<int, int> kcViewportWhValid(int w, int h);
double kcViewportIsoScale(int w, int h);
double kcViewportWidthScale(int w, int h);
double kcViewportHeightScale(int w, int h);
int kcViewportPxH(double ws, double design_px, int lo = 1, int hi = 320);
int kcViewportPxV(double vs, double design_px, int lo = 1, int hi = 320);
std::pair<int, int> kcViewportWhFromWidgetChain(QWidget* owner);

}  // namespace pipela::app::overlays::kc_metrics
