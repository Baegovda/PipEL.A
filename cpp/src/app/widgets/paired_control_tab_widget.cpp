#include "widgets/paired_control_tab_widget.hpp"

#include "widgets/paired_control_tab_bar.hpp"

namespace pipela::ui::widgets {

PairedControlTabWidget::PairedControlTabWidget(QWidget* parent) : QTabWidget(parent) {
    setTabBar(new PairedControlTabBar(this));
}

}  // namespace pipela::ui::widgets
