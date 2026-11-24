// The settings page at http://flyby.local (or the device's IP address).
#pragma once

#include <functional>

#include "FlightService.h"
#include "Settings.h"

namespace portal {

using SaveHandler = std::function<void(const Settings&)>;

void begin(const Settings& current, FlightService& flights, SaveHandler onSave);
void handle();  // call from loop()

}  // namespace portal
