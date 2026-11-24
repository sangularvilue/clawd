#pragma once

// Friendly name for an ICAO aircraft type designator ("B789" -> "Boeing 787-9"),
// or nullptr if it's not in the table.
const char* lookupAircraftName(const char* typeCode);
