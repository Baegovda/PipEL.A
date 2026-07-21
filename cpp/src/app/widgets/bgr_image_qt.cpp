#include "widgets/bgr_image_qt.hpp"

#include <QImage>
#include <QPixmap>

#include "pipela/core/vision/capture.hpp"

namespace pipela::app::widgets {

QPixmap pixmapFromBgr(const pipela::core::vision::BgrImage& bgr, int max_w, int max_h) {
    if (bgr.bytes.empty() || bgr.width < 1 || bgr.height < 1) {
        return {};
    }
    QImage qimg(bgr.bytes.data(), bgr.width, bgr.height, bgr.width * 3, QImage::Format_RGB888);
    QPixmap pm = QPixmap::fromImage(qimg.rgbSwapped());
    if (pm.isNull()) {
        return {};
    }
    if (max_w > 0 && max_h > 0) {
        pm = pm.scaled(max_w, max_h, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    }
    return pm;
}

QPixmap pixmapFromTemplatePngPath(const QString& path, int max_w, int max_h) {
    if (path.isEmpty()) {
        return {};
    }
#if defined(PIPELA_HAS_OPENCV)
    if (auto bgr = pipela::core::vision::loadBgrFromPath(path.toStdString())) {
        return pixmapFromBgr(*bgr, max_w, max_h);
    }
#endif
    QPixmap pm(path);
    if (pm.isNull()) {
        return {};
    }
    if (max_w > 0 && max_h > 0) {
        pm = pm.scaled(max_w, max_h, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    }
    return pm;
}

}  // namespace pipela::app::widgets
