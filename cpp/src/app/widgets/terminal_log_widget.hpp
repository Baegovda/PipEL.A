#pragma once

#include <QVector>
#include <QWidget>

class QPlainTextEdit;
class QScrollBar;

namespace pipela::ui::widgets {

struct TerminalLogDisplayEntry {
    double wall_t{0.0};
    double mono_t{0.0};
    QString body;
};

// AGENT: Conventional read-only console log (QPlainTextEdit append + auto-scroll).
class TerminalLogWidget : public QWidget {
    Q_OBJECT
public:
    explicit TerminalLogWidget(QWidget* parent = nullptr);

    void appendLine(const QString& body, double wall_t = -1.0, double mono_t = -1.0);
    void setLines(const QVector<TerminalLogDisplayEntry>& lines, bool stick_to_bottom);
    void clearLog();
    void refreshTimePrefixes();
    void setMaxVisibleLines(int max_lines);

    QScrollBar* verticalScrollBarProxy() const;

signals:
    void userScrollGesture();

private:
    struct StoredLine {
        double wall_t{0.0};
        double mono_t{0.0};
        QString body;
    };

    void rebuildDocument(bool stick_to_bottom);
    bool atBottom() const;
    void notifyUserScrolled();
    void scrollToBottom();

    QPlainTextEdit* view_{nullptr};
    QVector<StoredLine> lines_;
    int max_blocks_{2000};
    bool user_pinned_up_{false};
};

}  // namespace pipela::ui::widgets
