#include "Format.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "AircraftNames.h"
#include "Flight.h"

void formatThousands(char* buf, size_t size, long value) {
  char tmp[24];
  bool neg = value < 0;
  unsigned long v = neg ? (unsigned long)(-value) : (unsigned long)value;
  int n = snprintf(tmp, sizeof(tmp), "%lu", v);
  char out[32];
  size_t o = 0;
  if (neg) out[o++] = '-';
  for (int i = 0; i < n; i++) {
    out[o++] = tmp[i];
    int left = n - i - 1;
    if (left > 0 && left % 3 == 0) out[o++] = ',';
  }
  out[o] = '\0';
  copyStr(buf, size, out);
}

void formatAltitude(char* buf, size_t size, int32_t altFt, bool onGround, Units u) {
  if (onGround) {
    copyStr(buf, size, "GND");
    return;
  }
  char num[16];
  if (u == Units::Metric) {
    long m = lround(altFt * 0.3048 / 10.0) * 10;  // nearest 10 m
    formatThousands(num, sizeof(num), m);
    snprintf(buf, size, "%sm", num);
  } else {
    long ft = lround(altFt / 25.0) * 25;  // feeds report in 25 ft steps
    formatThousands(num, sizeof(num), ft);
    snprintf(buf, size, "%sft", num);
  }
}

void formatAltitudeShort(char* buf, size_t size, int32_t altFt, bool onGround, Units u) {
  if (onGround) {
    copyStr(buf, size, "GND");
    return;
  }
  double v = u == Units::Metric ? altFt * 0.3048 : (double)altFt;
  if (v < 0) v = 0;
  if (v < 950) {
    snprintf(buf, size, "%ld", lround(v / 10.0) * 10);
  } else if (v < 9950) {
    snprintf(buf, size, "%.1fk", lround(v / 100.0) / 10.0);
  } else {
    snprintf(buf, size, "%ldk", lround(v / 1000.0));
  }
}

void formatSpeed(char* buf, size_t size, float gsKt, Units u) {
  switch (u) {
    case Units::Metric:
      snprintf(buf, size, "%ldkm/h", lround(gsKt * 1.852));
      break;
    case Units::Imperial:
      snprintf(buf, size, "%ldmph", lround(gsKt * 1.15078));
      break;
    default:
      snprintf(buf, size, "%ldkt", lround(gsKt));
  }
}

void formatDistance(char* buf, size_t size, float km, Units u) {
  double v = km;
  const char* unit = "km";
  if (u == Units::Aviation) {
    v = km / 1.852;
    unit = "nm";
  } else if (u == Units::Imperial) {
    v = km / 1.609344;
    unit = "mi";
  }
  if (v < 9.95) {
    snprintf(buf, size, "%.1f%s", v, unit);
  } else {
    char num[16];
    formatThousands(num, sizeof(num), lround(v));
    snprintf(buf, size, "%s%s", num, unit);
  }
}

void titleCase(char* buf, size_t size, const char* src) {
  size_t n = 0;
  bool start = true;
  for (; src && *src && n + 1 < size; src++) {
    char c = *src;
    if (isalpha((unsigned char)c)) {
      buf[n++] = start ? (char)toupper((unsigned char)c) : (char)tolower((unsigned char)c);
      start = false;
    } else {
      buf[n++] = c;
      start = (c == ' ' || c == '/' || c == '(');
    }
  }
  if (size) buf[n] = '\0';
}

void aircraftName(char* buf, size_t size, const char* typeCode, const char* feedDesc) {
  const char* known = lookupAircraftName(typeCode);
  if (known) {
    copyStr(buf, size, known);
  } else if (feedDesc && *feedDesc) {
    titleCase(buf, size, feedDesc);
  } else {
    copyStr(buf, size, typeCode ? typeCode : "");
  }
}
