#include "overlays/kill_counter_viewport_metrics.hpp"

#include <algorithm>
#include <cmath>

#include <QVariant>
#include <QWidget>

#include "theme/ui_adaptive.hpp"

namespace pipela::app::overlays::kc_metrics {

namespace {

constexpr double kIsoLo = 0.42;
constexpr double kIsoHi = 1.92;

int clampWh(int v, int lo, int hi) { return std::max(lo, std::min(hi, v)); }

}  // namespace

std::pair<int, int> kcViewportWhValid(int w, int h) {
    return {clampWh(w, 120, 980), clampWh(h, 260, 1360)};
}

double kcViewportIsoScale(int w, int h) {
    const auto [aw, ah] = kcViewportWhValid(w, h);
    const double rx = static_cast<double>(aw) / static_cast<double>(kBodyRefWidth);
    const double ry = static_cast<double>(ah) / static_cast<double>(kBodyRefHeight);
    const double iso = std::sqrt(std::max(1e-4, rx * ry));
    return std::clamp(iso, kIsoLo, kIsoHi);
}

double kcViewportWidthScale(int w, int h) {
    const auto [aw, _ah] = kcViewportWhValid(w, h);
    const double rx = static_cast<double>(aw) / static_cast<double>(kBodyRefWidth);
    return std::clamp(rx, kIsoLo, kIsoHi);
}

double kcViewportHeightScale(int w, int h) {
    const auto [_aw, ah] = kcViewportWhValid(w, h);
    const double ry = static_cast<double>(ah) / static_cast<double>(kBodyRefHeight);
    return std::clamp(ry, kIsoLo, kIsoHi);
}

int kcViewportPxH(double ws, double design_px, int lo, int hi) {
    const int raw = pipela::ui::theme::scalePxH(static_cast<int>(std::lround(design_px)), kBodyRefWidth);
    const int v = static_cast<int>(std::lround(static_cast<double>(raw) * ws));
    return clampWh(v, lo, hi);
}

int kcViewportPxV(double vs, double design_px, int lo, int hi) {
    const int raw = pipela::ui::theme::scalePxV(static_cast<int>(std::lround(design_px)), kBodyRefHeight);
    const int v = static_cast<int>(std::lround(static_cast<double>(raw) * vs));
    return clampWh(v, lo, hi);
}

std::pair<int, int> kcViewportWhFromWidgetChain(QWidget* owner) {
    QWidget* p = owner;
    for (int depth = 0; p != nullptr && depth < 32; ++depth, p = p->parentWidget()) {
        const QVariant vw = p->property("_kc_vw");
        const QVariant vh = p->property("_kc_vh");
        if (vw.isValid() && vh.isValid()) {
            const int w = vw.toInt();
            const int h = vh.toInt();
            if (w >= 120 && h >= 260) {
                return {w, h};
            }
        }
    }
    return kcViewportWhValid(kBodyRefWidth, kBodyRefHeight);
}

}  // namespace pipela::app::overlays::kc_metrics
