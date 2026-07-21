#include "widgets/terminal_log_widget.hpp"

#include <algorithm>
#include <chrono>

#include <QAbstractSlider>
#include <QFont>
#include <QFontDatabase>
#include <QFrame>
#include <QPlainTextEdit>
#include <QScrollBar>
#include <QTextCursor>
#include <QTextOption>
#include <QVBoxLayout>

#include "theme/theme_engine.hpp"
#include "widgets/terminal_log_html.hpp"

namespace pipela::ui::widgets {

namespace {

double nowWallSec() {
    using clock = std::chrono::system_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

double nowMonoSec() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

double lineAgeSec(double wall_t, double mono_t) {
    if (consoleLogTimeDisplayRelative()) {
        return std::max(0.0, nowMonoSec() - mono_t);
    }
    return std::max(0.0, nowWallSec() - wall_t);
}

QFont consoleLogFont() {
    static const char* kFamilies[] = {"Cascadia Mono", "Consolas", "D2Coding", "Malgun Gothic",
                                      "Segoe UI"};
    QFont font;
    for (const char* family : kFamilies) {
        if (QFontDatabase::hasFamily(QString::fromUtf8(family))) {
            font.setFamily(QString::fromUtf8(family));
            break;
        }
    }
    font.setPointSize(10);
    font.setStyleHint(QFont::Monospace);
    return font;
}

}  // namespace

TerminalLogWidget::TerminalLogWidget(QWidget* parent) : QWidget(parent) {
    auto* outer = new QVBoxLayout(this);
    outer->setContentsMargins(0, 0, 0, 0);

    view_ = new QPlainTextEdit(this);
    view_->setReadOnly(true);
    view_->setUndoRedoEnabled(false);
    view_->setLineWrapMode(QPlainTextEdit::WidgetWidth);
    view_->setFrameShape(QFrame::NoFrame);
    view_->setFont(consoleLogFont());
    view_->setMaximumBlockCount(max_blocks_);
    QTextOption text_opt = view_->document()->defaultTextOption();
    text_opt.setAlignment(Qt::AlignLeft | Qt::AlignVCenter);
    view_->document()->setDefaultTextOption(text_opt);
    view_->setStyleSheet(pipela::ui::theme::terminalViewQss());

    if (auto* bar = view_->verticalScrollBar()) {
        connect(bar, &QScrollBar::valueChanged, this, [this](int value) {
            Q_UNUSED(value);
            if (view_ == nullptr) {
                return;
            }
            const bool bottom = atBottom();
            if (!bottom) {
                user_pinned_up_ = true;
                emit userScrollGesture();
            } else if (user_pinned_up_) {
                user_pinned_up_ = false;
            }
        });
        connect(bar, &QScrollBar::sliderMoved, this, [this]() { notifyUserScrolled(); });
        connect(bar, &QScrollBar::actionTriggered, this, [this](int action) {
            if (action == QAbstractSlider::SliderSingleStepAdd ||
                action == QAbstractSlider::SliderSingleStepSub ||
                action == QAbstractSlider::SliderPageStepAdd ||
                action == QAbstractSlider::SliderPageStepSub) {
                notifyUserScrolled();
            }
        });
    }

    outer->addWidget(view_);
}

void TerminalLogWidget::setMaxVisibleLines(int max_lines) {
    max_blocks_ = std::max(32, max_lines);
    if (view_ != nullptr) {
        view_->setMaximumBlockCount(max_blocks_);
    }
}

QScrollBar* TerminalLogWidget::verticalScrollBarProxy() const {
    return view_ != nullptr ? view_->verticalScrollBar() : nullptr;
}

bool TerminalLogWidget::atBottom() const {
    if (view_ == nullptr || view_->verticalScrollBar() == nullptr) {
        return true;
    }
    const auto* bar = view_->verticalScrollBar();
    return bar->maximum() <= 0 || bar->value() >= bar->maximum() - 2;
}

void TerminalLogWidget::notifyUserScrolled() {
    if (!atBottom()) {
        user_pinned_up_ = true;
        emit userScrollGesture();
    }
}

void TerminalLogWidget::scrollToBottom() {
    if (view_ == nullptr || view_->verticalScrollBar() == nullptr) {
        return;
    }
    view_->verticalScrollBar()->setValue(view_->verticalScrollBar()->maximum());
    user_pinned_up_ = false;
}

void TerminalLogWidget::rebuildDocument(bool stick_to_bottom) {
    if (view_ == nullptr) {
        return;
    }
    const int saved = view_->verticalScrollBar() != nullptr ? view_->verticalScrollBar()->value() : 0;
    const bool was_bottom = atBottom();

    view_->clear();
    QTextCursor cursor(view_->document());
    for (int i = 0; i < lines_.size(); ++i) {
        if (i > 0) {
            cursor.insertBlock();
        }
        const StoredLine& line = lines_[i];
        const QString prefix = formatTerminalTimePrefix(line.wall_t, line.mono_t);
        appendTerminalLogLine(cursor, prefix, line.body, lineAgeSec(line.wall_t, line.mono_t));
    }

    if (stick_to_bottom || was_bottom || !user_pinned_up_) {
        scrollToBottom();
    } else if (view_->verticalScrollBar() != nullptr) {
        view_->verticalScrollBar()->setValue(std::min(saved, view_->verticalScrollBar()->maximum()));
    }
}

void TerminalLogWidget::appendLine(const QString& body, double wall_t, double mono_t) {
    const double ts = wall_t >= 0.0 ? wall_t : nowWallSec();
    const double mono = mono_t >= 0.0 ? mono_t : nowMonoSec();
    lines_.push_back(StoredLine{ts, mono, body});
    while (lines_.size() > max_blocks_) {
        lines_.removeFirst();
    }

    if (view_ == nullptr) {
        return;
    }

    const bool stick = !user_pinned_up_;
    QTextCursor cursor(view_->document());
    cursor.movePosition(QTextCursor::End);
    if (!view_->document()->isEmpty()) {
        cursor.insertBlock();
    }
    const QString prefix = formatTerminalTimePrefix(ts, mono);
    appendTerminalLogLine(cursor, prefix, body, lineAgeSec(ts, mono));

    if (stick) {
        scrollToBottom();
    }
}

void TerminalLogWidget::setLines(const QVector<TerminalLogDisplayEntry>& entries,
                                 bool stick_to_bottom) {
    lines_.clear();
    lines_.reserve(entries.size());
    for (const auto& entry : entries) {
        lines_.push_back(StoredLine{entry.wall_t, entry.mono_t, entry.body});
    }
    rebuildDocument(stick_to_bottom);
}

void TerminalLogWidget::clearLog() {
    lines_.clear();
    if (view_ != nullptr) {
        view_->clear();
    }
    user_pinned_up_ = false;
}

void TerminalLogWidget::refreshTimePrefixes() {
    if (lines_.isEmpty()) {
        return;
    }
    rebuildDocument(!user_pinned_up_);
}

}  // namespace pipela::ui::widgets
