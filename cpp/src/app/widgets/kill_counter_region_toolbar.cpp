#include "widgets/kill_counter_region_toolbar.hpp"

#include <QHBoxLayout>
#include <QPushButton>
#include <QVBoxLayout>

#include "overlays/template_overlay_controller.hpp"
#include "theme/theme_engine.hpp"

namespace pipela::ui::overlays {

namespace {

QPushButton* makeToolButton(const QString& text, const QString& qss, QWidget* parent) {
    auto* btn = new QPushButton(text, parent);
    btn->setCursor(Qt::PointingHandCursor);
    btn->setStyleSheet(qss);
    return btn;
}

}  // namespace

void attachKillCounterRegionToolbar(QHBoxLayout* merge_row, TemplateOverlayController* controller) {
    if (merge_row == nullptr || controller == nullptr) {
        return;
    }
    QWidget* host = merge_row->parentWidget();
    if (host == nullptr) {
        return;
    }

    auto* prev = makeToolButton(QString::fromUtf8("미리보기"),
                                pipela::ui::theme::killCounterGhostButtonQss(), host);
    auto* reg = makeToolButton(QString::fromUtf8("영역 선택"),
                               pipela::ui::theme::killCounterPrimaryButtonQss(), host);
    auto* clr = makeToolButton(QString::fromUtf8("해제"),
                               pipela::ui::theme::killCounterDangerButtonQss(false), host);

    QObject::connect(prev, &QPushButton::clicked, host, [controller]() {
        controller->toggleRegionPreviewForType(QString::fromUtf8("kill_counter"),
                                               QString::fromUtf8("kill_counter_detect_region"),
                                               QString::fromUtf8("Kill Counter"));
    });
    QObject::connect(reg, &QPushButton::clicked, host, [controller]() {
        controller->startRegionSelectForType(QString::fromUtf8("kill_counter"),
                                             QString::fromUtf8("kill_counter_detect_region"),
                                             QString::fromUtf8("Kill Counter"));
    });
    QObject::connect(clr, &QPushButton::clicked, host, [controller]() {
        controller->clearMatchRegionForKey(QString::fromUtf8("kill_counter_detect_region"),
                                           QString::fromUtf8("Kill Counter"));
    });

    merge_row->insertWidget(0, prev);
    merge_row->insertWidget(1, reg);
    merge_row->insertWidget(2, clr);
}

}  // namespace pipela::ui::overlays
