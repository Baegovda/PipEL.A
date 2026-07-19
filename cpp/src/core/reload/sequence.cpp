#include "pipela/core/reload/sequence.hpp"

#include <algorithm>

namespace pipela::core::reload {

std::tuple<int, std::string> clampAmmoCount(int raw) {
    int ammo = std::clamp(raw, 1, 99999);
    return {ammo, std::to_string(ammo)};
}

}  // namespace pipela::core::reload
