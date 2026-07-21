#pragma once

#include <QPixmap>

#include "pipela/core/vision/capture.hpp"

namespace pipela::app::widgets {

QPixmap pixmapFromBgr(const pipela::core::vision::BgrImage& bgr, int max_w, int max_h);

// AGENT: OpenCV first — Qt imageformats plugin may be absent in deployed builds.
QPixmap pixmapFromTemplatePngPath(const QString& path, int max_w, int max_h);

}  // namespace pipela::app::widgets
