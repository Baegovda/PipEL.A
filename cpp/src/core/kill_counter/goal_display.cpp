#include "pipela/core/kill_counter/goal_display.hpp"

#include <algorithm>
#include <cctype>
#include <regex>
#include <sstream>

#include "pipela/core/kill_counter/tier_data.hpp"

namespace pipela::core::kill_counter {

namespace {

std::string stripCommasSpaces(std::string s) {
    s.erase(std::remove_if(s.begin(), s.end(),
                           [](unsigned char c) { return std::isspace(c) || c == ','; }),
            s.end());
    return s;
}

std::optional<std::pair<std::string, std::string>> slashPairParts(const std::string& prog_txt) {
    if (prog_txt.empty()) {
        return std::nullopt;
    }
    static const std::regex re(R"((\d[\d,\s]*)\s*/\s*(\d[\d,\s]*))");
    std::smatch m;
    if (!std::regex_search(prog_txt, m, re)) {
        return std::nullopt;
    }
    return std::make_pair(stripCommasSpaces(m[1].str()), stripCommasSpaces(m[2].str()));
}

std::string embeddedDigits(const std::string& text) {
    std::string digits;
    for (unsigned char c : text) {
        if (std::isdigit(c)) {
            digits.push_back(static_cast<char>(c));
        }
    }
    return digits;
}

}  // namespace

std::optional<int> progressN1FromOcr(const std::string& progress) {
    const auto parts = slashPairParts(progress);
    if (!parts || parts->first.empty()) {
        return std::nullopt;
    }
    try {
        return std::stoi(parts->first);
    } catch (...) {
        return std::nullopt;
    }
}

std::string formatIntComma(int value) {
    const std::string s = std::to_string(std::max(0, value));
    std::string out;
    out.reserve(s.size() + s.size() / 3);
    int count = 0;
    for (auto it = s.rbegin(); it != s.rend(); ++it) {
        if (count > 0 && count % 3 == 0) {
            out.push_back(',');
        }
        out.push_back(*it);
        ++count;
    }
    std::reverse(out.begin(), out.end());
    return out;
}

std::string panelProgressValueText(const std::string& progress) {
    if (progress.empty()) {
        return "—";
    }
    const auto parts = slashPairParts(progress);
    if (parts && !parts->first.empty() && !parts->second.empty()) {
        if (auto n1 = progressN1FromOcr(progress)) {
            return formatIntComma(*n1);
        }
    }
    const std::string digits = embeddedDigits(progress);
    if (digits.empty()) {
        return "—";
    }
    try {
        return formatIntComma(std::stoi(digits));
    } catch (...) {
        return digits;
    }
}

std::optional<TierState> tierStateForN1(int n1) {
    const auto rows = builtinRankTableRows();
    if (rows.empty()) {
        return std::nullopt;
    }
    n1 = std::max(0, n1);
    const TierRow* cur = &rows.front();
    for (const auto& row : rows) {
        if (row.point <= n1) {
            cur = &row;
        } else {
            break;
        }
    }
    TierState out;
    out.floor = cur->point;
    out.title = cur->title;
    out.next_cap = cur->next_cap;
    if (!cur->next_cap) {
        out.at_max = true;
        out.pct = 100.0;
        return out;
    }
    const int cap = *cur->next_cap;
    out.next_title = "—";
    for (const auto& row : rows) {
        if (row.point == cap) {
            out.next_title = row.title;
            break;
        }
    }
    const int seg = cap - out.floor;
    const int into = n1 - out.floor;
    out.rem = cap - n1;
    if (seg > 0) {
        out.pct = std::max(0.0, std::min(100.0, 100.0 * static_cast<double>(into) / seg));
    }
    return out;
}

std::string goalTransitionLine(int n1) {
    const auto st = tierStateForN1(n1);
    if (!st) {
        return "등급 구간 표를 불러오지 못함";
    }
    if (st->at_max) {
        return st->title + " → —";
    }
    return st->title + " → " + (st->next_title.empty() ? "—" : st->next_title);
}

std::string goalChoinTransitionLine(int n1) {
    const auto rows = builtinRankTableRows();
    if (rows.empty()) {
        return "등급 구간 표를 불러오지 못함";
    }
    const auto& final_row = rows.back();
    const auto st = tierStateForN1(n1);
    if (!st || final_row.point <= 0) {
        return "등급 구간 표를 불러오지 못함";
    }
    if (n1 >= final_row.point) {
        return st->title + " → 달성";
    }
    const std::string ftit = final_row.title.empty() ? "초인" : final_row.title;
    return st->title + " → " + ftit;
}

std::string goalRemLine(int n1) {
    const auto st = tierStateForN1(n1);
    if (!st) {
        return "남은 킬 —";
    }
    if (st->at_max || st->rem <= 0) {
        return "남은 킬 0";
    }
    return "남은 킬 " + formatIntComma(st->rem);
}

std::optional<double> goalTierPctFloat(int n1) {
    const auto st = tierStateForN1(n1);
    if (!st || st->at_max) {
        return std::nullopt;
    }
    return st->pct;
}

}  // namespace pipela::core::kill_counter
