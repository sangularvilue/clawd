// Text formatting for the display: units, numbers, names.
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "Settings.h"

// "34,000ft" / "10,360m". Ground -> "GND".
void formatAltitude(char* buf, size_t size, int32_t altFt, bool onGround, Units u);
// Short form for the list view: "34k", "8.5k", "900", "GND"; metric "10.4k" (metres).
void formatAltitudeShort(char* buf, size_t size, int32_t altFt, bool onGround, Units u);
// "480kt" / "552mph" / "889km/h"
void formatSpeed(char* buf, size_t size, float gsKt, Units u);
// "12nm" / "7.4mi" / "12km"
void formatDistance(char* buf, size_t size, float km, Units u);
// "1,234" (thousands separators)
void formatThousands(char* buf, size_t size, long value);

// Display name for an aircraft: our table first ("Boeing 787-9"),
// then the feed's description in title case, then the raw type code.
void aircraftName(char* buf, size_t size, const char* typeCode, const char* feedDesc);

// "AIRBUS A-350-1000" -> "Airbus A-350-1000"
void titleCase(char* buf, size_t size, const char* src);
