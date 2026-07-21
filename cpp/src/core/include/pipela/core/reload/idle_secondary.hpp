#pragma once

#include <cstdint>

namespace pipela::core::workers {
class WorkerContext;
}

namespace pipela::core::reload {

// AGENT: Idle bullet/vault score refresh when nobullet not latched (reload_idle_secondary.py).
void refreshIdleBulletVaultScores(workers::WorkerContext& ctx, std::intptr_t hwnd);

}  // namespace pipela::core::reload
