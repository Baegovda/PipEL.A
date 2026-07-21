#pragma once

#include <cstdint>

#include <QString>

class QLabel;

#include "dock/dock_ui_phase.hpp"

namespace pipela::ui::theme {

QString stripResolutionBlockHtml(std::intptr_t anchor_hwnd,
                                 std::intptr_t game_hwnd,
                                 std::intptr_t launcher_hwnd,
                                 pipela::ui::dock::UiDockPhase phase);

QString controlResolutionBlockHtml(std::intptr_t game_hwnd,
                                   std::intptr_t launcher_hwnd,
                                   pipela::ui::dock::UiDockPhase phase);

QString resolutionChromeContentKey(std::intptr_t anchor_hwnd,
                                   std::intptr_t game_hwnd,
                                   std::intptr_t launcher_hwnd,
                                   pipela::ui::dock::UiDockPhase phase);

void applyResolutionRichLabelFixed(QLabel* label,
                                   const QString& block_html,
                                   double design_scale = 1.0);

void applyResolutionRichLabelFit(QLabel* label,
                                 const QString& block_html,
                                 double avail_css_px,
                                 double design_scale = 1.0);

}  // namespace pipela::ui::theme
