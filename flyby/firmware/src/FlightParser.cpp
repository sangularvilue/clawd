#include "FlightParser.h"

#include <ctype.h>
#include <string.h>

#include "Geo.h"

void normalizeCallsign(char* dst, size_t size, const char* src) {
  size_t n = 0;
  if (src) {
    while (*src == ' ') src++;
    for (; *src && n + 1 < size; src++) {
      if (*src == ' ') break;
      dst[n++] = (char)toupper((unsigned char)*src);
    }
  }
  dst[n] = '\0';
}

static void addFeedFields(JsonObject o) {
  o["hex"] = true;
  o["flight"] = true;
  o["r"] = true;
  o["t"] = true;
  o["desc"] = true;
  o["alt_baro"] = true;
  o["alt_geom"] = true;
  o["gs"] = true;
  o["track"] = true;
  o["baro_rate"] = true;
  o["geom_rate"] = true;
  o["lat"] = true;
  o["lon"] = true;
}

void buildFeedFilter(JsonDocument& filter) {
  filter.clear();
  addFeedFields(filter["ac"][0].to<JsonObject>());
  addFeedFields(filter["aircraft"][0].to<JsonObject>());
}

static void addAirportFields(JsonObject o) {
  o["iata_code"] = true;
  o["icao_code"] = true;
  o["municipality"] = true;
  o["latitude"] = true;
  o["longitude"] = true;
}

void buildRouteFilter(JsonDocument& filter) {
  filter.clear();
  JsonObject fr = filter["response"]["flightroute"].to<JsonObject>();
  fr["callsign_iata"] = true;
  fr["callsign_icao"] = true;
  JsonObject al = fr["airline"].to<JsonObject>();
  al["name"] = true;
  al["iata"] = true;
  al["icao"] = true;
  addAirportFields(fr["origin"].to<JsonObject>());
  addAirportFields(fr["midpoint"].to<JsonObject>());
  addAirportFields(fr["destination"].to<JsonObject>());
}

static bool readNumber(JsonVariantConst v, double& out) {
  if (v.is<double>()) {
    out = v.as<double>();
    return true;
  }
  return false;
}

// Fills everything except distance/bearing. Returns false if there's no
// usable position.
static bool parseAircraft(JsonObjectConst a, Flight& f) {
  double lat, lon;
  if (!readNumber(a["lat"], lat) || !readNumber(a["lon"], lon)) return false;
  f = Flight();
  f.lat = lat;
  f.lon = lon;

  const char* hex = a["hex"] | "";
  if (*hex == '~') hex++;  // non-ICAO (TIS-B) addresses are prefixed with ~
  copyStr(f.hex, hex);
  normalizeCallsign(f.callsign, sizeof(f.callsign), a["flight"] | "");
  copyStr(f.reg, a["r"] | "");
  copyStr(f.typeCode, a["t"] | "");
  copyStr(f.typeDesc, a["desc"] | "");

  JsonVariantConst alt = a["alt_baro"];
  double n;
  if (alt.is<const char*>()) {
    f.onGround = strcmp(alt.as<const char*>(), "ground") == 0;
    f.hasAlt = f.onGround;
    f.altFt = 0;
  } else if (readNumber(alt, n)) {
    f.hasAlt = true;
    f.altFt = (int32_t)lround(n);
  } else if (readNumber(a["alt_geom"], n)) {
    f.hasAlt = true;
    f.altFt = (int32_t)lround(n);
  }
  if (readNumber(a["gs"], n)) {
    f.hasSpeed = true;
    f.gsKt = (float)n;
  }
  if (readNumber(a["track"], n)) {
    f.hasTrack = true;
    f.trackDeg = (float)n;
  }
  if (readNumber(a["baro_rate"], n) || readNumber(a["geom_rate"], n)) {
    f.hasVrate = true;
    if (n > 32000) n = 32000;
    if (n < -32000) n = -32000;
    f.vrateFpm = (int16_t)lround(n);
  }
  return true;
}

size_t selectFlights(JsonDocument& doc, const FeedFilter& filt, Flight* out, size_t maxOut,
                     size_t* totalSeen) {
  JsonArrayConst list = doc["ac"].as<JsonArrayConst>();
  if (list.isNull()) list = doc["aircraft"].as<JsonArrayConst>();
  size_t count = 0, seen = 0;
  if (!list.isNull()) {
    for (JsonObjectConst a : list) {
      Flight f;
      if (!parseAircraft(a, f)) continue;
      seen++;
      f.distKm = (float)geo::distanceKm(filt.homeLat, filt.homeLon, f.lat, f.lon);
      f.bearingDeg = (float)geo::bearingDeg(filt.homeLat, filt.homeLon, f.lat, f.lon);

      if (filt.radiusKm > 0 && f.distKm > filt.radiusKm) continue;
      if (f.onGround && !filt.includeGround) continue;
      if (!f.onGround && f.hasAlt && (f.altFt < filt.minAltFt || f.altFt > filt.maxAltFt)) continue;
      if (filt.requireCallsign && !f.callsign[0]) continue;

      // Insertion into the sorted output, nearest first.
      size_t pos = count;
      while (pos > 0 && out[pos - 1].distKm > f.distKm) pos--;
      if (pos >= maxOut) continue;
      size_t last = count < maxOut ? count : maxOut - 1;
      for (size_t i = last; i > pos; i--) out[i] = out[i - 1];
      out[pos] = f;
      if (count < maxOut) count++;
    }
  }
  if (totalSeen) *totalSeen = seen;
  return count;
}

static bool parseAirport(JsonObjectConst o, Airport& ap) {
  ap = Airport();
  if (o.isNull()) return false;
  copyStr(ap.iata, o["iata_code"] | "");
  copyStr(ap.icao, o["icao_code"] | "");
  copyStr(ap.city, o["municipality"] | "");
  double lat, lon;
  if (!readNumber(o["latitude"], lat) || !readNumber(o["longitude"], lon)) return false;
  ap.lat = (float)lat;
  ap.lon = (float)lon;
  // Small airfields have no IATA code; the renderer falls back to ICAO.
  ap.valid = ap.iata[0] || ap.icao[0];
  return ap.valid;
}

bool parseRoute(JsonDocument& doc, Route& out) {
  out = Route();
  JsonObjectConst fr = doc["response"]["flightroute"].as<JsonObjectConst>();
  if (fr.isNull()) return false;
  copyStr(out.flightIata, fr["callsign_iata"] | "");
  copyStr(out.callsignIcao, fr["callsign_icao"] | "");
  JsonObjectConst al = fr["airline"].as<JsonObjectConst>();
  if (!al.isNull()) {
    copyStr(out.airlineName, al["name"] | "");
    copyStr(out.airlineIata, al["iata"] | "");
    copyStr(out.airlineIcao, al["icao"] | "");
  }
  bool o = parseAirport(fr["origin"].as<JsonObjectConst>(), out.origin);
  bool d = parseAirport(fr["destination"].as<JsonObjectConst>(), out.dest);
  parseAirport(fr["midpoint"].as<JsonObjectConst>(), out.midpoint);
  out.valid = o && d;
  return true;
}

// How far out of the way the aircraft is, compared with flying a -> b direct.
static double detourKm(const Airport& a, const Airport& b, double lat, double lon) {
  return geo::distanceKm(a.lat, a.lon, lat, lon) + geo::distanceKm(lat, lon, b.lat, b.lon) -
         geo::distanceKm(a.lat, a.lon, b.lat, b.lon);
}

void selectLeg(Route& r, double lat, double lon) {
  if (!r.valid || !r.midpoint.valid) return;
  Airport mid = r.midpoint;
  if (detourKm(r.origin, mid, lat, lon) <= detourKm(mid, r.dest, lat, lon)) {
    r.dest = mid;
  } else {
    r.origin = mid;
  }
  r.midpoint = Airport();
}

bool routeIsPlausible(const Route& r, double lat, double lon) {
  if (!r.valid) return false;
  double od = geo::distanceKm(r.origin.lat, r.origin.lon, r.dest.lat, r.dest.lon);
  double via = geo::distanceKm(r.origin.lat, r.origin.lon, lat, lon) +
               geo::distanceKm(lat, lon, r.dest.lat, r.dest.lon);
  return via <= od * 1.2 + 150.0;
}

float routeProgress(const Route& r, double lat, double lon) {
  if (!r.valid) return 0;
  double a = geo::distanceKm(r.origin.lat, r.origin.lon, lat, lon);
  double b = geo::distanceKm(lat, lon, r.dest.lat, r.dest.lon);
  if (a + b < 1e-6) return 0;
  double p = a / (a + b);
  return (float)(p < 0 ? 0 : p > 1 ? 1 : p);
}
