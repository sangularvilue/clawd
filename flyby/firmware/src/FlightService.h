// Fetches flights in the background so the display never stalls on the
// network. Runs as its own FreeRTOS task on core 0; the display loop on
// core 1 takes copies of the latest snapshot.
#pragma once

#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>

#include "Flight.h"
#include "Settings.h"

struct FlightSnapshot {
  Flight flights[MAX_FLIGHTS];
  uint8_t count = 0;
  bool haveData = false;    // a fetch has succeeded since the search last changed
  bool lastOk = false;      // the most recent fetch succeeded
  uint32_t lastOkMs = 0;
  uint16_t aircraftSeen = 0;
  char status[40] = "";     // why the last fetch failed, if it did
  uint32_t version = 0;
};

class FlightService {
 public:
  void begin(const Settings& s);
  // New settings take effect straight away (wakes the worker).
  void setSettings(const Settings& s);
  void copySnapshot(FlightSnapshot& out);
  uint32_t version() const { return version_; }

 private:
  struct CachedRoute {
    char callsign[9] = "";
    bool found = false;
    Route route;
    uint32_t atMs = 0;
  };
  static const size_t kRouteCacheSize = 24;

  static void taskMain(void* self);
  void run();
  void publish(const FlightSnapshot& next, bool ok);
  bool fetchArea(const Settings& s, FlightSnapshot& out);
  bool fetchTracked(const Settings& s, FlightSnapshot& out);
  bool fetchFeed(const char* url, const Settings& s, float radiusKm, FlightSnapshot& out);
  void addRoutes(FlightSnapshot& snap, int maxLookups);
  // Route for a callsign from the cache or adsbdb. Returns false on a
  // network error (nothing is cached, so it's retried next time).
  bool route(const char* callsign, bool allowFetch, Route& out, bool& found);

  SemaphoreHandle_t mutex_ = nullptr;
  TaskHandle_t task_ = nullptr;
  Settings settings_;
  FlightSnapshot snap_;
  volatile uint32_t version_ = 0;
  CachedRoute cache_[kRouteCacheSize];
  char resolvedQuery_[16] = "";     // track query we last resolved...
  char resolvedCallsign_[9] = "";   // ...and the callsign it maps to
};
