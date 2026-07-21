#include "widgets/settings_chrome.hpp"

#include <QString>

#include <QHBoxLayout>
#include <QLabel>
#include <QFrame>
#include <QScrollArea>
#include <QVBoxLayout>

#include "theme/theme_engine.hpp"
#include "theme/ui_adaptive.hpp"

namespace pipela::app::widgets {

int settingsRootVerticalSpacing() { return pipela::ui::theme::scalePxV(8, 720); }

QString settingsSectionHeadingStyle(int top_margin_px) {
    return pipela::ui::theme::textQss("FG", 14, 600, top_margin_px);
}

QString settingsCaptionStyle() {
    return pipela::ui::theme::textQss("FG_SECONDARY", 11, 500);
}

void configureSettingsScrollArea(QScrollArea* scroll) {
    if (scroll == nullptr) {
        return;
    }
    scroll->setWidgetResizable(true);
    scroll->setFrameShape(QFrame::NoFrame);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
}

void settingsLabelAlignCenterH(QLabel* label) {
    if (label != nullptr) {
        label->setAlignment(Qt::AlignHCenter | Qt::AlignVCenter);
    }
}

QVBoxLayout* createSettingsPageLayout(QWidget* page) {
    auto* lay = new QVBoxLayout(page);
    lay->setSpacing(settingsRootVerticalSpacing());
    lay->setContentsMargins(0, 0, 0, 0);
    return lay;
}

void addSettingsCenteredWidget(QVBoxLayout* layout, QWidget* widget, int stretch) {
    if (layout == nullptr || widget == nullptr) {
        return;
    }
    layout->addWidget(widget, stretch, Qt::AlignHCenter);
}

void addSettingsCenteredLayout(QVBoxLayout* layout, QLayout* inner) {
    if (layout == nullptr || inner == nullptr) {
        return;
    }
    auto* row = new QHBoxLayout();
    row->setContentsMargins(0, 0, 0, 0);
    row->addStretch(1);
    row->addLayout(inner);
    row->addStretch(1);
    layout->addLayout(row);
}

void addSettingsCheckboxRow(QVBoxLayout* layout, QWidget* checkbox) {
    if (layout == nullptr || checkbox == nullptr) {
        return;
    }
    auto* row = new QHBoxLayout();
    row->setContentsMargins(0, 0, 0, 0);
    row->addStretch(1);
    row->addWidget(checkbox, 0, Qt::AlignHCenter);
    row->addStretch(1);
    layout->addLayout(row);
}

void addSettingsProseLabel(QVBoxLayout* layout, QLabel* label) {
    if (layout == nullptr || label == nullptr) {
        return;
    }
    settingsLabelAlignCenterH(label);
    layout->addWidget(label);
}

void addSettingsFieldRow(QVBoxLayout* layout, const QString& caption, QWidget* control,
                         QWidget* suffix) {
    if (layout == nullptr || control == nullptr) {
        return;
    }
    auto* block = new QVBoxLayout();
    block->setSpacing(pipela::ui::theme::scalePxV(4, 720));
    if (!caption.isEmpty()) {
        auto* cap = new QLabel(caption);
        cap->setStyleSheet(settingsCaptionStyle());
        settingsLabelAlignCenterH(cap);
        block->addWidget(cap, 0, Qt::AlignHCenter);
    }
    auto* control_row = new QHBoxLayout();
    control_row->setSpacing(pipela::ui::theme::scalePxH(8, 420));
    control_row->addStretch(1);
    control_row->addWidget(control, 0, Qt::AlignHCenter);
    if (suffix != nullptr) {
        control_row->addWidget(suffix, 0, Qt::AlignHCenter);
    }
    control_row->addStretch(1);
    block->addLayout(control_row);
    addSettingsCenteredLayout(layout, block);
}

}  // namespace pipela::app::widgets
