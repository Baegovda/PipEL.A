#pragma once

class QApplication;
class QWidget;

namespace pipela::ui::theme {

// AGENT: Broadcast global font pt to open Qt chrome (Python qt_typography_refresh parity).
void refreshPipelaTypography(QApplication* app, QWidget* control_root, int font_pt);

}  // namespace pipela::ui::theme
