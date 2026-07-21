#include "theme/resolution_chrome.hpp"

#include <cmath>

#include <QApplication>
#include <QFont>
#include <QLabel>
#include <QTextDocument>

#include "dock/dock_ui_phase.hpp"
#include "pipela/core/vision/roi.hpp"
#include "pipela/core/win32/game_windows.hpp"
#include "theme/dpi_helpers.hpp"
#include "theme/ui_adaptive.hpp"

namespace pipela::ui::theme {

namespace {

QString muted(const QString& text) {
    return QString::fromUtf8("<span style=\"color:#7a8a82;\">%1</span>").arg(text);
}

QString val(const QString& text) {
    return QString::fromUtf8("<span style=\"color:#3dd4c9; font-weight:600;\">%1</span>")
        .arg(text);
}

QString warn(const QString& text) {
    return QString::fromUtf8("<span style=\"color:#e8b060; font-weight:600;\">%1</span>")
        .arg(text);
}

QString sep() { return QString::fromUtf8("<span style=\"color:#2a3438;\">·</span>"); }

QString dpiFragment(std::intptr_t hwnd) {
    const double scale = win32DpiScaleForHwnd(hwnd);
    const int pct = static_cast<int>(std::lround(scale * 100.0));
    const int dpi = static_cast<int>(std::lround(scale * 96.0));
    return QString::fromUtf8("%1&nbsp;%2&#8239;%3")
        .arg(muted(QString::fromUtf8("DPI")))
        .arg(val(QString::fromUtf8("%1%").arg(pct)))
        .arg(val(QString::number(dpi)));
}

QString clientTemplateLine(int client_w, int client_h) {
    const double ratio =
        static_cast<double>(std::max(1, client_h)) / static_cast<double>(pipela::core::vision::kBaseHeight);
    return QString::fromUtf8("%1&nbsp;%2%3%4&nbsp;%5%6")
        .arg(muted(QString::fromUtf8("클라")))
        .arg(val(QString::fromUtf8("%1×%2").arg(client_w).arg(client_h)))
        .arg(sep())
        .arg(muted(QString::fromUtf8("템플릿")))
        .arg(val(QString::number(ratio, 'f', 3)))
        .arg(muted(QString::fromUtf8("&nbsp;(1440p)")));
}

std::pair<int, int> clientSizeLogical(std::intptr_t hwnd) {
    const auto cr = pipela::core::win32::getClientRectScreen(hwnd);
    return {std::get<2>(cr) - std::get<0>(cr), std::get<3>(cr) - std::get<1>(cr)};
}

QString resLineWrap(const QString& inner_html, double letter_spacing_em) {
    return QString::fromUtf8(
               "<div style=\"white-space:nowrap; letter-spacing:%1em;\">%2</div>")
        .arg(letter_spacing_em, 0, 'f', 3)
        .arg(inner_html);
}

double measureResRichWidth(const QFont& font, const QString& html) {
    QTextDocument doc;
    doc.setDefaultFont(font);
    doc.setHtml(html);
    doc.setTextWidth(-1);
    return static_cast<double>(doc.idealWidth());
}

constexpr double kResFitLetterSpacingEm[] = {
    0.03, 0.02, 0.01, 0.0, -0.015, -0.03, -0.045, -0.06, -0.075, -0.09,
};
constexpr double kResFitBaseDesignPt = 10.5;
constexpr double kResFitMinDesignPt = 3.85;
constexpr double kResFitAbsoluteMinDesignPt = 1.55;
constexpr double kResFitPtStep = 0.35;
constexpr double kResFitPtStepFine = 0.12;

}  // namespace

QString stripResolutionBlockHtml(std::intptr_t anchor_hwnd,
                                 std::intptr_t game_hwnd,
                                 std::intptr_t launcher_hwnd,
                                 pipela::ui::dock::UiDockPhase phase) {
    if (phase == pipela::ui::dock::UiDockPhase::Client && game_hwnd &&
        pipela::core::win32::isWindow(game_hwnd)) {
        if (pipela::core::win32::isWindowMinimized(game_hwnd)) {
            return warn(QString::fromUtf8("게임 최소화"))
                .append(sep())
                .append(muted(QString::fromUtf8("캡처·매칭 대기")))
                .append(sep())
                .append(dpiFragment(game_hwnd));
        }
        const auto [gw, gh] = clientSizeLogical(game_hwnd);
        if (gw > 0 && gh > 0) {
            return clientTemplateLine(gw, gh).append(sep()).append(dpiFragment(game_hwnd));
        }
    }
    if (launcher_hwnd && pipela::core::win32::isWindow(launcher_hwnd) &&
        !pipela::core::win32::isWindowMinimized(launcher_hwnd)) {
        const auto [lw, lh] = clientSizeLogical(launcher_hwnd);
        if (lw > 0 && lh > 0) {
            return clientTemplateLine(lw, lh).append(sep()).append(dpiFragment(launcher_hwnd));
        }
        return muted(QString::fromUtf8("연결"))
            .append(QString::fromUtf8("&nbsp;"))
            .append(val(QString::fromUtf8("런처만")))
            .append(sep())
            .append(dpiFragment(launcher_hwnd));
    }
    if (anchor_hwnd && pipela::core::win32::isWindow(anchor_hwnd)) {
        return muted(QString::fromUtf8("이터널시티 창 없음")).append(sep()).append(
            dpiFragment(anchor_hwnd));
    }
    return muted(QString::fromUtf8("이터널시티 창 없음"));
}

QString controlResolutionBlockHtml(std::intptr_t game_hwnd,
                                   std::intptr_t launcher_hwnd,
                                   pipela::ui::dock::UiDockPhase phase) {
    const std::intptr_t anchor =
        (phase == pipela::ui::dock::UiDockPhase::Launcher && launcher_hwnd) ? launcher_hwnd
                                                                              : game_hwnd;
    return stripResolutionBlockHtml(anchor, game_hwnd, launcher_hwnd, phase);
}

QString resolutionChromeContentKey(std::intptr_t anchor_hwnd,
                                   std::intptr_t game_hwnd,
                                   std::intptr_t launcher_hwnd,
                                   pipela::ui::dock::UiDockPhase phase) {
    if (phase == pipela::ui::dock::UiDockPhase::Client && game_hwnd &&
        pipela::core::win32::isWindow(game_hwnd)) {
        if (pipela::core::win32::isWindowMinimized(game_hwnd)) {
            return QString::fromUtf8("gmin:%1").arg(game_hwnd);
        }
        const auto [gw, gh] = clientSizeLogical(game_hwnd);
        const double ratio =
            static_cast<double>(std::max(1, gh)) / static_cast<double>(pipela::core::vision::kBaseHeight);
        const int dpi = static_cast<int>(std::lround(win32DpiScaleForHwnd(game_hwnd) * 96.0));
        return QString::fromUtf8("game:%1:%2:%3:%4:%5")
            .arg(game_hwnd)
            .arg(gw)
            .arg(gh)
            .arg(ratio, 0, 'f', 4)
            .arg(dpi);
    }
    if (launcher_hwnd && pipela::core::win32::isWindow(launcher_hwnd) &&
        !pipela::core::win32::isWindowMinimized(launcher_hwnd)) {
        const auto [lw, lh] = clientSizeLogical(launcher_hwnd);
        const int dpi = static_cast<int>(std::lround(win32DpiScaleForHwnd(launcher_hwnd) * 96.0));
        if (lw > 0 && lh > 0) {
            const double ratio =
                static_cast<double>(lh) / static_cast<double>(pipela::core::vision::kBaseHeight);
            return QString::fromUtf8("lsz:%1:%2:%3:%4:%5")
                .arg(launcher_hwnd)
                .arg(lw)
                .arg(lh)
                .arg(ratio, 0, 'f', 4)
                .arg(dpi);
        }
        return QString::fromUtf8("lonly:%1:%2").arg(launcher_hwnd).arg(dpi);
    }
    const int dpi = anchor_hwnd ? static_cast<int>(std::lround(win32DpiScaleForHwnd(anchor_hwnd) * 96.0))
                                : 96;
    return QString::fromUtf8("none:%1").arg(dpi);
}

void applyResolutionRichLabelFixed(QLabel* label, const QString& block_html, double design_scale) {
    if (label == nullptr) {
        return;
    }
    const QString inner = block_html.trimmed();
    if (inner.isEmpty()) {
        label->hide();
        return;
    }
    const QString cache_key =
        QString::fromUtf8("fixed:%1:%2").arg(inner).arg(design_scale, 0, 'f', 4);
    if (label->property("pipelaResFitCache").toString() == cache_key) {
        return;
    }
    label->setProperty("pipelaResFitCache", cache_key);
    label->setMaximumWidth(16777215);
    const double root_pt = QApplication::font().pointSizeF();
    const double scale = (root_pt / 11.0) * design_scale;
    const double chosen_pt = 10.5 * scale;
    QFont fnt = label->font();
    fnt.setPointSizeF(chosen_pt);
    label->setFont(fnt);
    label->setText(resLineWrap(inner, 0.0));
    label->setMinimumHeight(std::max(8, pipela::ui::theme::scalePxV(8, label->height() > 0 ? label->height() : 24)));
    label->show();
}

void applyResolutionRichLabelFit(QLabel* label, const QString& block_html, double avail_css_px,
                                 double design_scale) {
    if (label == nullptr) {
        return;
    }
    const QString inner = block_html.trimmed();
    if (inner.isEmpty()) {
        label->hide();
        return;
    }
    const double avail = std::max(40.0, avail_css_px);
    const double avail_fit = std::max(40.0, avail - static_cast<double>(scalePxV(4, 24)));
    const int avail_i = std::max(40, static_cast<int>(std::lround(avail)));
    const double root_pt = QApplication::font().pointSizeF();
    const QString cache_key = QString::fromUtf8("fit:%1:%2:%3:%4")
                                  .arg(inner)
                                  .arg(avail_i)
                                  .arg(design_scale, 0, 'f', 4)
                                  .arg(root_pt, 0, 'f', 3);
    if (label->property("pipelaResFitCache").toString() == cache_key) {
        return;
    }
    label->setMaximumWidth(avail_i);
    const double fit_limit = std::max(24.0, avail_fit * 0.99);
    const double scale = (root_pt / 11.0) * design_scale;
    const double base_pt = kResFitBaseDesignPt * scale;
    const double coarse_floor = kResFitMinDesignPt * scale;
    const double abs_floor = kResFitAbsoluteMinDesignPt * scale;
    double chosen_pt = abs_floor;
    double chosen_lsem = kResFitLetterSpacingEm[9];
    bool found = false;
    double pt = base_pt;
    {
        QFont f_quick = label->font();
        f_quick.setPointSizeF(pt);
        const QString w_quick = resLineWrap(inner, kResFitLetterSpacingEm[0]);
        if (measureResRichWidth(f_quick, w_quick) <= fit_limit) {
            chosen_pt = pt;
            chosen_lsem = kResFitLetterSpacingEm[0];
            found = true;
        }
    }
    while (!found && pt >= coarse_floor - 1e-9) {
        for (double lsem : kResFitLetterSpacingEm) {
            QFont fnt = label->font();
            fnt.setPointSizeF(pt);
            if (measureResRichWidth(fnt, resLineWrap(inner, lsem)) <= fit_limit) {
                chosen_pt = pt;
                chosen_lsem = lsem;
                found = true;
                break;
            }
        }
        if (!found) {
            pt -= kResFitPtStep;
        }
    }
    if (!found) {
        pt = std::min(base_pt, coarse_floor);
        while (!found && pt >= abs_floor - 1e-9) {
            for (double lsem : kResFitLetterSpacingEm) {
                QFont fnt = label->font();
                fnt.setPointSizeF(pt);
                if (measureResRichWidth(fnt, resLineWrap(inner, lsem)) <= fit_limit) {
                    chosen_pt = pt;
                    chosen_lsem = lsem;
                    found = true;
                    break;
                }
            }
            if (!found) {
                pt -= kResFitPtStepFine;
            }
        }
    }
    QFont fnt = label->font();
    fnt.setPointSizeF(chosen_pt);
    label->setFont(fnt);
    label->setText(resLineWrap(inner, chosen_lsem));
    label->setMinimumHeight(std::max(8, scalePxV(8, label->height() > 0 ? label->height() : 24)));
    label->setProperty("pipelaResFitCache", cache_key);
    label->show();
}

}  // namespace pipela::ui::theme
