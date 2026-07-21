#pragma once

class QHBoxLayout;
class QVBoxLayout;

namespace pipela::ui::overlays {

class TemplateOverlayController;

void attachKillCounterRegionToolbar(QHBoxLayout* merge_row, TemplateOverlayController* controller);

}  // namespace pipela::ui::overlays
