#include "widgets/template_last_match_thumb.hpp"

#include <QHBoxLayout>
#include <QLabel>
#include <QMouseEvent>
#include <QVBoxLayout>

#include "pipela/core/template/last_match_cache.hpp"
#include "theme/ui_adaptive.hpp"
#include "widgets/bgr_image_qt.hpp"
#include "widgets/card_popup_shell.hpp"
#include "widgets/settings_chrome.hpp"

namespace pipela::app::widgets {

namespace {

constexpr int kThumbMaxW = 148;
constexpr int kThumbMaxH = 90;
constexpr int kThumbSlotMinW = 92;
constexpr int kThumbSlotMinH = 56;

QString thumbSlotBaseQss() {
    return QString::fromUtf8("background: #1a1d24; border-radius: %1px;")
        .arg(pipela::ui::theme::scalePxV(4, 720));
}

QString thumbTargetCaptionStyle() {
    return QString::fromUtf8("color: #9aa0ac; font-size: 10px; font-weight: 600;");
}

QString thumbMatchCaptionStyle() {
    return QString::fromUtf8("color: #8ec8ff; font-size: 10px; font-weight: 600;");
}

void showPixmapPreview(QWidget* parent, const QPixmap& pm) {
    if (pm.isNull()) {
        return;
    }
    auto* dlg = new pipela::ui::widgets::CardFramelessDialog(parent);
    dlg->setAttribute(Qt::WA_DeleteOnClose);
    dlg->setTitleText(QString::fromUtf8("미리보기"));
    auto* img = new QLabel(dlg);
    img->setAlignment(Qt::AlignCenter);
    img->setPixmap(pm);
    dlg->setBodyWidget(img);
    dlg->resize(std::min(pm.width() + 48, 640), std::min(pm.height() + 80, 480));
    pipela::ui::widgets::centerCardPopup(dlg, parent);
    dlg->show();
}

void fitThumbLabel(QLabel* lbl, const QPixmap& pm, int min_w, int min_h,
                   const QString& empty_text) {
    if (lbl == nullptr) {
        return;
    }
    const QString base = thumbSlotBaseQss();
    lbl->setAlignment(Qt::AlignCenter);
    if (!pm.isNull()) {
        lbl->setText({});
        lbl->setPixmap(pm);
        lbl->setFixedSize(pm.size());
        lbl->setStyleSheet(base);
        return;
    }
    lbl->clear();
    lbl->setText(empty_text);
    lbl->setFixedSize(min_w, min_h);
    lbl->setStyleSheet(base + QString::fromUtf8(" color: #6a7080;"));
}

class ThumbZoomLabel : public QLabel {
public:
    using QLabel::QLabel;
    void setZoomPixmap(const QPixmap& pm) { zoom_ = pm; }

protected:
    void mouseReleaseEvent(QMouseEvent* event) override {
        QLabel::mouseReleaseEvent(event);
        if (event->button() == Qt::LeftButton && !zoom_.isNull()) {
            showPixmapPreview(window(), zoom_);
        }
    }

private:
    QPixmap zoom_;
};

QString formatLastMatchCaption(const QString& capture_kind) {
    const auto score =
        pipela::core::template_meta::getLastMatchScore(capture_kind.toStdString());
    if (!score) {
        return QString::fromUtf8("매칭된 이미지 · —");
    }
    return QString::fromUtf8("매칭된 이미지 · %1").arg(*score, 0, 'f', 2);
}

}  // namespace

TemplateLastMatchThumbRow createTemplateLastMatchThumbRow(QWidget* parent, QVBoxLayout* parent_lay,
                                                          QLabel* target_thumb) {
    TemplateLastMatchThumbRow row;
    const int min_w = pipela::ui::theme::scalePxH(kThumbSlotMinW, 420);
    const int min_h = pipela::ui::theme::scalePxV(kThumbSlotMinH, 720);

    auto* row_w = new QWidget(parent);
    auto* h = new QHBoxLayout(row_w);
    h->setContentsMargins(0, 0, 0, 0);
    h->setSpacing(pipela::ui::theme::scalePxH(12, 420));

    auto* left_col = new QVBoxLayout();
    left_col->setSpacing(pipela::ui::theme::scalePxV(4, 720));
    row.target_caption = new QLabel(QString::fromUtf8("목표 이미지"), row_w);
    row.target_caption->setWordWrap(true);
    row.target_caption->setStyleSheet(thumbTargetCaptionStyle());
    settingsLabelAlignCenterH(row.target_caption);
    left_col->addWidget(row.target_caption, 0, Qt::AlignHCenter);
    row.target_thumb = target_thumb != nullptr ? target_thumb : new ThumbZoomLabel(row_w);
    if (target_thumb == nullptr) {
        fitThumbLabel(row.target_thumb, {}, min_w, min_h, QString::fromUtf8("없음"));
    }
    left_col->addWidget(row.target_thumb, 0, Qt::AlignHCenter);

    auto* right_col = new QVBoxLayout();
    right_col->setSpacing(pipela::ui::theme::scalePxV(4, 720));
    row.match_caption = new QLabel(QString::fromUtf8("매칭된 이미지 · —"), row_w);
    row.match_caption->setWordWrap(true);
    row.match_caption->setStyleSheet(thumbMatchCaptionStyle());
    settingsLabelAlignCenterH(row.match_caption);
    right_col->addWidget(row.match_caption, 0, Qt::AlignHCenter);
    row.match_thumb = new ThumbZoomLabel(row_w);
    fitThumbLabel(row.match_thumb, {}, min_w, min_h, QString::fromUtf8("없음"));
    right_col->addWidget(row.match_thumb, 0, Qt::AlignHCenter);

    auto* lw = new QWidget(row_w);
    lw->setLayout(left_col);
    auto* rw = new QWidget(row_w);
    rw->setLayout(right_col);
    h->addWidget(lw, 1);
    h->addWidget(rw, 1);
    parent_lay->addWidget(row_w, 0, Qt::AlignHCenter);

    return row;
}

void updateTemplateLastMatchThumbnail(TemplateLastMatchThumbRow& row, const QString& capture_kind,
                                      QLabel* orig_template_thumb) {
    const int min_w = pipela::ui::theme::scalePxH(kThumbSlotMinW, 420);
    const int min_h = pipela::ui::theme::scalePxV(kThumbSlotMinH, 720);
    const int max_w = pipela::ui::theme::scalePxH(kThumbMaxW, 420);
    const int max_h = pipela::ui::theme::scalePxV(kThumbMaxH, 720);

    if (row.match_caption != nullptr) {
        row.match_caption->setText(formatLastMatchCaption(capture_kind));
    }

    if (orig_template_thumb != nullptr && row.target_thumb != nullptr) {
        const QPixmap pm = orig_template_thumb->pixmap(Qt::ReturnByValue);
        if (!pm.isNull()) {
            fitThumbLabel(row.target_thumb, pm, min_w, min_h, QString::fromUtf8("없음"));
            if (auto* zoom = dynamic_cast<ThumbZoomLabel*>(row.target_thumb)) {
                zoom->setZoomPixmap(pm);
            }
        }
    }

    if (row.match_thumb != nullptr) {
        if (auto patch =
                pipela::core::template_meta::getLastMatchPatchBgr(capture_kind.toStdString())) {
            const QPixmap pm = pixmapFromBgr(*patch, max_w, max_h);
            fitThumbLabel(row.match_thumb, pm, min_w, min_h, QString::fromUtf8("없음"));
            if (auto* zoom = dynamic_cast<ThumbZoomLabel*>(row.match_thumb)) {
                zoom->setZoomPixmap(pm);
            }
        } else {
            fitThumbLabel(row.match_thumb, {}, min_w, min_h, QString::fromUtf8("없음"));
            if (auto* zoom = dynamic_cast<ThumbZoomLabel*>(row.match_thumb)) {
                zoom->setZoomPixmap({});
            }
        }
    }
}

}  // namespace pipela::app::widgets
