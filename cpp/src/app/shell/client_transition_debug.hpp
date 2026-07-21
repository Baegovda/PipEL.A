#pragma once

#include <string>

namespace pipela::app::shell {

bool clientTransitionDebugEnabled();

void clientTransitionLog(const std::string& msg);

}  // namespace pipela::app::shell
