#pragma once

#include <QString>

class QLabel;
class QVBoxLayout;
class QWidget;

namespace pipela::app::widgets {

struct TemplateLastMatchThumbRow {
    QLabel* target_caption{nullptr};
    QLabel* match_caption{nullptr};
    QLabel* target_thumb{nullptr};
    QLabel* match_thumb{nullptr};
};

TemplateLastMatchThumbRow createTemplateLastMatchThumbRow(QWidget* parent, QVBoxLayout* parent_lay,
                                                          QLabel* target_thumb = nullptr);

void updateTemplateLastMatchThumbnail(TemplateLastMatchThumbRow& row, const QString& capture_kind,
                                      QLabel* orig_template_thumb);

}  // namespace pipela::app::widgets
