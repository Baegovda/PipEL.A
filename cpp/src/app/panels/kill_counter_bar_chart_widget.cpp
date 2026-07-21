#include "panels/kill_counter_bar_chart_widget.hpp"

#include <algorithm>

#include <cmath>

#include <QButtonGroup>
#include <QHBoxLayout>
#include <QLabel>
#include <QLinearGradient>
#include <QMouseEvent>
#include <QPainter>
#include <QPainterPath>
#include <QPen>
#include <QPushButton>
#include <QResizeEvent>
#include <QTimer>
#include <QToolTip>
#include <QVBoxLayout>
#include <QWheelEvent>

#include "pipela/core/kill_counter/stats_store.hpp"

namespace pipela::ui::panels {

namespace {

constexpr int kMaxVisibleBars = 24;

struct BucketSpec {
    int minutes;
    const char* label;
};

constexpr BucketSpec kBucketSpecs[] = {
    {5, "5분"},
    {30, "30분"},
    {60, "1시간"},
    {360, "6시간"},
    {720, "12시간"},
};

constexpr QColor kAccentColor(61, 212, 201);

void paintZeroKillBar(QPainter& p, double x, int plot_bottom, int w, int h, bool is_hover) {
    const double hs = is_hover ? 1.0 : 0.0;
    const double pad = 1.0 + 1.25 * hs;
    const double xo = x - pad * 0.5;
    const double wo = std::max(2.0, static_cast<double>(w) + pad * 2.0);
    const double ho = std::max(3.0, static_cast<double>(h) + 5.0 * hs);
    const double yo = static_cast<double>(plot_bottom) - ho;
    const int fill_a = static_cast<int>(72 + 100 * hs);
    const int edge_a = static_cast<int>(165 + 75 * hs);
    const double rz = std::max(1.5, std::min({5.0, wo * 0.38, ho * 0.5}));
    const QRectF rr(xo, yo, wo, ho);
    p.setPen(Qt::NoPen);
    p.setBrush(QColor(kAccentColor.red(), kAccentColor.green(), kAccentColor.blue(),
                      std::min(255, fill_a)));
    p.drawRoundedRect(rr, rz, rz);
    p.setBrush(Qt::NoBrush);
    p.setPen(QPen(QColor(kAccentColor.red(), kAccentColor.green(), kAccentColor.blue(),
                         std::min(255, edge_a)),
                  std::max(1.25, 1.35 + 0.65 * hs)));
    p.drawRoundedRect(rr, rz, rz);
}

void paintGlassBar(QPainter& p, double x, double y, int w, int h, bool is_hover, double shimmer,
                   double pulse) {
    const double hs = is_hover ? 1.0 : 0.0;
    const double pad = 2.0 * hs;
    const double lift = 5.0 * hs;
    const double xo = x - pad * 0.5;
    const double wo = std::max(2.0, static_cast<double>(w) + pad);
    const double ho = std::max(2.0, static_cast<double>(h) + lift);
    const double yo = y - lift;
    const double r = std::max(1.0, std::min({4.0, wo / 2.0, ho / 3.0}));
    QColor col = kAccentColor;
    if (pulse > 0.001) {
        const double t = 0.13 * pulse;
        col = QColor(std::min(255, static_cast<int>(col.red() + (255 - col.red()) * t)),
                     std::min(255, static_cast<int>(col.green() + (255 - col.green()) * t)),
                     std::min(255, static_cast<int>(col.blue() + (255 - col.blue()) * t)));
    }
    const QColor top_c(std::min(255, col.red() + 26), std::min(255, col.green() + 30),
                       std::min(255, col.blue() + 24));
    const QColor mid_c = col;
    const QColor bot_c(std::max(0, col.red() - 20), std::max(0, col.green() - 22),
                       std::max(0, col.blue() - 18));
    QPainterPath path;
    path.addRoundedRect(xo, yo, wo, ho, r, r);
    QLinearGradient body(xo, yo, xo, yo + ho);
    body.setColorAt(0.0, top_c);
    body.setColorAt(0.48, mid_c);
    body.setColorAt(1.0, bot_c);
    p.fillPath(path, body);
    const double sh = 0.5 + 0.5 * std::sin(shimmer);
    const int ga = static_cast<int>(30 + 42 * sh);
    QLinearGradient gloss(xo, yo, xo, yo + ho * 0.58);
    gloss.setColorAt(0.0, QColor(255, 255, 255, std::min(130, ga)));
    gloss.setColorAt(0.32, QColor(255, 255, 255, static_cast<int>(16 + 22 * sh)));
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0));
    p.fillPath(path, gloss);
    const int rim = static_cast<int>(52 + 130 * hs);
    p.setPen(QPen(QColor(255, 255, 255, std::min(200, rim)), std::max(1.0, 1.0 + 0.8 * hs)));
    p.setBrush(Qt::NoBrush);
    p.drawPath(path);
}

void paintReloadMarker(QPainter& p, double cx, double bar_top, int bw) {
    const double wbar = std::max(1.0, static_cast<double>(bw));
    const double h_tri = std::max(3.0, std::min(6.0, wbar * 0.9));
    const double half_w = std::max(3.0, std::min(wbar * 0.4, h_tri * 0.75));
    QPainterPath path;
    path.moveTo(cx, bar_top);
    path.lineTo(cx - half_w, bar_top - h_tri);
    path.lineTo(cx + half_w, bar_top - h_tri);
    path.closeSubpath();
    p.setPen(Qt::NoPen);
    p.setBrush(QColor(239, 68, 68, 255));
    p.drawPath(path);
    p.setBrush(Qt::NoBrush);
    p.setPen(QPen(QColor(120, 23, 31, 228), 0.8));
    p.drawPath(path);
}

class ZoomLabel : public QLabel {
public:
    explicit ZoomLabel(KillCounterBarChartWidget* owner) : owner_(owner) {
        setAlignment(Qt::AlignCenter);
        setStyleSheet(
            "color: #9aa8a0; background: rgba(12,16,20,180); border: 1px solid #2a3438;"
            "border-radius: 4px; padding: 1px 4px; font-size: 9px;");
        setCursor(Qt::SizeHorCursor);
    }

    void refreshText() {
        if (owner_ == nullptr) {
            return;
        }
        const int pct = static_cast<int>(std::lround(owner_->xScale() * 100.0));
        setText(QString::fromUtf8("%1%").arg(pct));
        adjustSize();
    }

protected:
    void mousePressEvent(QMouseEvent* event) override {
        if (event->button() == Qt::LeftButton) {
            drag_ = true;
            drag_x0_ = event->globalPosition().x();
            scale0_ = owner_ != nullptr ? owner_->xScale() : 1.0;
            event->accept();
            return;
        }
        QLabel::mousePressEvent(event);
    }

    void mouseMoveEvent(QMouseEvent* event) override {
        if (drag_ && owner_ != nullptr) {
            const double dx = event->globalPosition().x() - drag_x0_;
            const double next = scale0_ * std::exp(0.002 * dx);
            owner_->setXScale(next);
            refreshText();
            event->accept();
            return;
        }
        QLabel::mouseMoveEvent(event);
    }

    void mouseReleaseEvent(QMouseEvent* event) override {
        if (drag_ && event->button() == Qt::LeftButton) {
            drag_ = false;
            event->accept();
            return;
        }
        QLabel::mouseReleaseEvent(event);
    }

private:
    KillCounterBarChartWidget* owner_{nullptr};
    bool drag_{false};
    double drag_x0_{0.0};
    double scale0_{1.0};
};

class RangeIndicator : public QWidget {
public:
    explicit RangeIndicator(KillCounterBarChartWidget* owner) : owner_(owner) {
        setFixedHeight(6);
    }

protected:
    void paintEvent(QPaintEvent* event) override {
        Q_UNUSED(event);
        if (owner_ == nullptr) {
            return;
        }
        const int n_total = static_cast<int>(owner_->bucketsForPaint().size());
        if (n_total <= 0) {
            return;
        }
        const int n_vis = owner_->visibleBarCount(n_total);
        const int start = owner_->panOffset();
        QPainter p(this);
        p.setRenderHint(QPainter::Antialiasing, true);
        const int w = width();
        const int h = height();
        p.setPen(Qt::NoPen);
        p.setBrush(QColor(42, 52, 56));
        p.drawRoundedRect(0, 0, w, h, 3, 3);
        if (n_total <= n_vis) {
            return;
        }
        const double thumb_w = std::max(8.0, static_cast<double>(w) * static_cast<double>(n_vis) /
                                                    static_cast<double>(n_total));
        const double span = static_cast<double>(w) - thumb_w;
        const double ratio =
            static_cast<double>(start) / static_cast<double>(std::max(1, n_total - n_vis));
        const int tx = static_cast<int>(ratio * span);
        p.setBrush(QColor(61, 212, 201, 140));
        p.drawRoundedRect(tx, 0, static_cast<int>(thumb_w), h, 3, 3);
    }

private:
    KillCounterBarChartWidget* owner_{nullptr};
};

class ChartCanvas : public QWidget {
public:
    explicit ChartCanvas(KillCounterBarChartWidget* owner, ZoomLabel* zoom_label,
                         RangeIndicator* range_indicator)
        : owner_(owner), zoom_label_(zoom_label), range_indicator_(range_indicator) {
        setMinimumHeight(56);
        setMouseTracking(true);
        setFocusPolicy(Qt::WheelFocus);
        shimmer_timer_ = new QTimer(this);
        shimmer_timer_->setInterval(50);
        connect(shimmer_timer_, &QTimer::timeout, this, [this]() {
            shimmer_phase_ += 0.13;
            if (shimmer_phase_ > 6.283185307) {
                shimmer_phase_ -= 6.283185307;
            }
            update();
        });
        shimmer_timer_->start();
    }

protected:
    void paintEvent(QPaintEvent* event) override {
        Q_UNUSED(event);
        if (owner_ == nullptr) {
            return;
        }
        const auto& buckets = owner_->bucketsForPaint();
        const int hover = owner_->hoverIndex();
        const int pan = owner_->panOffset();
        QPainter p(this);
        p.setRenderHint(QPainter::Antialiasing, true);
        p.fillRect(rect(), QColor(24, 30, 36));
        if (buckets.empty()) {
            p.setPen(QColor(120, 130, 125));
            p.drawText(rect(), Qt::AlignCenter, QString::fromUtf8("그래프 데이터 없음"));
            return;
        }
        const int n_total = static_cast<int>(buckets.size());
        const int n_vis = owner_->visibleBarCount(n_total);
        const int start = std::clamp(pan, 0, std::max(0, n_total - n_vis));
        const int max_k = std::max(1, *std::max_element(buckets.begin(), buckets.end()));
        const double bar_w = static_cast<double>(width()) / static_cast<double>(n_vis);
        const int plot_h = height() - 16;
        const int baseline = height() - 10;
        p.setPen(QColor(50, 58, 62));
        p.drawLine(0, baseline, width(), baseline);
        for (int vi = 0; vi < n_vis; ++vi) {
            const int i = start + vi;
            const int kills = buckets[static_cast<size_t>(i)];
            const int min_h = kills > 0 ? 3 : 2;
            const int h = std::max(min_h,
                                   static_cast<int>((static_cast<double>(kills) / max_k) * plot_h));
            const int x = static_cast<int>(vi * bar_w);
            const int w = std::max(1, static_cast<int>(bar_w) - 1);
            const bool hover_bar = hover == i;
            if (kills <= 0) {
                paintZeroKillBar(p, static_cast<double>(x + 1), baseline, w, h, hover_bar);
            } else {
                const double reload_pulse =
                    owner_->bucketReloadMark(i)
                        ? 0.35 + 0.35 * std::sin(shimmer_phase_ + static_cast<double>(i))
                        : 0.0;
                paintGlassBar(p, static_cast<double>(x + 1), static_cast<double>(baseline - h), w,
                              h, hover_bar, shimmer_phase_, reload_pulse);
            }
            if (owner_->bucketReloadMark(i)) {
                paintReloadMarker(p, static_cast<double>(x + 1) + w * 0.5,
                                  static_cast<double>(baseline - h), w);
            }
            if (hover_bar) {
                const int delta = owner_->barDelta(i);
                if (delta != 0) {
                    const QString delta_txt =
                        QString::fromUtf8("%1%2")
                            .arg(delta > 0 ? "+" : "")
                            .arg(delta);
                    p.setPen(delta > 0 ? QColor(140, 255, 230) : QColor(255, 160, 140));
                    p.drawText(QRect(x, baseline - h - 14, w + 4, 12),
                               Qt::AlignHCenter | Qt::AlignBottom, delta_txt);
                }
            }
            if (vi == 0 || vi == n_vis - 1 || (n_vis > 8 && vi % (n_vis / 4) == 0)) {
                const std::string tr = pipela::core::kill_counter::formatTodayBucketTimeRange(
                    i, owner_->bucketMinutes());
                if (!tr.empty() && bar_w >= 18.0) {
                    p.setPen(QColor(90, 100, 95));
                    p.drawText(QRect(x, baseline + 1, w + 4, 10), Qt::AlignHCenter | Qt::AlignTop,
                               QString::fromStdString(tr.substr(0, 5)));
                }
            }
        }
        if (n_total > n_vis) {
            p.setPen(QColor(100, 110, 105));
            p.drawText(rect().adjusted(4, 2, -4, 0), Qt::AlignTop | Qt::AlignRight,
                       QString::fromUtf8("%1-%2 / %3")
                           .arg(start + 1)
                           .arg(start + n_vis)
                           .arg(n_total));
        }
        if (zoom_label_ != nullptr) {
            zoom_label_->move(width() - zoom_label_->width() - 4, 4);
            zoom_label_->raise();
        }
        if (range_indicator_ != nullptr) {
            range_indicator_->update();
        }
    }

    void resizeEvent(QResizeEvent* event) override {
        QWidget::resizeEvent(event);
        if (zoom_label_ != nullptr) {
            zoom_label_->move(width() - zoom_label_->width() - 4, 4);
        }
    }

    void mouseMoveEvent(QMouseEvent* event) override {
        if (owner_ == nullptr) {
            return;
        }
        const auto& buckets = owner_->bucketsForPaint();
        if (buckets.empty()) {
            return;
        }
        const int n_total = static_cast<int>(buckets.size());
        const int n_vis = owner_->visibleBarCount(n_total);
        const int start = owner_->panOffset();
        const double bar_w = static_cast<double>(width()) / static_cast<double>(n_vis);
        const int vi = static_cast<int>(event->position().x() / bar_w);
        const int idx = start + std::clamp(vi, 0, n_vis - 1);
        const int clamped = std::clamp(idx, 0, n_total - 1);
        owner_->setHoverIndex(clamped);
        const QString tip = owner_->hoverTooltipText(clamped);
        if (!tip.isEmpty()) {
            QToolTip::showText(event->globalPosition().toPoint(), tip, this);
        }
    }

    void mouseDoubleClickEvent(QMouseEvent* event) override {
        if (owner_ != nullptr) {
            owner_->setXScale(1.0);
            owner_->setUserPanned(false);
            owner_->followTailIfNeeded();
            if (zoom_label_ != nullptr) {
                zoom_label_->refreshText();
            }
            update();
            event->accept();
            return;
        }
        QWidget::mouseDoubleClickEvent(event);
    }

    void wheelEvent(QWheelEvent* event) override {
        if (owner_ == nullptr) {
            return;
        }
        const int delta = event->angleDelta().y();
        if (event->modifiers() & Qt::ControlModifier) {
            const double factor = delta > 0 ? 1.08 : 0.92;
            owner_->setXScale(owner_->xScale() * factor);
            if (zoom_label_ != nullptr) {
                zoom_label_->refreshText();
            }
            event->accept();
            return;
        }
        owner_->setUserPanned(true);
        owner_->touchUserPan();
        if (delta > 0) {
            owner_->setPanOffset(owner_->panOffset() - 1);
        } else if (delta < 0) {
            owner_->setPanOffset(owner_->panOffset() + 1);
        }
        event->accept();
    }

    void leaveEvent(QEvent* event) override {
        Q_UNUSED(event);
        if (owner_ != nullptr) {
            owner_->setHoverIndex(-1);
        }
        QToolTip::hideText();
    }

private:
    KillCounterBarChartWidget* owner_{nullptr};
    ZoomLabel* zoom_label_{nullptr};
    RangeIndicator* range_indicator_{nullptr};
    QTimer* shimmer_timer_{nullptr};
    double shimmer_phase_{0.0};
};

}  // namespace

KillCounterBarChartWidget::KillCounterBarChartWidget(QWidget* parent) : QWidget(parent) {
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(4);

    auto* bucket_row = new QHBoxLayout();
    bucket_row->setSpacing(4);
    bucket_group_ = new QButtonGroup(this);
    bucket_group_->setExclusive(true);
    const QString bucket_qss =
        QString::fromUtf8(
            "QPushButton { background: #1e262c; color: #8a9a92; border: 1px solid #2a3438; "
            "border-radius: 4px; padding: 3px 2px; font-size: 9px; text-align: center; }"
            "QPushButton:checked { background: #243830; color: #3dd4c9; border-color: #3a5a52; }"
            "QPushButton:hover { color: #c8d8d0; }");
    for (const BucketSpec& spec : kBucketSpecs) {
        auto* btn = new QPushButton(QString::fromUtf8(spec.label), this);
        btn->setCheckable(true);
        btn->setStyleSheet(bucket_qss);
        btn->setProperty("bucket_minutes", spec.minutes);
        btn->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
        bucket_group_->addButton(btn);
        bucket_row->addWidget(btn, 1);
        if (spec.minutes == 30) {
            btn->setChecked(true);
        }
        connect(btn, &QPushButton::toggled, this, [this, btn](bool on) {
            if (!on) {
                return;
            }
            bucket_minutes_ = btn->property("bucket_minutes").toInt();
            refresh();
        });
    }
    layout->addLayout(bucket_row);

    auto* range = new RangeIndicator(this);
    range_indicator_ = range;
    layout->addWidget(range);

    auto* zoom_label = new ZoomLabel(this);
    chart_host_ = new ChartCanvas(this, zoom_label, range);
    zoom_label->setParent(chart_host_);
    zoom_label->refreshText();
    layout->addWidget(chart_host_, 1);

    pan_idle_timer_ = new QTimer(this);
    pan_idle_timer_->setInterval(400);
    connect(pan_idle_timer_, &QTimer::timeout, this, [this]() {
        if (!user_panned_ || bucket_entries_.empty()) {
            return;
        }
        const auto now = std::chrono::steady_clock::now();
        if (last_user_pan_mono_.time_since_epoch().count() == 0) {
            return;
        }
        if (std::chrono::duration<double>(now - last_user_pan_mono_).count() < 30.0) {
            return;
        }
        user_panned_ = false;
        followTailIfNeeded();
        if (chart_host_ != nullptr) {
            chart_host_->update();
        }
    });
    pan_idle_timer_->start();

    refresh();
}

void KillCounterBarChartWidget::refresh() {
    bucket_entries_ = pipela::core::kill_counter::statsTodayBucketEntries(bucket_minutes_);
    pan_offset_ = 0;
    x_scale_ = 1.0;
    user_panned_ = false;
    if (chart_host_ != nullptr) {
        chart_host_->update();
    }
    if (range_indicator_ != nullptr) {
        range_indicator_->update();
    }
    followTailIfNeeded();
}

const std::vector<int>& KillCounterBarChartWidget::bucketsForPaint() const {
    static thread_local std::vector<int> kills_cache;
    kills_cache.clear();
    kills_cache.reserve(bucket_entries_.size());
    for (const auto& e : bucket_entries_) {
        kills_cache.push_back(e.kills);
    }
    return kills_cache;
}

int KillCounterBarChartWidget::bucketMinutes() const { return bucket_minutes_; }

int KillCounterBarChartWidget::hoverIndex() const { return hover_index_; }

int KillCounterBarChartWidget::panOffset() const { return pan_offset_; }

QString KillCounterBarChartWidget::hoverTooltipText(int bucket_index) const {
    if (bucket_index < 0 || bucket_index >= static_cast<int>(bucket_entries_.size())) {
        return {};
    }
    const int kills = bucket_entries_[static_cast<size_t>(bucket_index)].kills;
    const std::string range =
        pipela::core::kill_counter::formatTodayBucketTimeRange(bucket_index, bucket_minutes_);
    const int delta = barDelta(bucket_index);
    QString base;
    if (range.empty()) {
        base = QString::fromUtf8("%1 킬").arg(kills);
    } else {
        base = QString::fromUtf8("%1 · %2 킬")
                   .arg(QString::fromStdString(range))
                   .arg(kills);
    }
    if (delta != 0) {
        base += QString::fromUtf8(" (%1%2)")
                    .arg(delta > 0 ? "+" : "")
                    .arg(delta);
    }
    return base;
}

int KillCounterBarChartWidget::barDelta(int bucket_index) const {
    if (bucket_index <= 0 || bucket_index >= static_cast<int>(bucket_entries_.size())) {
        return 0;
    }
    return bucket_entries_[static_cast<size_t>(bucket_index)].kills -
           bucket_entries_[static_cast<size_t>(bucket_index - 1)].kills;
}

bool KillCounterBarChartWidget::bucketReloadMark(int bucket_index) const {
    if (bucket_index < 0 || bucket_index >= static_cast<int>(bucket_entries_.size())) {
        return false;
    }
    return bucket_entries_[static_cast<size_t>(bucket_index)].reload_mark;
}

void KillCounterBarChartWidget::setPanOffset(int offset) {
    const int n_total = static_cast<int>(bucket_entries_.size());
    const int max_pan = std::max(0, n_total - visibleBarCount(n_total));
    const int next = std::clamp(offset, 0, max_pan);
    if (pan_offset_ != next) {
        pan_offset_ = next;
        if (chart_host_ != nullptr) {
            chart_host_->update();
        }
        if (range_indicator_ != nullptr) {
            range_indicator_->update();
        }
    }
}

double KillCounterBarChartWidget::xScale() const { return x_scale_; }

void KillCounterBarChartWidget::setXScale(double scale) {
    const double next = std::clamp(scale, 0.5, 3.0);
    if (std::abs(next - x_scale_) > 1e-6) {
        x_scale_ = next;
        if (chart_host_ != nullptr) {
            chart_host_->update();
        }
        if (range_indicator_ != nullptr) {
            range_indicator_->update();
        }
    }
}

int KillCounterBarChartWidget::visibleBarCount(int n_total) const {
    if (n_total <= 0) {
        return 0;
    }
    const int scaled = static_cast<int>(std::lround(static_cast<double>(kMaxVisibleBars) / x_scale_));
    return std::clamp(scaled, 6, n_total);
}

void KillCounterBarChartWidget::setUserPanned(bool panned) { user_panned_ = panned; }

void KillCounterBarChartWidget::touchUserPan() {
    last_user_pan_mono_ = std::chrono::steady_clock::now();
}

bool KillCounterBarChartWidget::userPanned() const { return user_panned_; }

void KillCounterBarChartWidget::followTailIfNeeded() {
    if (user_panned_) {
        return;
    }
    const int n_total = static_cast<int>(bucket_entries_.size());
    const int n_vis = visibleBarCount(n_total);
    const int tail = std::max(0, n_total - n_vis);
    if (pan_offset_ != tail) {
        pan_offset_ = tail;
        if (chart_host_ != nullptr) {
            chart_host_->update();
        }
        if (range_indicator_ != nullptr) {
            range_indicator_->update();
        }
    }
}

void KillCounterBarChartWidget::setHoverIndex(int idx) {
    if (hover_index_ != idx) {
        hover_index_ = idx;
        if (chart_host_ != nullptr) {
            chart_host_->update();
        }
    }
}

}  // namespace pipela::ui::panels
