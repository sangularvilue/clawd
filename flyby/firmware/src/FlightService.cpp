#include "FlightService.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "Airlines.h"
#include "Config.h"
#include "FlightParser.h"
#include "Sources.h"

namespace {

const int kParseError = -100;
const uint32_t kStaleAfterMs = 60 * 1000;            // drop flights if updates stop this long
const uint32_t kRouteTtlMs = 6UL * 60 * 60 * 1000;   // routes don't change mid-flight
const uint32_t kNoRouteTtlMs = 60UL * 60 * 1000;     // retry unknown callsigns hourly
const int kRouteLookupsPerRefresh = 3;               // spread lookups out

// GET a URL and parse the JSON body through `filter`. Returns the HTTP status
// (or a negative HTTPClient error, or kParseError).
int httpGetJson(const char* url, JsonDocument& doc, JsonDocument& filter) {
  WiFiClientSecure client;
  // Public, read-only flight data: skip certificate checks. That saves RAM
  // and means no root certificates to expire inside the firmware.
  client.setInsecure();
  HTTPClient http;
  http.useHTTP10(true);  // no chunked encoding, so ArduinoJson can read the stream directly
  http.setConnectTimeout(8000);
  http.setTimeout(10000);
  http.setUserAgent(USER_AGENT);
  if (!http.begin(client, url)) return HTTPC_ERROR_CONNECTION_REFUSED;
  http.addHeader("Accept", "application/json");
  int code = http.GET();
  // adsbdb answers unknown callsigns with a 404 and a JSON body.
  if (code == HTTP_CODE_OK || code == HTTP_CODE_NOT_FOUND) {
    DeserializationError err =
        deserializeJson(doc, http.getStream(), DeserializationOption::Filter(filter));
    if (err && code == HTTP_CODE_OK) {
      log_w("JSON error from %s: %s", url, err.c_str());
      code = kParseError;
    }
  }
  http.end();
  return code;
}

void describeError(char* buf, size_t size, const char* source, int code) {
  if (code == HTTP_CODE_TOO_MANY_REQUESTS) {
    snprintf(buf, size, "%s: too many requests", source);
  } else if (code == kParseError) {
    snprintf(buf, size, "%s: bad data", source);
  } else if (code < 0) {
    snprintf(buf, size, "Can't reach %s", source);
  } else {
    snprintf(buf, size, "%s error %d", source, code);
  }
}

// Settings that change *which* flights we want. Changing these clears the screen.
bool sameSearch(const Settings& a, const Settings& b) {
  return a.lat == b.lat && a.lon == b.lon && a.radiusKm == b.radiusKm && a.mode == b.mode &&
         strcmp(a.trackQuery, b.trackQuery) == 0 && a.source == b.source && a.minAltFt == b.minAltFt &&
         a.maxAltFt == b.maxAltFt && a.includeGround == b.includeGround;
}

}  // namespace

void FlightService::begin(const Settings& s) {
  mutex_ = xSemaphoreCreateMutex();
  settings_ = s;
  // Core 0 alongside WiFi; the display loop has core 1 to itself.
  xTaskCreatePinnedToCore(taskMain, "flights", 16384, this, 1, &task_, 0);
}

void FlightService::setSettings(const Settings& s) {
  xSemaphoreTake(mutex_, portMAX_DELAY);
  if (!sameSearch(settings_, s)) {
    snap_.count = 0;
    snap_.haveData = false;
    snap_.status[0] = '\0';
    snap_.version = ++version_;
  }
  settings_ = s;
  xSemaphoreGive(mutex_);
  if (task_) xTaskNotifyGive(task_);
}

void FlightService::copySnapshot(FlightSnapshot& out) {
  xSemaphoreTake(mutex_, portMAX_DELAY);
  out = snap_;
  xSemaphoreGive(mutex_);
}

void FlightService::taskMain(void* self) { static_cast<FlightService*>(self)->run(); }

void FlightService::run() {
  for (;;) {
    xSemaphoreTake(mutex_, portMAX_DELAY);
    Settings s = settings_;
    xSemaphoreGive(mutex_);

    FlightSnapshot next;
    bool ok = false;
    if (WiFi.status() != WL_CONNECTED) {
      copyStr(next.status, "WiFi disconnected");
    } else if (s.mode == TrackMode::Flight) {
      if (s.trackQuery[0]) ok = fetchTracked(s, next);
      else copyStr(next.status, "No flight entered");
    } else if (!s.locationSet()) {
      copyStr(next.status, "Location not set");
    } else {
      ok = fetchArea(s, next);
    }
    if (ok) addRoutes(next, kRouteLookupsPerRefresh);

    // Only publish if nobody changed the search while we were fetching.
    xSemaphoreTake(mutex_, portMAX_DELAY);
    bool current = sameSearch(s, settings_);
    xSemaphoreGive(mutex_);
    if (current) publish(next, ok);

    // Sleep until the next refresh, or until setSettings() wakes us.
    ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(current ? s.refreshSeconds * 1000UL : 0));
  }
}

void FlightService::publish(const FlightSnapshot& next, bool ok) {
  xSemaphoreTake(mutex_, portMAX_DELAY);
  uint32_t now = millis();
  if (ok) {
    for (uint8_t i = 0; i < next.count; i++) snap_.flights[i] = next.flights[i];
    snap_.count = next.count;
    snap_.aircraftSeen = next.aircraftSeen;
    snap_.haveData = true;
    snap_.lastOk = true;
    snap_.lastOkMs = now;
    snap_.status[0] = '\0';
  } else {
    snap_.lastOk = false;
    copyStr(snap_.status, next.status);
    if (now - snap_.lastOkMs > kStaleAfterMs) snap_.count = 0;
  }
  snap_.version = ++version_;
  xSemaphoreGive(mutex_);
}

bool FlightService::fetchFeed(const char* url, const Settings& s, float radiusKm, FlightSnapshot& out) {
  JsonDocument filter;
  buildFeedFilter(filter);
  JsonDocument doc;
  int code = httpGetJson(url, doc, filter);
  if (code != HTTP_CODE_OK) {
    describeError(out.status, sizeof(out.status), sourceName(s.source), code);
    log_w("%s -> %d", url, code);
    return false;
  }
  FeedFilter ff;
  ff.homeLat = s.lat;
  ff.homeLon = s.lon;
  ff.radiusKm = radiusKm;
  bool area = radiusKm > 0;  // tracking mode shows the flight wherever it is
  ff.minAltFt = area ? s.minAltFt : 0;
  ff.maxAltFt = area ? s.maxAltFt : 999999;
  ff.includeGround = area ? s.includeGround : true;
  size_t seen = 0;
  out.count = (uint8_t)selectFlights(doc, ff, out.flights, MAX_FLIGHTS, &seen);
  out.aircraftSeen = (uint16_t)(seen > 65535 ? 65535 : seen);
  return true;
}

bool FlightService::fetchArea(const Settings& s, FlightSnapshot& out) {
  char url[160];
  areaUrl(url, sizeof(url), s);
  return fetchFeed(url, s, s.radiusKm, out);
}

bool FlightService::fetchTracked(const Settings& s, FlightSnapshot& out) {
  char url[160];

  // Work out which callsign a typed flight number means, once per query.
  if (strcmp(resolvedQuery_, s.trackQuery) != 0) {
    char cs[16] = "";
    if (!flightNumberToCallsign(cs, sizeof(cs), s.trackQuery)) {
      // Not an airline we know. adsbdb may know the flight number.
      Route r;
      bool found = false;
      if (!route(s.trackQuery, true, r, found)) {
        copyStr(out.status, "Can't reach adsbdb");
        return false;
      }
      if (found) copyStr(cs, r.callsignIcao);
    }
    copyStr(resolvedCallsign_, cs);
    copyStr(resolvedQuery_, s.trackQuery);
  }

  // Flight number / callsign first, then registration, then the raw text as a callsign.
  if (resolvedCallsign_[0]) {
    callsignUrl(url, sizeof(url), s.source, resolvedCallsign_);
    if (!fetchFeed(url, s, 0, out)) return false;
    if (out.count) return true;
  }
  registrationUrl(url, sizeof(url), s.source, s.trackQuery);
  if (!fetchFeed(url, s, 0, out)) return false;
  if (out.count || resolvedCallsign_[0]) return true;
  callsignUrl(url, sizeof(url), s.source, s.trackQuery);
  return fetchFeed(url, s, 0, out);
}

void FlightService::addRoutes(FlightSnapshot& snap, int maxLookups) {
  for (uint8_t i = 0; i < snap.count; i++) {
    Flight& f = snap.flights[i];
    char airline[4];
    airlineIcaoFromCallsign(airline, sizeof(airline), f.callsign);
    if (!airline[0]) continue;  // private flights aren't in the route database
    Route r;
    bool found = false;
    bool have = route(f.callsign, false, r, found);
    if (!have && maxLookups > 0) {
      maxLookups--;
      have = route(f.callsign, true, r, found);
    }
    if (have && found) {
      selectLeg(r, f.lat, f.lon);
      f.route = r;
      f.routePlausible = routeIsPlausible(r, f.lat, f.lon);
    }
  }
}

bool FlightService::route(const char* callsign, bool allowFetch, Route& out, bool& found) {
  char key[9];
  normalizeCallsign(key, sizeof(key), callsign);
  uint32_t now = millis();

  CachedRoute* slot = nullptr;
  for (CachedRoute& e : cache_) {
    if (e.callsign[0] && strcmp(e.callsign, key) == 0) {
      slot = &e;
      break;
    }
  }
  if (slot && now - slot->atMs < (slot->found ? kRouteTtlMs : kNoRouteTtlMs)) {
    found = slot->found;
    out = slot->route;
    return true;
  }
  if (!allowFetch) return false;

  char url[96];
  routeUrl(url, sizeof(url), key);
  JsonDocument filter;
  buildRouteFilter(filter);
  JsonDocument doc;
  int code = httpGetJson(url, doc, filter);
  if (code != HTTP_CODE_OK && code != HTTP_CODE_NOT_FOUND) {
    log_w("route %s -> %d", key, code);
    return false;
  }
  Route r;
  bool ok = code == HTTP_CODE_OK && parseRoute(doc, r);

  if (!slot) {
    // Reuse an empty slot, else the oldest.
    slot = &cache_[0];
    for (CachedRoute& e : cache_) {
      if (!e.callsign[0]) {
        slot = &e;
        break;
      }
      if (now - e.atMs > now - slot->atMs) slot = &e;
    }
  }
  copyStr(slot->callsign, key);
  slot->found = ok;
  slot->route = r;
  slot->atMs = now;
  found = ok;
  out = r;
  return true;
}
