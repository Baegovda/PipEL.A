#pragma once

#include <QTabWidget>

namespace pipela::ui::widgets {

// AGENT: QTabWidget with PairedControlTabBar installed (setTabBar is protected on QTabWidget).
class PairedControlTabWidget : public QTabWidget {
    Q_OBJECT
public:
    explicit PairedControlTabWidget(QWidget* parent = nullptr);
};

}  // namespace pipela::ui::widgets
