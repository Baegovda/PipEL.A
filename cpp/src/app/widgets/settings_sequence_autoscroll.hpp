#pragma once

#include <functional>
#include <string>
#include <vector>

class QScrollArea;
class QWidget;

namespace pipela::app::widgets {

void applySequenceAutoscroll(QWidget* panel, QScrollArea* scroll, const std::string& feature,
                             const std::vector<QWidget*>& targets,
                             std::function<bool()> active_check = {});

}  // namespace pipela::app::widgets
