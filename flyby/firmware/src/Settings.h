// User settings. Edited from the web page, stored in flash (NVS).
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "Flight.h"

enum class Units : uint8_t { Aviation = 0, Imperial = 1, Metric = 2 };  // ft/kt/nm, ft/mph/mi, m/kmh/km
enum class ViewMode : uint8_t { Card = 0, List = 1 };                    // one flight at a time, or up to 5
enum class TrackMode : uint8_t { Area = 0, Flight = 1 };                 // flights near home, or one flight anywhere
enum class DataSource : uint8_t { AdsbLol = 0, AirplanesLive = 1, AdsbFi = 2 };

struct Settings {
  // Location. 0/0 means "not set yet" and the display asks you to set it.
  double lat = 0;
  double lon = 0;
  float radiusKm = 10;

  // Which aircraft to show.
  int32_t minAltFt = 0;
  int32_t maxAltFt = 60000;
  bool includeGround = false;

  // Area or single-flight tracking.
  TrackMode mode = TrackMode::Area;
  char trackQuery[16] = "";  // flight number ("BA117"), callsign ("BAW117") or registration ("N12345")

  // Display.
  ViewMode view = ViewMode::Card;
  Units units = Units::Imperial;
  uint8_t brightness = 70;       // 0..255
  uint8_t nightBrightness = 8;   // 0 turns the display off at night
  int8_t nightStartHour = 23;    // night window; equal start/end disables it
  int8_t nightEndHour = 7;
  uint8_t cycleSeconds = 8;      // how long each flight card stays up
  bool clock24h = false;
  bool clockWhenIdle = true;

  // Time zone as a POSIX TZ string (the web page has a picker).
  char tz[48] = "EST5EDT,M3.2.0,M11.1.0";

  DataSource source = DataSource::AdsbLol;
  uint8_t refreshSeconds = 10;   // feeds ask for no more than about one call per second

  bool locationSet() const { return !(lat == 0 && lon == 0); }
};

// Clamps everything into sensible ranges (after loading, and after the web form).
void sanitizeSettings(Settings& s);

// Reads "40.7128, -74.0060" (what Google Maps copies when you right-click a
// spot) or "40.7128 -74.0060". Returns false if it isn't a valid pair.
bool parseCoordinates(const char* text, double& lat, double& lon);

// True if `hour` (0-23, local) is inside the night window.
bool isNightHour(const Settings& s, int hour);

// Brightness for the given local hour, or the day brightness if hour < 0
// (time not known yet).
uint8_t brightnessForHour(const Settings& s, int hour);

// Radius in the units the person chose, and back.
float radiusInUnits(const Settings& s);
float radiusToKm(float value, Units u);
const char* radiusUnitLabel(Units u);
