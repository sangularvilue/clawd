// Turns ADS-B feed JSON and route lookup JSON into Flight / Route structs.
//
// Feed format: the "v2" readsb API shared by adsb.lol, airplanes.live and
// adsb.fi:  {"ac":[{"hex":"4ca7b5","flight":"BAW117  ","r":"G-XWBA",
//            "t":"A35K","alt_baro":34000,"gs":480.1,"track":271.3,
//            "baro_rate":-64,"lat":51.4,"lon":-0.2, ...}, ...], "now":...}
// (some mirrors call the array "aircraft" instead of "ac").
//
// Route format: adsbdb.com /v0/callsign/<callsign>
//   {"response":{"flightroute":{"callsign_iata":"BA117",
//      "airline":{"name":"British Airways","iata":"BA","icao":"BAW"},
//      "origin":{"iata_code":"LHR","icao_code":"EGLL","municipality":"London",
//                "latitude":51.47,"longitude":-0.46}, "destination":{...}}}}
#pragma once

#include <ArduinoJson.h>

#include "Flight.h"

struct FeedFilter {
  double homeLat = 0;
  double homeLon = 0;
  float radiusKm = 10;       // <= 0 means "any distance" (tracking mode)
  int32_t minAltFt = 0;
  int32_t maxAltFt = 99999;
  bool includeGround = false;
  bool requireCallsign = false;
};

// Fills `filter` with the fields we read, so ArduinoJson discards the rest of
// a large feed while streaming it (keeps RAM use small on the ESP32).
void buildFeedFilter(JsonDocument& filter);
void buildRouteFilter(JsonDocument& filter);

// Picks the nearest aircraft that pass `f`, sorted by distance, at most
// maxOut. Returns the number written to `out`. `totalSeen`, if given,
// receives how many aircraft with a position were in the feed.
size_t selectFlights(JsonDocument& doc, const FeedFilter& f, Flight* out, size_t maxOut,
                     size_t* totalSeen = nullptr);

// Parses an adsbdb callsign response. Returns false for "unknown callsign".
bool parseRoute(JsonDocument& doc, Route& out);

// For multi-leg flights (A -> B -> C), narrows the route to the leg the
// aircraft is flying now, judged by its position. No-op otherwise.
void selectLeg(Route& r, double lat, double lon);

// True when the aircraft's position is roughly on the way from origin to
// destination. Callsign-based route databases are sometimes stale; this hides
// routes that can't be right.
bool routeIsPlausible(const Route& r, double lat, double lon);

// 0 at the origin, 1 at the destination.
float routeProgress(const Route& r, double lat, double lon);

// "BAW117  " -> "BAW117"; also upper-cases.
void normalizeCallsign(char* dst, size_t size, const char* src);
