#pragma once

#include <QWidget>

class QString;

namespace pipela::app::panels::settings {

QWidget* makeRegistryPrefixPanel(QWidget* parent, const QString& title, const QString& prefix);

}  // namespace pipela::app::panels::settings
