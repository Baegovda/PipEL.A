#pragma once

#include "pipela/core/state/app_state.hpp"
#include "pipela/core/vision/capture.hpp"

namespace pipela::core::kill_counter {

bool shouldSkipOcrSameScreen(const state::AppState& state, const vision::BgrImage& cur_bgr);
void rememberOcrScreenProbe(const vision::BgrImage& cur_bgr);

}  // namespace pipela::core::kill_counter
