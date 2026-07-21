#pragma once

#include <QWidget>

namespace pipela::app::panels::settings {

struct SettingsPanelContext;

QWidget* createInterfacePanel(QWidget* parent, const SettingsPanelContext& ctx);
QWidget* createConsolePanel(QWidget* parent, const SettingsPanelContext& ctx);
QWidget* createFlameTriggerPanel(QWidget* parent);
QWidget* createUpdatePanel(QWidget* parent,
                           const pipela::app::panels::settings::SettingsPanelContext& ctx);
QWidget* createTesseractPanel(QWidget* parent);

}  // namespace pipela::app::panels::settings
