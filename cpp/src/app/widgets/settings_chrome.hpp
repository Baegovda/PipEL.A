#pragma once

#include <QString>

class QHBoxLayout;
class QLabel;
class QLayout;
class QScrollArea;
class QVBoxLayout;
class QWidget;

namespace pipela::app::widgets {

int settingsRootVerticalSpacing();
QString settingsSectionHeadingStyle(int top_margin_px = 0);
QString settingsCaptionStyle();
void configureSettingsScrollArea(QScrollArea* scroll);
void settingsLabelAlignCenterH(QLabel* label);

// AGENT: Shared settings page layout — vertically stacked, horizontally centered children.
QVBoxLayout* createSettingsPageLayout(QWidget* page);
void addSettingsCenteredWidget(QVBoxLayout* layout, QWidget* widget, int stretch = 0);
void addSettingsCenteredLayout(QVBoxLayout* layout, QLayout* inner);
void addSettingsCheckboxRow(QVBoxLayout* layout, QWidget* checkbox);
void addSettingsProseLabel(QVBoxLayout* layout, QLabel* label);

void addSettingsFieldRow(QVBoxLayout* layout, const QString& caption, QWidget* control,
                         QWidget* suffix = nullptr);

}  // namespace pipela::app::widgets
