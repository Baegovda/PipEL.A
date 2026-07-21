#include "pipela/core/template/capture_catalog.hpp"

#include "pipela/core/paths.hpp"

#include <filesystem>
#include <unordered_map>

namespace pipela::core::template_meta {

namespace {

struct MetaRow {
    const char* filename;
    const char* image_data_key;
    const char* path_key;
};

const std::unordered_map<std::string, MetaRow> kMeta = {
    {"ride_target", {"target.png", "ride_target_image_data", "RIDE_TARGET_IMAGE_PATH"}},
    {"reload_nobullet",
     {"nobullet.png", "reload_nobullet_image_data", "RELOAD_NOBULLET_IMAGE_PATH"}},
    {"reload_bullet", {"bullet.png", "reload_bullet_image_data", "RELOAD_BULLET_IMAGE_PATH"}},
    {"reload_vault", {"vault.png", "reload_vault_image_data", "RELOAD_VAULT_IMAGE_PATH"}},
    {"hp_zkey", {"zkey.png", "hp_refill_zkey_image_data", "HP_REFILL_ZKEY_IMAGE_PATH"}},
    {"ammo_buybutton",
     {"buybutton.png", "ammo_restock_buybutton_image_data", "AMMO_RESTOCK_BUYBUTTON_IMAGE_PATH"}},
    {"ammo_inven", {"inven.png", "ammo_restock_inven_image_data", "AMMO_RESTOCK_INVEN_IMAGE_PATH"}},
    {"ammo_bank", {"bank.png", "ammo_restock_bank_image_data", "AMMO_RESTOCK_BANK_IMAGE_PATH"}},
    {"call_merc_1", {"call_merc_1.png", "call_merc_1_image_data", "CALL_MERC_1_IMAGE_PATH"}},
    {"call_merc_2", {"call_merc_2.png", "call_merc_2_image_data", "CALL_MERC_2_IMAGE_PATH"}},
    {"call_merc_3", {"call_merc_3.png", "call_merc_3_image_data", "CALL_MERC_3_IMAGE_PATH"}},
    {"call_merc_4", {"call_merc_4.png", "call_merc_4_image_data", "CALL_MERC_4_IMAGE_PATH"}},
    {"start_game_launcher",
     {"start_game.png", "start_game_launcher_image_data", "START_GAME_IMAGE_PATH"}},
    {"start_game_intro_skip",
     {"intro_skip.png", "start_game_intro_skip_image_data", "START_GAME_INTRO_SKIP_IMAGE_PATH"}},
    {"start_game_accept",
     {"accept.png", "start_game_accept_image_data", "START_GAME_ACCEPT_IMAGE_PATH"}},
};

}  // namespace

std::optional<CaptureKindMeta> captureKindMeta(const std::string& capture_kind) {
    const auto it = kMeta.find(capture_kind);
    if (it == kMeta.end()) {
        return std::nullopt;
    }
    return CaptureKindMeta{it->second.filename, it->second.image_data_key, it->second.path_key};
}

std::optional<std::string> captureOutputPathForKind(const std::string& capture_kind) {
    const auto meta = captureKindMeta(capture_kind);
    if (!meta) {
        return std::nullopt;
    }
    return (std::filesystem::path(templateCaptureUserStorageDir()) / meta->filename).string();
}

std::optional<std::string> defaultTemplatePathForPathRegistryKey(
    const std::string& path_registry_key) {
    for (const auto& [kind, row] : kMeta) {
        (void)kind;
        if (path_registry_key == row.path_key) {
            return (std::filesystem::path(templateCaptureUserStorageDir()) / row.filename).string();
        }
    }
    return std::nullopt;
}

}  // namespace pipela::core::template_meta
