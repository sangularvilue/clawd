// Great-circle helpers.
#pragma once

#include <math.h>

namespace geo {

static const double kEarthRadiusKm = 6371.0088;
static const double kPi = 3.14159265358979323846;

inline double toRad(double deg) { return deg * kPi / 180.0; }
inline double toDeg(double rad) { return rad * 180.0 / kPi; }

// Haversine distance in kilometres.
inline double distanceKm(double lat1, double lon1, double lat2, double lon2) {
  double dLat = toRad(lat2 - lat1);
  double dLon = toRad(lon2 - lon1);
  double a = sin(dLat / 2) * sin(dLat / 2) +
             cos(toRad(lat1)) * cos(toRad(lat2)) * sin(dLon / 2) * sin(dLon / 2);
  return 2 * kEarthRadiusKm * atan2(sqrt(a), sqrt(1 - a));
}

// Initial bearing from point 1 to point 2, 0..360, 0 = north.
inline double bearingDeg(double lat1, double lon1, double lat2, double lon2) {
  double p1 = toRad(lat1), p2 = toRad(lat2), dl = toRad(lon2 - lon1);
  double y = sin(dl) * cos(p2);
  double x = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dl);
  double b = toDeg(atan2(y, x));
  return fmod(b + 360.0, 360.0);
}

// 16-point compass name for a bearing.
inline const char* compass16(double deg) {
  static const char* const names[16] = {"N",  "NNE", "NE", "ENE", "E",  "ESE", "SE", "SSE",
                                        "S",  "SSW", "SW", "WSW", "W",  "WNW", "NW", "NNW"};
  int i = (int)floor(fmod(deg + 360.0 + 11.25, 360.0) / 22.5);
  return names[i & 15];
}

// 8-point compass, shorter for tight layouts.
inline const char* compass8(double deg) {
  static const char* const names[8] = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"};
  int i = (int)floor(fmod(deg + 360.0 + 22.5, 360.0) / 45.0);
  return names[i & 7];
}

}  // namespace geo
