#pragma once

#include <QColor>
#include <QString>

class QApplication;

namespace pipela::ui::theme {

// AGENT: Single design-token loader — colors from :/theme/pipela_theme.json.
void loadThemeEngine();
bool themeEngineLoaded();

QString color(const char* key, const QString& fallback = QString());
QColor qColor(const char* key, const QColor& fallback = QColor());
int radiusPx(const char* key, int fallback);

QString globalInteractionQss(const QString& scope_selector = QString::fromUtf8(
    "QWidget#pipelaControlRoot"));
QString actionGridGlassQss(bool enabled, bool emitting, int layout_width_px);
QString terminalViewQss();
QString cardFrameQss();
QString cardTitleQss();
QString cardScrimQss();

QString textQss(const char* color_key, int font_px, int font_weight = 400, int top_margin_px = 0);
QString killCounterTileQss();
QString killCounterHubCardQss();
QString killCounterProgressQss(const QString& chunk_color);
QString killCounterLapButtonQss(const QString& font_pt = QString());
QString killCounterDangerButtonQss(bool strong = false, const QString& font_pt = QString());
QString killCounterHeroCardQss();
QString killCounterSectionAccentBarQss();
QString killCounterStatChipQss();
QString killCounterPrimaryButtonQss(const QString& font_pt = QString());
QString killCounterGhostButtonQss(const QString& font_pt = QString());
QString killCounterGoalBlockQss();
QString killCounterWindowChromeQss();

void applyFullTheme(QApplication& app);

}  // namespace pipela::ui::theme
