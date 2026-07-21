#include "widgets/terminal_log_html.hpp"

#include <algorithm>
#include <chrono>
#include <optional>

#include <QColor>
#include <QDateTime>
#include <QFont>
#include <QRegularExpression>
#include <QTextCursor>

#include "pipela/core/registry/store.hpp"
#include "theme/theme_engine.hpp"

namespace pipela::ui::widgets {

namespace {

QColor terminalBodyFg() {
    return pipela::ui::theme::qColor("TERMINAL_FG", QColor(0xb8, 0xd4, 0xc8));
}
QColor terminalBodyMuted() {
    return pipela::ui::theme::qColor("TERMINAL_FG_MUTED", QColor(0x6a, 0x7f, 0x74));
}
QColor terminalTimeFresh() {
    return pipela::ui::theme::qColor("TERMINAL_TIME_FRESH", QColor(0x6e, 0xe7, 0xb7));
}
QColor terminalTimeMid() {
    return pipela::ui::theme::qColor("TERMINAL_TIME_MID", QColor(0x9c, 0xb8, 0xaa));
}
QColor terminalTimeOld() {
    return pipela::ui::theme::qColor("TERMINAL_TIME_OLD", QColor(0x4d, 0x5e, 0x56));
}
QColor terminalOnFg() { return pipela::ui::theme::qColor("SUCCESS", QColor(0x6e, 0xe7, 0xb7)); }
QColor terminalOffFg() { return pipela::ui::theme::qColor("DANGER", QColor(0xf0, 0x71, 0x78)); }
QColor terminalInfoFg() { return pipela::ui::theme::qColor("ACCENT", QColor(0x40, 0xe8, 0xd8)); }

double nowMonoSec() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

double nowWallSec() {
    using clock = std::chrono::system_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

QColor lerpColor(const QColor& a, const QColor& b, double t) {
    t = std::clamp(t, 0.0, 1.0);
    return QColor(static_cast<int>(a.red() + (b.red() - a.red()) * t),
                  static_cast<int>(a.green() + (b.green() - a.green()) * t),
                  static_cast<int>(a.blue() + (b.blue() - a.blue()) * t));
}

QString formatKoCoarseAgo(double dt_sec) {
    const int s = static_cast<int>(std::max(0.0, dt_sec));
    if (s < 8) {
        return QString::fromUtf8("방금");
    }
    if (s < 60) {
        return QString::fromUtf8("%1초 전").arg(s);
    }
    if (s < 3600) {
        return QString::fromUtf8("%1분 전").arg(s / 60);
    }
    if (s < 86400) {
        return QString::fromUtf8("%1시간 전").arg(s / 3600);
    }
    return QString::fromUtf8("%1일 전").arg(s / 86400);
}

struct TagVisual {
    QString display;
    QColor fg;
};

std::optional<TagVisual> tagVisualFor(const QString& tag) {
    const QString t = tag.trimmed();
    const QString tl = t.toLower();
    static const TagVisual kRows[] = {
        {QString::fromUtf8("LeftClick"), QColor(0x5e, 0xea, 0xd4)},
        {QString::fromUtf8("RightHold"), QColor(0xfb, 0xbf, 0x24)},
        {QString::fromUtf8("Flame Trigger"), QColor(0xfb, 0x92, 0x3c)},
        {QString::fromUtf8("Reload"), QColor(0x60, 0xa5, 0xfa)},
        {QString::fromUtf8("HP Refill"), QColor(0xf8, 0x71, 0x71)},
        {QString::fromUtf8("Ammo Restock"), QColor(0xa7, 0x8b, 0xfa)},
        {QString::fromUtf8("Call Merc"), QColor(0xc4, 0xb5, 0xfd)},
        {QString::fromUtf8("Ride"), QColor(0x4a, 0xde, 0x80)},
        {QString::fromUtf8("Kill Counter"), QColor(0xe8, 0x79, 0xf9)},
        {QString::fromUtf8("Start Game"), QColor(0x38, 0xbd, 0xf8)},
        {QString::fromUtf8("Pipela"), QColor(0x6e, 0xe7, 0xb7)},
        {QString::fromUtf8("설정"), QColor(0x94, 0xa3, 0xb8)},
    };
    for (const auto& row : kRows) {
        if (t == row.display) {
            return row;
        }
    }
    if (t == QString::fromUtf8("LC") || tl == QLatin1String("leftclick") ||
        t == QString::fromUtf8("좌클릭자동")) {
        return kRows[0];
    }
    if (t == QString::fromUtf8("RH") || tl == QLatin1String("righthold") ||
        t == QString::fromUtf8("우클릭홀드")) {
        return kRows[1];
    }
    if (t == QString::fromUtf8("FT") || tl.contains(QLatin1String("flame")) ||
        t == QString::fromUtf8("플레임트리거")) {
        return kRows[2];
    }
    if (t == QString::fromUtf8("Ammo") || t == QString::fromUtf8("탄약보급")) {
        return kRows[5];
    }
    if (tl.contains(QString::fromUtf8("리로드")) || tl.contains(QLatin1String("reload"))) {
        return kRows[3];
    }
    if (tl.contains(QString::fromUtf8("용병")) || tl.contains(QLatin1String("merc"))) {
        return kRows[6];
    }
    if (tl.contains(QLatin1String("ride"))) {
        return kRows[7];
    }
    if (tl.contains(QString::fromUtf8("킬")) || tl.contains(QLatin1String("kill"))) {
        return kRows[8];
    }
    if (tl.contains(QString::fromUtf8("게임")) || tl.contains(QLatin1String("start"))) {
        return kRows[9];
    }
    if (tl.contains(QString::fromUtf8("hp")) || t == QString::fromUtf8("HP회복")) {
        return kRows[4];
    }
    return std::nullopt;
}

QString registryKeyLabel(const QString& key) {
    static const std::pair<const char*, const char*> kMap[] = {
        {"left_click_feature_enabled", "LeftClick"},
        {"right_hold_feature_enabled", "RightHold"},
        {"flame_trigger_feature_enabled", "Flame Trigger"},
        {"reload_active", "Reload"},
        {"ride_feature_enabled", "Ride"},
        {"hp_refill_feature_enabled", "HP Refill"},
        {"ammo_restock_active", "Ammo Restock"},
        {"call_merc_active", "Call Merc"},
        {"kill_counter_enabled", "Kill Counter"},
        {"start_game_launcher_active", "Start Game"},
    };
    const std::string k = key.toStdString();
    for (const auto& row : kMap) {
        if (k == row.first) {
            return QString::fromUtf8(row.second);
        }
    }
    return key;
}

QString normalizeTerminalLogLine(QString raw) {
    raw = raw.trimmed();
    if (raw.isEmpty()) {
        return raw;
    }

    static const QRegularExpression kRegistry(
        QString::fromUtf8(R"(^registry\s+(\S+)\s*=\s*(ON|OFF)$)"),
        QRegularExpression::CaseInsensitiveOption);
    if (const QRegularExpressionMatch rm = kRegistry.match(raw); rm.hasMatch()) {
        const QString label = registryKeyLabel(rm.captured(1));
        const bool on = rm.captured(2).compare(QString::fromUtf8("ON"), Qt::CaseInsensitive) == 0;
        return QString::fromUtf8("[설정] %1 %2")
            .arg(label, on ? QString::fromUtf8("켜짐") : QString::fromUtf8("꺼짐"));
    }

    static const struct {
        const char* from;
        const char* to;
    } kReplacements[] = {
        {"[LC] 켜짐 (홀드 인식)", "[LeftClick] 자동 클릭 켜짐"},
        {"[LC] 끔 (사용자 해제)", "[LeftClick] 자동 클릭 꺼짐"},
        {"[RH] 켜짐", "[RightHold] 우클릭 유지 켜짐"},
        {"[RH] 꺼짐", "[RightHold] 우클릭 유지 꺼짐"},
        {"[RH] 끔 (플레임 트리거 우선)", "[RightHold] 우클릭 유지 꺼짐 · 플레임 우선"},
        {"[FT] 켜짐", "[Flame Trigger] 켜짐"},
        {"[FT] 꺼짐", "[Flame Trigger] 꺼짐"},
        {"[Pipela] C++ control window ready", "[Pipela] 준비 완료"},
        {"[Pipela] 종료 (F8)", "[Pipela] 종료 · F8"},
        {"[Reload] 기능 켜짐 (F5)", "[Reload] 기능 켜짐 · F5"},
        {"[Reload] 기능 꺼짐 (F5)", "[Reload] 기능 꺼짐 · F5"},
        {"[Ammo] 기능 켜짐", "[Ammo Restock] 켜짐"},
        {"[Ammo] 기능 꺼짐", "[Ammo Restock] 꺼짐"},
        {"[게임시작]", "[Start Game]"},
    };
    for (const auto& row : kReplacements) {
        const QString from = QString::fromUtf8(row.from);
        if (raw == from) {
            return QString::fromUtf8(row.to);
        }
    }

    static const QRegularExpression kReloadOk(
        QString::fromUtf8(R"(^\[Reload\] 성공 \((\d+)\)$)"));
    if (const QRegularExpressionMatch m = kReloadOk.match(raw); m.hasMatch()) {
        return QString::fromUtf8("[Reload] 성공 ×%1").arg(m.captured(1));
    }
    static const QRegularExpression kFt(
        QString::fromUtf8(R"(^\[Flame Trigger\] 발동 \((\d+)\)$)"));
    if (const QRegularExpressionMatch m = kFt.match(raw); m.hasMatch()) {
        return QString::fromUtf8("[Flame Trigger] 발동 ×%1").arg(m.captured(1));
    }
    static const QRegularExpression kHp(
        QString::fromUtf8(R"(^\[HP Refill\] 트리거 \((\d+)\)$)"));
    if (const QRegularExpressionMatch m = kHp.match(raw); m.hasMatch()) {
        return QString::fromUtf8("[HP Refill] 회복 ×%1").arg(m.captured(1));
    }

    if (raw.startsWith(QString::fromUtf8("[")) && raw.contains(QString::fromUtf8("] 토글"))) {
        return QString::fromUtf8("[설정] 버튼 눌림");
    }

    return raw;
}

void insertText(QTextCursor& cursor, const QString& text, const QColor& color, bool bold = false) {
    QTextCharFormat fmt;
    fmt.setForeground(color);
    if (bold) {
        fmt.setFontWeight(QFont::DemiBold);
    }
    cursor.insertText(text, fmt);
}

QColor highlightWordColor(const QString& word) {
    static const QStringList kOn = {QString::fromUtf8("켜짐"), QString::fromUtf8("ON"),
                                    QString::fromUtf8("성공"), QString::fromUtf8("준비 완료"),
                                    QString::fromUtf8("완료")};
    static const QStringList kOff = {QString::fromUtf8("꺼짐"), QString::fromUtf8("OFF"),
                                   QString::fromUtf8("끔"), QString::fromUtf8("종료")};
    static const QStringList kInfo = {QString::fromUtf8("발동"), QString::fromUtf8("회복"),
                                      QString::fromUtf8("트리거"), QString::fromUtf8("대기"),
                                      QString::fromUtf8("매칭")};
    if (kOn.contains(word)) {
        return terminalOnFg();
    }
    if (kOff.contains(word)) {
        return terminalOffFg();
    }
    if (kInfo.contains(word)) {
        return terminalInfoFg();
    }
    return terminalBodyFg();
}

void appendHighlightedBody(QTextCursor& cursor, const QString& rest) {
    const QStringList tokens = rest.split(QRegularExpression(QString::fromUtf8(R"(\s+)")),
                                          Qt::KeepEmptyParts);
    for (int i = 0; i < tokens.size(); ++i) {
        if (i > 0) {
            insertText(cursor, QString::fromUtf8(" "), terminalBodyFg());
        }
        const QString& tok = tokens[i];
        insertText(cursor, tok, highlightWordColor(tok), highlightWordColor(tok) != terminalBodyFg());
    }
}

}  // namespace

bool consoleLogTimeDisplayRelative() {
    const auto all = pipela::core::registry::loadAllStringValues();
    const auto it = all.find("console_log_time_display_mode");
    if (it == all.end()) {
        return false;
    }
    return it->second == "relative";
}

QString formatTerminalTimePrefix(double wall_t, double mono_t) {
    if (consoleLogTimeDisplayRelative()) {
        const double age = std::max(0.0, nowMonoSec() - mono_t);
        return formatKoCoarseAgo(age);
    }
    const QDateTime dt = QDateTime::fromSecsSinceEpoch(static_cast<qint64>(wall_t));
    return dt.toString(QString::fromUtf8("HH:mm:ss"));
}

QString terminalTimeColorForAge(double age_sec) {
    const double a = std::max(0.0, age_sec);
    if (a <= 45.0) {
        return lerpColor(terminalTimeFresh(), terminalTimeMid(), a / 45.0).name(QColor::HexRgb);
    }
    if (a <= 300.0) {
        return lerpColor(terminalTimeMid(), terminalTimeOld(), (a - 45.0) / 255.0)
            .name(QColor::HexRgb);
    }
    return terminalTimeOld().name(QColor::HexRgb);
}

void appendTerminalLogLine(QTextCursor& cursor, const QString& time_prefix,
                           const QString& raw_line, double time_age_sec) {
    const QString normalized = normalizeTerminalLogLine(raw_line);
    const QColor time_color = QColor(terminalTimeColorForAge(time_age_sec));

    insertText(cursor, time_prefix.leftJustified(8, QLatin1Char(' ')), time_color);
    insertText(cursor, QString::fromUtf8("  "), terminalBodyMuted());

    if (normalized.isEmpty()) {
        return;
    }

    static const QRegularExpression kBracketHead(QString::fromUtf8(R"(^\[([^\]]+)\]\s*(.*)\s*$)"),
                                                 QRegularExpression::DotMatchesEverythingOption);
    const QRegularExpressionMatch m = kBracketHead.match(normalized);
    if (!m.hasMatch()) {
        appendHighlightedBody(cursor, normalized);
        return;
    }

    const QString tag = m.captured(1);
    const QString rest = m.captured(2).trimmed();
    const auto vis = tagVisualFor(tag);
    if (vis) {
        insertText(cursor, QString::fromUtf8("[%1]").arg(vis->display), vis->fg, true);
    } else {
        insertText(cursor, QString::fromUtf8("[%1]").arg(tag), terminalBodyMuted(), true);
    }

    if (!rest.isEmpty()) {
        insertText(cursor, QString::fromUtf8("  "), terminalBodyMuted());
        appendHighlightedBody(cursor, rest);
    }
}

}  // namespace pipela::ui::widgets
