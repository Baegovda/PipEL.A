#pragma once

#include <QString>

class QTextCursor;

namespace pipela::ui::widgets {

bool consoleLogTimeDisplayRelative();
QString formatTerminalTimePrefix(double wall_t, double mono_t);
QString terminalTimeColorForAge(double age_sec);

// AGENT: Append one log line to a QTextDocument (monospace console style — no per-row widgets).
void appendTerminalLogLine(QTextCursor& cursor, const QString& time_prefix, const QString& raw_line,
                           double time_age_sec);

}  // namespace pipela::ui::widgets
