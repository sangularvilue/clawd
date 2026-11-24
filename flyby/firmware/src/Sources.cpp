#include "Sources.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>

// Endpoints, checked against each project's documentation:
//   adsb.lol        https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}, /v2/callsign/{cs}, /v2/registration/{reg}
//   airplanes.live  https://api.airplanes.live/v2/point/{lat}/{lon}/{nm}, /v2/callsign/{cs}, /v2/reg/{reg}
//   adsb.fi         https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{nm}, /api/v2/callsign/{cs},
//                   /api/v2/registration/{reg}   (1 request/second; please credit adsb.fi)
static const char* base(DataSource src) {
  switch (src) {
    case DataSource::AirplanesLive:
      return "https://api.airplanes.live/v2";
    case DataSource::AdsbFi:
      return "https://opendata.adsb.fi/api/v2";
    default:
      return "https://api.adsb.lol/v2";
  }
}

const char* sourceName(DataSource src) {
  switch (src) {
    case DataSource::AirplanesLive:
      return "airplanes.live";
    case DataSource::AdsbFi:
      return "adsb.fi";
    default:
      return "adsb.lol";
  }
}

// Keeps letters, digits and '-' so nothing odd ends up in a URL path.
static void urlSafe(char* out, size_t size, const char* in) {
  size_t n = 0;
  for (; in && *in && n + 1 < size; in++) {
    char c = *in;
    if (isalnum((unsigned char)c) || c == '-') out[n++] = (char)toupper((unsigned char)c);
  }
  if (size) out[n] = '\0';
}

void areaUrl(char* buf, size_t size, const Settings& s) {
  // The feeds take a radius in nautical miles (max 250). Ask for a little
  // more than we need and filter exactly on the device.
  int nm = (int)ceil(s.radiusKm / 1.852f) + 1;
  if (nm > 250) nm = 250;
  if (s.source == DataSource::AdsbFi) {
    snprintf(buf, size, "https://opendata.adsb.fi/api/v3/lat/%.4f/lon/%.4f/dist/%d", s.lat, s.lon, nm);
  } else {
    snprintf(buf, size, "%s/point/%.4f/%.4f/%d", base(s.source), s.lat, s.lon, nm);
  }
}

void callsignUrl(char* buf, size_t size, DataSource src, const char* callsign) {
  char cs[16];
  urlSafe(cs, sizeof(cs), callsign);
  snprintf(buf, size, "%s/callsign/%s", base(src), cs);
}

void registrationUrl(char* buf, size_t size, DataSource src, const char* reg) {
  char r[16];
  urlSafe(r, sizeof(r), reg);
  snprintf(buf, size, "%s/%s/%s", base(src), src == DataSource::AirplanesLive ? "reg" : "registration", r);
}

void routeUrl(char* buf, size_t size, const char* callsign) {
  char cs[16];
  urlSafe(cs, sizeof(cs), callsign);
  snprintf(buf, size, "https://api.adsbdb.com/v0/callsign/%s", cs);
}
