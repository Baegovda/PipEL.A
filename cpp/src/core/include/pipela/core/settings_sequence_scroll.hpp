#pragma once

#include <string>

namespace pipela::core::settings {

constexpr const char* kFeatReload = "reload";
constexpr const char* kFeatCallMerc = "call_merc";
constexpr const char* kFeatAmmoRestock = "ammo_restock";
constexpr const char* kFeatStartGame = "start_game";

void seqScrollSet(const std::string& feature, int step);
int seqScrollGet(const std::string& feature, int default_step = 0);

}  // namespace pipela::core::settings
