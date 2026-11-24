#include "SettingsStore.h"

#include <Preferences.h>

namespace settings_store {

static const char* kNamespace = "flyby";

void load(Settings& s) {
  Preferences p;
  Settings d;  // defaults
  p.begin(kNamespace, true);
  s.lat = p.getDouble("lat", d.lat);
  s.lon = p.getDouble("lon", d.lon);
  s.radiusKm = p.getFloat("radius", d.radiusKm);
  s.minAltFt = p.getInt("minAlt", d.minAltFt);
  s.maxAltFt = p.getInt("maxAlt", d.maxAltFt);
  s.includeGround = p.getBool("ground", d.includeGround);
  s.mode = (TrackMode)p.getUChar("mode", (uint8_t)d.mode);
  if (!p.getString("track", s.trackQuery, sizeof(s.trackQuery))) s.trackQuery[0] = '\0';
  s.view = (ViewMode)p.getUChar("view", (uint8_t)d.view);
  s.units = (Units)p.getUChar("units", (uint8_t)d.units);
  s.brightness = p.getUChar("bright", d.brightness);
  s.nightBrightness = p.getUChar("nBright", d.nightBrightness);
  s.nightStartHour = p.getChar("nStart", d.nightStartHour);
  s.nightEndHour = p.getChar("nEnd", d.nightEndHour);
  s.cycleSeconds = p.getUChar("cycle", d.cycleSeconds);
  s.clock24h = p.getBool("clock24", d.clock24h);
  s.clockWhenIdle = p.getBool("idleClock", d.clockWhenIdle);
  if (!p.getString("tz", s.tz, sizeof(s.tz))) copyStr(s.tz, d.tz);
  s.source = (DataSource)p.getUChar("source", (uint8_t)d.source);
  s.refreshSeconds = p.getUChar("refresh", d.refreshSeconds);
  p.end();
  sanitizeSettings(s);
}

void save(const Settings& s) {
  Preferences p;
  p.begin(kNamespace, false);
  p.putDouble("lat", s.lat);
  p.putDouble("lon", s.lon);
  p.putFloat("radius", s.radiusKm);
  p.putInt("minAlt", s.minAltFt);
  p.putInt("maxAlt", s.maxAltFt);
  p.putBool("ground", s.includeGround);
  p.putUChar("mode", (uint8_t)s.mode);
  p.putString("track", s.trackQuery);
  p.putUChar("view", (uint8_t)s.view);
  p.putUChar("units", (uint8_t)s.units);
  p.putUChar("bright", s.brightness);
  p.putUChar("nBright", s.nightBrightness);
  p.putChar("nStart", s.nightStartHour);
  p.putChar("nEnd", s.nightEndHour);
  p.putUChar("cycle", s.cycleSeconds);
  p.putBool("clock24", s.clock24h);
  p.putBool("idleClock", s.clockWhenIdle);
  p.putString("tz", s.tz);
  p.putUChar("source", (uint8_t)s.source);
  p.putUChar("refresh", s.refreshSeconds);
  p.end();
}

}  // namespace settings_store
