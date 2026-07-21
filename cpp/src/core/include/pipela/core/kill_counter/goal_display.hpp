#pragma once

#include <optional>
#include <string>

namespace pipela::core::kill_counter {

struct TierState {
    int floor{0};
    std::optional<int> next_cap;
    std::string title;
    std::string next_title;
    int rem{0};
    double pct{0.0};
    bool at_max{false};
};

std::optional<int> progressN1FromOcr(const std::string& progress);
std::string panelProgressValueText(const std::string& progress);
std::optional<TierState> tierStateForN1(int n1);
std::string goalTransitionLine(int n1);
std::string goalChoinTransitionLine(int n1);
std::string goalRemLine(int n1);
std::optional<double> goalTierPctFloat(int n1);
std::string formatIntComma(int value);

}  // namespace pipela::core::kill_counter
