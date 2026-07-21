#include "pipela/core/template/region_dispatch.hpp"

#include <unordered_map>

namespace pipela::core::template_meta {

namespace {

const std::unordered_map<std::string, std::string> kCaptureToRegion = {
    {"ride_target", "ride"},
    {"hp_zkey", "hp_refill"},
    {"reload_nobullet", "reload_nobullet"},
    {"reload_bullet", "reload_bullet"},
    {"reload_vault", "reload_vault"},
    {"ammo_buybutton", "ammo_buybutton"},
    {"ammo_inven", "ammo_inven"},
    {"ammo_bank", "ammo_bank"},
    {"call_merc_1", "call_merc_1"},
    {"call_merc_2", "call_merc_2"},
    {"call_merc_3", "call_merc_3"},
    {"call_merc_4", "call_merc_4"},
    {"start_game_launcher", "start_game_launcher"},
    {"start_game_intro_skip", "start_game_intro_skip"},
    {"start_game_accept", "start_game_accept"},
};

const std::unordered_map<std::string, std::string> kRegionToKey = {
    {"ride", "ride_detect_region"},
    {"hp_refill", "hp_refill_detect_region"},
    {"kill_counter", "kill_counter_detect_region"},
    {"reload_nobullet", "reload_nobullet_match_region"},
    {"reload_bullet", "reload_bullet_match_region"},
    {"reload_vault", "reload_vault_match_region"},
    {"ammo_buybutton", "ammo_buybutton_match_region"},
    {"ammo_inven", "ammo_inven_match_region"},
    {"ammo_bank", "ammo_bank_match_region"},
    {"call_merc_1", "call_merc_1_match_region"},
    {"call_merc_2", "call_merc_2_match_region"},
    {"call_merc_3", "call_merc_3_match_region"},
    {"call_merc_4", "call_merc_4_match_region"},
    {"start_game_launcher", "start_game_launcher_match_region"},
    {"start_game_intro_skip", "start_game_intro_skip_match_region"},
    {"start_game_accept", "start_game_accept_match_region"},
};

}  // namespace

std::optional<std::string> captureKindToRegionType(const std::string& capture_kind) {
    const auto it = kCaptureToRegion.find(capture_kind);
    if (it == kCaptureToRegion.end()) {
        return std::nullopt;
    }
    return it->second;
}

std::optional<std::string> regionTypeToRegistryKey(const std::string& region_type) {
    const auto it = kRegionToKey.find(region_type);
    if (it == kRegionToKey.end()) {
        return std::nullopt;
    }
    return it->second;
}

bool regionTypeAllowsClear(const std::string& region_type) {
    return kRegionToKey.count(region_type) > 0;
}

}  // namespace pipela::core::template_meta
