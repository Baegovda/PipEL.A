#pragma once

#include <QString>
#include <tuple>

namespace pipela::app::overlays::kc_typography {

constexpr double kKcWindowFontScale = 0.49;
constexpr double kKcViewportMinPt = 6.25;

double kcViewportIsoScale(int w, int h);
double kcViewportHeightScale(int w, int h);
double kcViewportDesignPtEffV(double vscale, double design_pt);
double heroProgPtHi(double vscale);
double heroProgPtLo(double vscale);
std::tuple<double, double> recentRollValuePts(double vscale);
std::tuple<double, double> miniColumnValuePts(double vscale);
std::tuple<double, double> dodGridValuePts(double vscale);
std::tuple<double, double> lapTileValuePts(double vscale);
std::tuple<double, double> lapSheetKillsPts(double vscale);
std::tuple<double, double> lapSheetCaptionPts(double vscale);
std::tuple<double, double> lapSheetElapsedLabelPts(double vscale);
std::tuple<double, double> lapSheetElapsedTimePts(double vscale);
double elapsedEffPtClip(double pt);
QString elapsedEffPtCss(double pt);
std::tuple<double, double> gaugeOverlayPctPts(double vscale);
std::tuple<double, double> statusBannerPts(double vscale);
std::tuple<double, double> goalPlainSubvalPts(double vscale);
QString kcViewportSptV(double vscale, double design_pt);
QString kcFitQPushButtonTextWidthQss(double vscale, double base_design_pt, double min_design_pt);

}  // namespace pipela::app::overlays::kc_typography
