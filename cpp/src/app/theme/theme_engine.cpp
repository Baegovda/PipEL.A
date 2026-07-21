#include "theme/theme_engine.hpp"

#include <QApplication>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPalette>

#include "theme/ui_adaptive.hpp"

namespace pipela::ui::theme {

namespace {

QJsonObject g_tokens;
bool g_loaded = false;

QString tokenString(const char* key, const QString& fallback) {
    const auto it = g_tokens.find(QString::fromUtf8(key));
    if (it != g_tokens.end() && it->isString()) {
        return it->toString();
    }
    return fallback;
}

int tokenInt(const char* key, int fallback) {
    const auto it = g_tokens.find(QString::fromUtf8(key));
    if (it != g_tokens.end() && it->isDouble()) {
        return static_cast<int>(it->toDouble());
    }
    return fallback;
}

}  // namespace

void loadThemeEngine() {
    g_tokens = QJsonObject();
    g_loaded = false;
    QFile f(QString::fromUtf8(":/theme/pipela_theme.json"));
    if (!f.open(QIODevice::ReadOnly)) {
        return;
    }
    const auto doc = QJsonDocument::fromJson(f.readAll());
    if (!doc.isObject()) {
        return;
    }
    g_tokens = doc.object();
    g_loaded = true;
}

bool themeEngineLoaded() { return g_loaded; }

QString color(const char* key, const QString& fallback) {
    return tokenString(key, fallback.isEmpty() ? QString::fromUtf8("#f2f6f4") : fallback);
}

QColor qColor(const char* key, const QColor& fallback) {
    const QString raw = color(key);
    QColor c(raw);
    return c.isValid() ? c : fallback;
}

int radiusPx(const char* key, int fallback) { return tokenInt(key, fallback); }

QString globalInteractionQss(const QString& scope_selector) {
    const QString scope =
        scope_selector.trimmed().isEmpty()
            ? QString::fromUtf8("QWidget#pipelaControlRoot")
            : scope_selector.trimmed();
    const QString prefix = scope + QLatin1Char(' ');
    const QString accent = color("ACCENT");
    const QString fg = color("FG");
    const QString fg_dim = color("FG_DIM");
    const QString btn_bg = color("BTN_BG");
    const QString btn_hover = color("BTN_HOVER");
    const QString btn_pressed = color("BTN_PRESSED");
    const QString panel_bg = color("PANEL_BG");
    const QString border = color("BORDER_DEFAULT");
    const QString accent_soft = color("ACCENT_SOFT");
    const int r = radiusPx("RADIUS_SM", 8);
    const int pad_v = scalePxV(8, 720);
    const int pad_h = scalePxH(10, 420);
    return QString::fromUtf8(
               "%15QPushButton {"
               " background-color: %1; color: %2; border: 1px solid %3;"
               " padding: %7px %8px; border-radius: %4px; font-weight: 500; }"
               "%15QPushButton:hover { background-color: %5; border-color: %6; color: %2; }"
               "%15QPushButton:pressed { background-color: %9; border-color: %3; color: %2; }"
               "%15QPushButton:disabled { background-color: %10; color: %11; border-color: %3; }"
               "%15QToolButton { background: transparent; border: none; padding: 4px; border-radius: %4px; }"
               "%15QToolButton:hover { background-color: %12; }"
               "%15QToolButton:pressed { background-color: %9; }"
               "%15QCheckBox { color: %2; spacing: 6px; }"
               "%15QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px;"
               " border: 1px solid %3; background: %1; }"
               "%15QCheckBox::indicator:checked { background: %12; border-color: %6; }"
               "%15QComboBox, %15QSpinBox, %15QDoubleSpinBox, %15QLineEdit {"
               " background: %1; color: %2; border: 1px solid %3; border-radius: %4px; padding: 4px 8px; }"
               "%15QComboBox:hover, %15QSpinBox:hover, %15QDoubleSpinBox:hover, %15QLineEdit:hover {"
               " border-color: %6; }"
               "%15QComboBox:focus, %15QSpinBox:focus, %15QDoubleSpinBox:focus, %15QLineEdit:focus {"
               " border-color: %6; }"
               "%15QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }"
               "%15QScrollBar::handle:vertical { background: %13; border-radius: 4px; min-height: 24px; }"
               "%15QScrollBar::handle:vertical:hover { background: %14; }"
               "%15QScrollBar::add-line:vertical, %15QScrollBar::sub-line:vertical { height: 0; }"
               "%15QScrollBar::add-page:vertical, %15QScrollBar::sub-page:vertical { background: transparent; }")
        .arg(btn_bg, fg, border)
        .arg(r)
        .arg(btn_hover, accent)
        .arg(pad_v)
        .arg(pad_h)
        .arg(btn_pressed, panel_bg, fg_dim, accent_soft)
        .arg(color("SCROLLBAR_HANDLE"), color("SCROLLBAR_HANDLE_HOVER"))
        .arg(prefix);
}

QString actionGridGlassQss(bool enabled, bool emitting, int layout_width_px) {
    const int radius = scalePxH(radiusPx("RADIUS_MD", 12), layout_width_px);
    QString bg;
    QString border;
    if (!enabled) {
        bg = color("GLASS_OFF_BG");
        border = color("GLASS_BORDER_OFF");
    } else if (emitting) {
        bg = color("GLASS_EMIT_BG");
        border = color("GLASS_BORDER_ON");
    } else {
        bg = color("GLASS_ON_BG");
        border = color("GLASS_BORDER_ON");
    }
    const QString fg = enabled ? color("FG") : color("FG_SECONDARY");
    const QString hover_border = color("GLASS_BORDER_HOVER");
    const QString hover_fg = color("FG");
    return QString::fromUtf8(
               "QPushButton { background: %1; color: %2; font-weight: 600; font-size: 10px; "
               "border: 1px solid %3; border-radius: %4px; padding: 8px 10px; text-align: center; }"
               "QPushButton:hover { border: 1px solid %5; color: %6; }"
               "QPushButton:pressed { background: %7; }")
        .arg(bg, fg, border)
        .arg(radius)
        .arg(hover_border, hover_fg, color("BTN_PRESSED"));
}

QString terminalViewQss() {
    return QString::fromUtf8(
               "QPlainTextEdit {"
               "  background: %1;"
               "  color: %2;"
               "  border: 1px solid %3;"
               "  border-radius: %4px;"
               "  padding: 10px 12px;"
               "  selection-background-color: %5;"
               "  selection-color: %6;"
               "}"
               "QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }"
               "QScrollBar::handle:vertical { background: %7; border-radius: 4px; min-height: 24px; }"
               "QScrollBar::handle:vertical:hover { background: %8; }"
               "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
               "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }")
        .arg(color("TERMINAL_BG"), color("TERMINAL_FG"), color("BORDER_SUBTLE"))
        .arg(radiusPx("RADIUS_MD", 12))
        .arg(color("TERMINAL_SELECTION_BG"), color("TERMINAL_SELECTION_FG"),
             color("SCROLLBAR_HANDLE"), color("SCROLLBAR_HANDLE_HOVER"));
}

QString cardFrameQss() {
    return QString::fromUtf8(
               "QWidget#pipelaCardFrame { background: %1; border: 1px solid %2; border-radius: %3px; }")
        .arg(color("CARD_BG"), color("BORDER_DEFAULT"))
        .arg(radiusPx("RADIUS_MD", 12));
}

QString cardTitleQss() {
    return QString::fromUtf8("color: %1; font-size: 14px; font-weight: 700;")
        .arg(color("FG"));
}

QString cardScrimQss() { return QString::fromUtf8("background: rgba(0, 0, 0, 88);"); }

QString textQss(const char* color_key, int font_px, int font_weight, int top_margin_px) {
    QString base =
        QString::fromUtf8("color: %1; font-size: %2px; font-weight: %3;")
            .arg(color(color_key))
            .arg(font_px)
            .arg(font_weight);
    if (top_margin_px > 0) {
        base += QString::fromUtf8(" margin-top: %1px;").arg(top_margin_px);
    }
    return base;
}

QString killCounterTileQss() {
    return QString::fromUtf8(
               "QFrame { background: %1; border: 1px solid %2; border-radius: %3px; }")
        .arg(color("KC_TILE_BG"), color("BORDER_DEFAULT"))
        .arg(radiusPx("RADIUS_SM", 8));
}

QString killCounterHubCardQss() {
    return QString::fromUtf8(
               "QFrame { background: %1; border: 1px solid %2; border-radius: %3px; }")
        .arg(color("KC_CARD_BG"), color("BORDER_DEFAULT"))
        .arg(radiusPx("RADIUS_MD", 12));
}

QString killCounterProgressQss(const QString& chunk_color) {
    return QString::fromUtf8(
               "QProgressBar { background: %1; border: 1px solid %2; border-radius: %3px; }"
               "QProgressBar::chunk { background: %4; border-radius: %5px; }")
        .arg(color("KC_PROGRESS_BG"), color("BORDER_DEFAULT"))
        .arg(radiusPx("RADIUS_SM", 8))
        .arg(chunk_color)
        .arg(radiusPx("RADIUS_SM", 8) - 1);
}

QString killCounterLapButtonQss(const QString& font_pt) {
    const QString fpt = font_pt.isEmpty() ? QString::fromUtf8("10px") : font_pt;
    return QString::fromUtf8(
               "QPushButton { background: %1; color: %2; border: 1px solid %3; border-radius: %4px; "
               "padding: 4px 10px; font-size: %5; font-weight: 600; text-align: center; }"
               "QPushButton:hover { background: %6; border-color: %7; }")
        .arg(color("ACCENT_SOFT"), color("FG"), color("ACCENT_BORDER"))
        .arg(radiusPx("RADIUS_SM", 8))
        .arg(fpt)
        .arg(color("BTN_HOVER"))
        .arg(color("ACCENT"));
}

QString killCounterDangerButtonQss(bool strong, const QString& font_pt) {
    const QString fpt = font_pt.isEmpty() ? QString::fromUtf8("10px") : font_pt;
    const QString bg = strong ? color("DANGER_HOVER_BG") : color("DANGER_SOFT");
    return QString::fromUtf8(
               "QPushButton { background: %1; color: %2; border: 1px solid %3; border-radius: %4px; "
               "padding: 5px 10px; font-size: %5; font-weight: 600; text-align: center; }"
               "QPushButton:hover { border-color: %6; color: %2; }")
        .arg(bg, color("FG"), color("BORDER_DEFAULT"))
        .arg(radiusPx("RADIUS_SM", 8))
        .arg(fpt)
        .arg(color("DANGER"));
}

QString killCounterHeroCardQss() {
    return QString::fromUtf8(
               "QFrame#pipelaKcHeroCard {"
               "  background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
               "    stop:0 %1, stop:1 %2);"
               "  border: 1px solid %3; border-radius: %4px; }")
        .arg(color("ACCENT_SOFT"), color("KC_CARD_BG"), color("ACCENT_BORDER"))
        .arg(radiusPx("RADIUS_LG", 16));
}

QString killCounterSectionAccentBarQss() {
    return QString::fromUtf8("background: %1; border: none; border-radius: 2px;")
        .arg(color("ACCENT"));
}

QString killCounterStatChipQss() {
    return QString::fromUtf8(
               "QFrame#pipelaKcStatChip {"
               "  background: %1; border: 1px solid %2; border-radius: %3px; }")
        .arg(color("SURFACE_ELEVATED"), color("BORDER_SUBTLE"))
        .arg(radiusPx("RADIUS_SM", 8));
}

QString killCounterPrimaryButtonQss(const QString& font_pt) {
    const QString fpt = font_pt.isEmpty() ? QString::fromUtf8("10px") : font_pt;
    return QString::fromUtf8(
               "QPushButton { background: %1; color: %2; border: 1px solid %3; border-radius: %4px; "
               "padding: 6px 12px; font-size: %5; font-weight: 700; text-align: center; }"
               "QPushButton:hover { background: %6; border-color: %6; }"
               "QPushButton:pressed { background: %7; }")
        .arg(color("ACCENT_MUTED"), color("WINDOW_BG"), color("ACCENT"))
        .arg(radiusPx("RADIUS_SM", 8))
        .arg(fpt)
        .arg(color("ACCENT"))
        .arg(color("ACCENT_MUTED"));
}

QString killCounterGhostButtonQss(const QString& font_pt) {
    const QString fpt = font_pt.isEmpty() ? QString::fromUtf8("10px") : font_pt;
    return QString::fromUtf8(
               "QPushButton { background: transparent; color: %1; border: 1px solid %2; "
               "border-radius: %3px; padding: 6px 10px; font-size: %4; font-weight: 600;"
               " text-align: center; }"
               "QPushButton:hover { background: %5; border-color: %6; color: %7; }")
        .arg(color("FG_SECONDARY"), color("BORDER_DEFAULT"))
        .arg(radiusPx("RADIUS_SM", 8))
        .arg(fpt)
        .arg(color("BTN_HOVER"))
        .arg(color("BORDER_STRONG"))
        .arg(color("FG"));
}

QString killCounterGoalBlockQss() {
    return QString::fromUtf8(
               "QFrame#pipelaKcGoalBlock {"
               "  background: %1; border: 1px solid %2; border-radius: %3px; }")
        .arg(color("SURFACE_ELEVATED"), color("BORDER_SUBTLE"))
        .arg(radiusPx("RADIUS_SM", 8));
}

QString killCounterWindowChromeQss() {
    return QString::fromUtf8(
               "background-color: %1; border: 1px solid %2; border-radius: %3px;")
        .arg(color("PANEL_BG"), color("BORDER_DEFAULT"))
        .arg(radiusPx("RADIUS_MD", 12));
}

void applyFullTheme(QApplication& app) {
    loadThemeEngine();
    QPalette pal = app.palette();
    const QColor window = qColor("WINDOW_BG", QColor(10, 13, 16));
    const QColor surface = qColor("SURFACE_ELEVATED", QColor(24, 30, 37));
    const QColor fg = qColor("FG", QColor(242, 246, 244));
    const QColor fg_muted = qColor("FG_SECONDARY", QColor(154, 171, 159));
    const QColor accent = qColor("ACCENT", QColor(64, 232, 216));
    pal.setColor(QPalette::Window, window);
    pal.setColor(QPalette::WindowText, fg);
    pal.setColor(QPalette::Base, surface);
    pal.setColor(QPalette::AlternateBase, qColor("PANEL_BG", window));
    pal.setColor(QPalette::Text, fg);
    pal.setColor(QPalette::Button, qColor("BTN_BG", surface));
    pal.setColor(QPalette::ButtonText, fg);
    pal.setColor(QPalette::BrightText, accent);
    pal.setColor(QPalette::Highlight, qColor("ACCENT_SOFT", accent));
    pal.setColor(QPalette::HighlightedText, fg);
    pal.setColor(QPalette::PlaceholderText, fg_muted);
    pal.setColor(QPalette::Disabled, QPalette::Text, qColor("FG_DIM", fg_muted));
    pal.setColor(QPalette::Disabled, QPalette::ButtonText, qColor("FG_DIM", fg_muted));
    app.setPalette(pal);
}

}  // namespace pipela::ui::theme
