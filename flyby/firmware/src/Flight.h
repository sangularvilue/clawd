// Data model shared by the parser, the renderer and the device code.
// Plain fixed-size structs: no heap, safe to copy between FreeRTOS tasks.
#pragma once

#include <stddef.h>
#include <stdint.h>

static const size_t MAX_FLIGHTS = 5;  // how many nearby flights we keep

struct Airport {
  bool valid = false;
  char iata[4] = "";   // "LHR"
  char icao[5] = "";   // "EGLL"
  char city[28] = "";  // "London"
  float lat = 0;
  float lon = 0;
};

struct Route {
  bool valid = false;          // origin and destination are known
  char airlineName[36] = "";   // "British Airways"
  char airlineIata[3] = "";    // "BA"
  char airlineIcao[4] = "";    // "BAW"
  char flightIata[9] = "";     // "BA117"
  char callsignIcao[9] = "";   // "BAW117"
  Airport origin;
  Airport dest;
  Airport midpoint;            // only for multi-leg flights
};

struct Flight {
  char hex[8] = "";        // ICAO 24-bit address, "4ca7b5"
  char callsign[9] = "";   // "BAW117"
  char reg[12] = "";       // "G-XWBA"
  char typeCode[5] = "";   // ICAO type designator, "A35K"
  char typeDesc[32] = "";  // feed description if provided, "AIRBUS A-350-1000"

  bool onGround = false;
  bool hasAlt = false;
  int32_t altFt = 0;
  bool hasSpeed = false;
  float gsKt = 0;
  bool hasTrack = false;
  float trackDeg = 0;
  bool hasVrate = false;
  int16_t vrateFpm = 0;

  double lat = 0;
  double lon = 0;
  float distKm = 0;     // from home
  float bearingDeg = 0; // from home towards the aircraft

  Route route;          // filled in later from the route lookup
  bool routePlausible = false;
};

// Copies at most size-1 chars and always terminates. Returns dst.
inline char* copyStr(char* dst, size_t size, const char* src) {
  if (!size) return dst;
  size_t i = 0;
  if (src) {
    for (; i + 1 < size && src[i]; i++) dst[i] = src[i];
  }
  dst[i] = '\0';
  return dst;
}

template <size_t N>
inline char* copyStr(char (&dst)[N], const char* src) {
  return copyStr(dst, N, src);
}
