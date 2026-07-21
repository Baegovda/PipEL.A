#include "overlays/kill_counter_viewport_typography.hpp"

#include <algorithm>
#include <cmath>

#include <QString>

#include "theme/ui_adaptive.hpp"

namespace pipela::app::overlays::kc_typography {

namespace {

constexpr double kBodyRefW = 440.0;
constexpr double kBodyRefH = 740.0;
constexpr double kIsoLo = 0.42;
constexpr double kIsoHi = 1.92;

int clampWh(int v, int lo, int hi) { return std::max(lo, std::min(hi, v)); }

std::tuple<double, double> band(double vscale, double hi_design, double lo_design, double lo_min) {
    const double hi = kcViewportDesignPtEffV(vscale, hi_design);
    const double lo = std::max(lo_min, kcViewportDesignPtEffV(vscale, lo_design));
    return {hi, lo};
}

}  // namespace

double kcViewportIsoScale(int w, int h) {
    const int aw = clampWh(w, 120, 980);
    const int ah = clampWh(h, 260, 1360);
    const double rx = static_cast<double>(aw) / kBodyRefW;
    const double ry = static_cast<double>(ah) / kBodyRefH;
    const double iso = std::sqrt(std::max(1e-4, rx * ry));
    return std::clamp(iso, kIsoLo, kIsoHi);
}

double kcViewportHeightScale(int /*w*/, int h) {
    const int ah = clampWh(h, 260, 1360);
    const double ry = static_cast<double>(ah) / kBodyRefH;
    return std::clamp(ry, kIsoLo, kIsoHi);
}

double kcViewportDesignPtEffV(double vscale, double design_pt) {
    return pipela::ui::theme::scaledDesignPt(design_pt * kKcWindowFontScale) * vscale;
}

double heroProgPtHi(double vscale) { return kcViewportDesignPtEffV(vscale, 14.0); }

double heroProgPtLo(double vscale) {
    return std::max(7.0, kcViewportDesignPtEffV(vscale, 6.25));
}

std::tuple<double, double> recentRollValuePts(double vscale) {
    return band(vscale, 11.0, 7.0, 6.0);
}

std::tuple<double, double> miniColumnValuePts(double vscale) { return recentRollValuePts(vscale); }

std::tuple<double, double> dodGridValuePts(double vscale) { return miniColumnValuePts(vscale); }

std::tuple<double, double> lapTileValuePts(double vscale) { return recentRollValuePts(vscale); }

std::tuple<double, double> lapSheetKillsPts(double vscale) {
    return band(vscale, 16.25, 8.0, 7.0);
}

std::tuple<double, double> lapSheetCaptionPts(double vscale) {
    return band(vscale, 7.65, 6.0, 6.0);
}

std::tuple<double, double> lapSheetElapsedLabelPts(double vscale) {
    return lapSheetCaptionPts(vscale);
}

std::tuple<double, double> lapSheetElapsedTimePts(double vscale) { return lapSheetKillsPts(vscale); }

double elapsedEffPtClip(double pt) { return std::max(kKcViewportMinPt, pt); }

QString elapsedEffPtCss(double pt) {
    return QString::number(elapsedEffPtClip(pt), 'g', 4) + QString::fromUtf8("pt");
}

std::tuple<double, double> gaugeOverlayPctPts(double vscale) {
    return band(vscale, 9.5, 6.5, 6.0);
}

std::tuple<double, double> statusBannerPts(double vscale) {
    return band(vscale, 9.5, 6.5, 6.5);
}

std::tuple<double, double> goalPlainSubvalPts(double vscale) {
    return statusBannerPts(vscale);
}

QString kcViewportSptV(double vscale, double design_pt) {
    double v = kcViewportDesignPtEffV(vscale, design_pt);
    v = std::max(kKcViewportMinPt, v);
    return QString::number(v, 'g', 4) + QString::fromUtf8("pt");
}

QString kcFitQPushButtonTextWidthQss(double vscale, double base_design_pt,
                                     double min_design_pt) {
    const double be = kcViewportDesignPtEffV(vscale, base_design_pt);
    const double me = std::max(6.25, kcViewportDesignPtEffV(vscale, min_design_pt));
    return QString::fromUtf8("font-size: %1pt; min-width: 0px;")
        .arg(QString::number(std::max(me, be * 0.85), 'g', 4));
}

}  // namespace pipela::app::overlays::kc_typography
