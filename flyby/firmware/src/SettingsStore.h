// Loads and saves Settings in the ESP32's flash (NVS), so they survive reboots.
#pragma once

#include "Settings.h"

namespace settings_store {
void load(Settings& s);
void save(const Settings& s);
}  // namespace settings_store
