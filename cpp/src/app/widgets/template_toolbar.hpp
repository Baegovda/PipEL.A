#pragma once

#include <functional>

#include <QString>

class QVBoxLayout;

namespace pipela::app::widgets {

struct TemplateToolbarCallbacks {
    std::function<void()> on_capture;
    std::function<void()> on_test;
    std::function<void()> on_preview;
    std::function<void()> on_region;
    std::function<void()> on_clear;
    std::function<void(const QString&)> log;
};

void addTemplateToolbar(QVBoxLayout* layout, const QString& capture_kind,
                        const TemplateToolbarCallbacks& callbacks);

}  // namespace pipela::app::widgets
