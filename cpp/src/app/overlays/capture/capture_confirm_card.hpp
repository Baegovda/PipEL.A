#pragma once

#include <cstdint>
#include <functional>

#include <QString>

#include "pipela/core/vision/capture.hpp"

class QWidget;

namespace pipela::ui::overlays::capture {

void showCaptureConfirmCard(QWidget* host, const QString& title,
                            const pipela::core::vision::BgrImage& preview,
                            std::intptr_t anchor_hwnd, std::function<void(bool accepted)> on_done);

}  // namespace pipela::ui::overlays::capture
