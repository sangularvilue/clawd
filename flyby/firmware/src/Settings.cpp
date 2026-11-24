#include "Settings.h"

#include <ctype.h>
#include <stdlib.h>

template <typename T>
static T clampv(T v, T lo, T hi) {
  return v < lo ? lo : v > hi ? hi : v;
}

void sanitizeSettings(Settings& s) {
  if (!(s.lat >= -90 && s.lat <= 90)) s.lat = 0;
  if (!(s.lon >= -180 && s.lon <= 180)) s.lon = 0;
  if (!(s.radiusKm >= 1)) s.radiusKm = 1;  // also catches NaN
  if (s.radiusKm > 200) s.radiusKm = 200;
  s.minAltFt = clampv<int32_t>(s.minAltFt, 0, 60000);
  s.maxAltFt = clampv<int32_t>(s.maxAltFt, s.minAltFt, 99999);
  if ((uint8_t)s.mode > (uint8_t)TrackMode::Flight) s.mode = TrackMode::Area;
  if ((uint8_t)s.view > (uint8_t)ViewMode::List) s.view = ViewMode::Card;
  if ((uint8_t)s.units > (uint8_t)Units::Metric) s.units = Units::Imperial;
  if ((uint8_t)s.source > (uint8_t)DataSource::AdsbFi) s.source = DataSource::AdsbLol;
  s.brightness = clampv<uint8_t>(s.brightness, 1, 255);
  s.nightStartHour = clampv<int8_t>(s.nightStartHour, 0, 23);
  s.nightEndHour = clampv<int8_t>(s.nightEndHour, 0, 23);
  s.cycleSeconds = clampv<uint8_t>(s.cycleSeconds, 3, 60);
  s.refreshSeconds = clampv<uint8_t>(s.refreshSeconds, 5, 120);
  s.tz[sizeof(s.tz) - 1] = '\0';
  s.trackQuery[sizeof(s.trackQuery) - 1] = '\0';
  if (!s.tz[0]) copyStr(s.tz, "UTC0");
}

bool parseCoordinates(const char* text, double& lat, double& lon) {
  if (!text) return false;
  char* end;
  double a = strtod(text, &end);
  if (end == text) return false;
  const char* p = end;
  while (*p == ' ' || *p == ',' || *p == ';' || *p == '\t') p++;
  double b = strtod(p, &end);
  if (end == p) return false;
  while (*end && isspace((unsigned char)*end)) end++;
  if (*end) return false;
  if (a < -90 || a > 90 || b < -180 || b > 180) return false;
  lat = a;
  lon = b;
  return true;
}

bool isNightHour(const Settings& s, int hour) {
  int a = s.nightStartHour, b = s.nightEndHour;
  if (a == b || hour < 0) return false;
  return a < b ? (hour >= a && hour < b) : (hour >= a || hour < b);
}

uint8_t brightnessForHour(const Settings& s, int hour) {
  return isNightHour(s, hour) ? s.nightBrightness : s.brightness;
}

float radiusToKm(float value, Units u) {
  switch (u) {
    case Units::Aviation:
      return value * 1.852f;
    case Units::Imperial:
      return value * 1.609344f;
    default:
      return value;
  }
}

float radiusInUnits(const Settings& s) { return s.radiusKm / radiusToKm(1.0f, s.units); }

const char* radiusUnitLabel(Units u) {
  switch (u) {
    case Units::Aviation:
      return "nm";
    case Units::Imperial:
      return "mi";
    default:
      return "km";
  }
}
