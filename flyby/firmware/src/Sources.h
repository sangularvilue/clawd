// Where the data comes from. All free, no account or API key needed.
//
//   Positions: adsb.lol, airplanes.live or adsb.fi (same "v2" JSON format)
//   Routes:    adsbdb.com, looked up by callsign
#pragma once

#include <stddef.h>

#include "Settings.h"

// Aircraft within the configured radius of home.
void areaUrl(char* buf, size_t size, const Settings& s);
// One flight by ICAO callsign ("BAW117") or by registration ("G-XWBA").
void callsignUrl(char* buf, size_t size, DataSource src, const char* callsign);
void registrationUrl(char* buf, size_t size, DataSource src, const char* reg);
// adsbdb route lookup. Also accepts IATA flight numbers ("BA117").
void routeUrl(char* buf, size_t size, const char* callsign);

const char* sourceName(DataSource src);
