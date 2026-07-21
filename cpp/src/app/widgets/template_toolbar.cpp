#include "widgets/template_toolbar.hpp"

#include <cmath>
#include <chrono>

#include <QFontMetrics>
#include <QHBoxLayout>
#include <QPainter>
#include <QPushButton>
#include <QTimer>
#include <QVBoxLayout>

#include "theme/ui_adaptive.hpp"
#include "widgets/settings_chrome.hpp"

namespace pipela::app::widgets {

namespace {

enum class ToolbarRole { Capture, Test, Preview, Region, Clear };

struct RoleStyle {
    const char* normal;
    const char* hover;
};

RoleStyle roleStyle(ToolbarRole role) {
    switch (role) {
        case ToolbarRole::Capture:
            return {"#2d6a4f", "#357a5c"};
        case ToolbarRole::Test:
            return {"#3d5a80", "#4a6a94"};
        case ToolbarRole::Preview:
            return {"#4a4e69", "#565a78"};
        case ToolbarRole::Region:
            return {"#6b4e71", "#7a5c80"};
        case ToolbarRole::Clear:
            return {"#5c4a4a", "#6b5858"};
    }
    return {"#3d5a80", "#4a6a94"};
}

QString panelTemplateToolbarButtonQss(ToolbarRole role, int font_pt, int pad_v, int pad_h) {
    const auto st = roleStyle(role);
    return QString::fromUtf8(
               "QPushButton { background: %1; color: #e8eaef; border: none; border-radius: 4px; "
               "padding: %2px %3px; font-size: %4pt; font-weight: 600; text-align: center; }"
               "QPushButton:hover { background: %5; }")
        .arg(QString::fromUtf8(st.normal))
        .arg(pad_v)
        .arg(pad_h)
        .arg(font_pt);
}

int templateToolbarMinMeasurePx() {
    return std::max(96, pipela::ui::theme::scalePxH(140, 420));
}

void fitQPushButtonTextWidth(QPushButton* btn, int min_measure_width_px, int pad_h, int pad_v,
                             double base_design_pt, double min_design_pt) {
    if (btn == nullptr) {
        return;
    }
    QFont font = btn->font();
    font.setWeight(QFont::DemiBold);
    double pt = base_design_pt;
    const QString text = btn->text();
    const int budget = std::max(min_measure_width_px, pad_h * 2 + 24);
    for (int i = 0; i < 24; ++i) {
        font.setPointSizeF(pt);
        btn->setFont(font);
        const QFontMetrics fm(font);
        const int w = fm.horizontalAdvance(text) + pad_h * 2;
        if (w <= budget || pt <= min_design_pt) {
            break;
        }
        pt -= 0.35;
    }
    btn->setMinimumWidth(std::min(budget, btn->fontMetrics().horizontalAdvance(text) + pad_h * 2));
}

class ShimmerPushButton : public QPushButton {
public:
    ShimmerPushButton(const QString& text, ToolbarRole role, QWidget* parent = nullptr)
        : QPushButton(text, parent), role_(role) {
        setCursor(Qt::PointingHandCursor);
        timer_ = new QTimer(this);
        timer_->setInterval(66);
        connect(timer_, &QTimer::timeout, this, [this]() { update(); });
    }

    void triggerShimmer() {
        shimmer_active_ = true;
        shimmer_t0_ = std::chrono::steady_clock::now();
        if (!timer_->isActive()) {
            timer_->start();
        }
        update();
    }

    void applyFitStyle() {
        const int ph = pipela::ui::theme::scalePxH(10, 420);
        const int pv = pipela::ui::theme::scalePxV(6, 720);
        fitQPushButtonTextWidth(this, templateToolbarMinMeasurePx(), ph, pv, 9.0, 3.8);
        const int pt = font().pointSize() > 0 ? font().pointSize() : 9;
        setStyleSheet(panelTemplateToolbarButtonQss(role_, pt, pv, ph));
    }

protected:
    void paintEvent(QPaintEvent* event) override {
        QPushButton::paintEvent(event);
        if (!shimmer_active_) {
            return;
        }
        const auto now = std::chrono::steady_clock::now();
        const double elapsed =
            std::chrono::duration<double>(now - shimmer_t0_).count();
        if (elapsed > 1.05) {
            shimmer_active_ = false;
            if (role_ != ToolbarRole::Test) {
                timer_->stop();
            }
            return;
        }
        QPainter p(this);
        p.setRenderHint(QPainter::Antialiasing, true);
        const QRect r = rect().adjusted(2, 2, -2, -2);
        const double phase = std::fmod(elapsed * 2.4, 1.0);
        const double alpha = 0.18 * (0.5 + 0.5 * std::sin(phase * 3.141592653589793 * 2.0));
        p.fillRect(r, QColor(255, 255, 255, static_cast<int>(alpha * 255)));
    }

private:
    ToolbarRole role_;
    QTimer* timer_{nullptr};
    bool shimmer_active_{false};
    std::chrono::steady_clock::time_point shimmer_t0_{};
};

QPushButton* makeToolButton(const QString& text, ToolbarRole role, QWidget* parent) {
    auto* btn = new ShimmerPushButton(text, role, parent);
    btn->applyFitStyle();
    return btn;
}

}  // namespace

void addTemplateToolbar(QVBoxLayout* layout, const QString& capture_kind,
                        const TemplateToolbarCallbacks& callbacks) {
    if (layout == nullptr) {
        return;
    }
    auto emit_log = [&](const QString& msg) {
        if (callbacks.log) {
            callbacks.log(msg);
        }
    };

    auto* row1 = new QHBoxLayout();
    row1->setSpacing(pipela::ui::theme::scalePxH(8, 420));
    auto* row2 = new QHBoxLayout();
    row2->setSpacing(pipela::ui::theme::scalePxH(8, 420));

    QWidget* host = layout->parentWidget();
    auto* cap = makeToolButton(QString::fromUtf8("캡처"), ToolbarRole::Capture, host);
    auto* test = dynamic_cast<ShimmerPushButton*>(
        makeToolButton(QString::fromUtf8("테스트"), ToolbarRole::Test, host));
    auto* prev = makeToolButton(QString::fromUtf8("미리보기"), ToolbarRole::Preview, host);
    auto* reg = makeToolButton(QString::fromUtf8("영역 선택"), ToolbarRole::Region, host);
    auto* clr = makeToolButton(QString::fromUtf8("해제"), ToolbarRole::Clear, host);

    QObject::connect(cap, &QPushButton::clicked, host, [callbacks, emit_log, capture_kind]() {
        if (callbacks.on_capture) {
            callbacks.on_capture();
        } else {
            emit_log(QString::fromUtf8("[%1] 캡처 미연결").arg(capture_kind));
        }
    });
    QObject::connect(test, &QPushButton::clicked, host, [callbacks, emit_log, capture_kind, test]() {
        if (test != nullptr) {
            test->triggerShimmer();
        }
        if (callbacks.on_test) {
            callbacks.on_test();
        } else {
            emit_log(QString::fromUtf8("[%1] 테스트 미연결").arg(capture_kind));
        }
    });
    QObject::connect(prev, &QPushButton::clicked, host, [callbacks, emit_log, capture_kind]() {
        if (callbacks.on_preview) {
            callbacks.on_preview();
        } else {
            emit_log(QString::fromUtf8("[%1] 미리보기 미연결").arg(capture_kind));
        }
    });
    QObject::connect(reg, &QPushButton::clicked, host, [callbacks, emit_log, capture_kind]() {
        if (callbacks.on_region) {
            callbacks.on_region();
        } else {
            emit_log(QString::fromUtf8("[%1] 영역 선택 미연결").arg(capture_kind));
        }
    });
    QObject::connect(clr, &QPushButton::clicked, host, [callbacks, emit_log, capture_kind]() {
        if (callbacks.on_clear) {
            callbacks.on_clear();
        } else {
            emit_log(QString::fromUtf8("[%1] 해제 미연결").arg(capture_kind));
        }
    });

    row1->addWidget(cap);
    row1->addWidget(test);
    row2->addWidget(prev);
    row2->addWidget(reg);
    row2->addWidget(clr);

    auto* col = new QVBoxLayout();
    col->setSpacing(pipela::ui::theme::scalePxV(8, 720));
    col->addLayout(row1);
    col->addLayout(row2);
    addSettingsCenteredLayout(layout, col);
}

}  // namespace pipela::app::widgets
