#include "Render.h"

#include <Fonts/TomThumb.h>
#include <ctype.h>
#include <stdio.h>
#include <string.h>

#include "Airlines.h"
#include "FlightParser.h"
#include "Format.h"
#include "Geo.h"

namespace render {
namespace {

// Palette. LEDs swallow dark colours at low brightness, so nothing that
// carries information is darker than about 0x70 per channel.
const uint32_t kWhite = 0xE8E8E8;
const uint32_t kAmber = 0xFFC65A;    // airport codes, like a departures board
const uint32_t kCity = 0xA2B6CC;
const uint32_t kType = 0x7CC8FF;
const uint32_t kDim = 0x80868F;
const uint32_t kLine = 0x3C424C;     // route still to fly
const uint32_t kLineDone = 0xA0A6B4; // route already flown
const uint32_t kAccent = 0x4FC3F7;
const uint32_t kClimb = 0x5BE37D;
const uint32_t kDescend = 0xFF9A4A;
const uint32_t kNoAirline = 0x5A6270;

enum class Font { Classic, Tiny };  // built-in 5x7, TomThumb 3x5

const int16_t kClassicH = 7;

// Little bitmaps, one byte per row, leftmost pixel in the high bit.
const uint8_t kPlaneRight[] PROGMEM = {0x20, 0xB0, 0xFE, 0xB0, 0x20};  // 7x5
const uint8_t kArrowUp[] PROGMEM = {0x20, 0x70, 0xF8};                  // 5x3
const uint8_t kArrowDown[] PROGMEM = {0xF8, 0x70, 0x20};                // 5x3

inline uint16_t C(uint32_t rgb) { return rgb565(rgb); }

void setFont(Adafruit_GFX& g, Font f, uint8_t size) {
  g.setFont(f == Font::Tiny ? &TomThumb : nullptr);
  g.setTextSize(size);
  g.setTextWrap(false);
}

int16_t textWidth(Adafruit_GFX& g, Font f, uint8_t size, const char* s) {
  if (!s || !*s) return 0;
  if (f == Font::Classic) return (int16_t)(strlen(s) * 6 * size - size);
  setFont(g, f, size);
  int16_t x1, y1;
  uint16_t w, h;
  g.getTextBounds(s, 0, 0, &x1, &y1, &w, &h);
  return (int16_t)(x1 + w);
}

// `top` is the first pixel row of the text, whatever the font.
void drawText(Adafruit_GFX& g, Font f, uint8_t size, int16_t x, int16_t top, const char* s,
              uint32_t rgb) {
  if (!s || !*s) return;
  setFont(g, f, size);
  g.setTextColor(C(rgb));
  g.setCursor(x, f == Font::Tiny ? top + 5 : top);
  g.print(s);
}

void drawRight(Adafruit_GFX& g, Font f, uint8_t size, int16_t right, int16_t top, const char* s,
               uint32_t rgb) {
  drawText(g, f, size, right - textWidth(g, f, size, s) + 1, top, s, rgb);
}

void drawCentered(Adafruit_GFX& g, Font f, uint8_t size, int16_t top, const char* s, uint32_t rgb) {
  drawText(g, f, size, (kWidth - textWidth(g, f, size, s)) / 2, top, s, rgb);
}

// Drops characters from the end until the text fits in maxW pixels.
void fitText(Adafruit_GFX& g, Font f, uint8_t size, const char* s, int16_t maxW, char* out,
             size_t outSize) {
  copyStr(out, outSize, s ? s : "");
  size_t n = strlen(out);
  while (n > 0 && textWidth(g, f, size, out) > maxW) out[--n] = '\0';
  while (n > 0 && out[n - 1] == ' ') out[--n] = '\0';
}

// Drops whole words from the end until the text fits (keeps the first word).
void trimWords(Adafruit_GFX& g, Font f, char* s, int16_t maxW) {
  while (textWidth(g, f, 1, s) > maxW) {
    char* sp = strrchr(s, ' ');
    if (!sp) return;
    *sp = '\0';
  }
}

// Origin and destination city names share one row. Prefer the normal font,
// shortening the longer name a word at a time; use the small font only when
// that still doesn't fit.
Font fitCities(Adafruit_GFX& g, const char* origin, const char* dest, char* o, char* d, size_t size) {
  const int16_t gap = 6;
  copyStr(o, size, origin);
  copyStr(d, size, dest);
  for (int pass = 0; pass < 4; pass++) {
    int16_t ow = textWidth(g, Font::Classic, 1, o), dw = textWidth(g, Font::Classic, 1, d);
    if (ow + dw + gap <= kWidth) return Font::Classic;
    char* longer = ow >= dw ? o : d;
    trimWords(g, Font::Classic, longer, kWidth - gap - (ow >= dw ? dw : ow));
  }
  // Still too wide: small font, each name in half the row.
  const int16_t half = kWidth / 2 - gap / 2;
  char tmp[32];
  fitText(g, Font::Tiny, 1, origin, half, tmp, sizeof(tmp));
  copyStr(o, size, tmp);
  fitText(g, Font::Tiny, 1, dest, half, tmp, sizeof(tmp));
  copyStr(d, size, tmp);
  return Font::Tiny;
}

float luminance(uint32_t rgb) {
  return (0.2126f * ((rgb >> 16) & 0xFF) + 0.7152f * ((rgb >> 8) & 0xFF) + 0.0722f * (rgb & 0xFF)) /
         255.0f;
}

uint32_t lerpRgb(uint32_t a, uint32_t b, float t) {
  auto ch = [&](int shift) {
    float va = (float)((a >> shift) & 0xFF), vb = (float)((b >> shift) & 0xFF);
    return (uint32_t)(va + (vb - va) * t + 0.5f) << shift;
  };
  return ch(16) | ch(8) | ch(0);
}

// Who is this? Works out the badge, colour, name and flight number from
// whatever we know: the route lookup, the callsign, the registration.
struct Identity {
  bool airline = false;
  char badge[4] = "";
  uint32_t color = kNoAirline;
  char name[36] = "";
  char flightNo[12] = "";
};

Identity identify(const Flight& f) {
  Identity id;
  char icao[4];
  if (f.route.airlineIcao[0]) {
    copyStr(icao, f.route.airlineIcao);
  } else {
    airlineIcaoFromCallsign(icao, sizeof(icao), f.callsign);
  }
  const AirlineInfo* al = findAirlineByIcao(icao);
  id.airline = icao[0] && (al || f.route.airlineName[0]);

  if (id.airline) {
    id.color = airlineColor(icao);
    const char* iata = al ? al->iata : f.route.airlineIata;
    copyStr(id.badge, iata[0] ? iata : icao);
    copyStr(id.name, al ? al->name : f.route.airlineName);
  }

  if (f.route.flightIata[0]) {
    copyStr(id.flightNo, f.route.flightIata);
  } else if (id.airline && al && f.callsign[0]) {
    snprintf(id.flightNo, sizeof(id.flightNo), "%s%s", al->iata, f.callsign + 3);
  } else if (f.callsign[0]) {
    copyStr(id.flightNo, f.callsign);
  } else if (f.reg[0]) {
    copyStr(id.flightNo, f.reg);
  } else {
    for (size_t i = 0; i < sizeof(id.flightNo) - 1 && f.hex[i]; i++) {
      id.flightNo[i] = (char)toupper((unsigned char)f.hex[i]);
      id.flightNo[i + 1] = '\0';
    }
  }

  if (!id.airline) {
    // Private and general aviation: name the aircraft instead.
    aircraftName(id.name, sizeof(id.name), f.typeCode, f.typeDesc);
    if (!id.name[0]) copyStr(id.name, "Unknown aircraft");
  }
  return id;
}

// Rounded airline badge with its code. Returns its width.
int16_t drawBadge(Adafruit_GFX& g, int16_t x, int16_t y, const Identity& id) {
  const int16_t h = 9;
  int16_t w = id.badge[0] ? textWidth(g, Font::Classic, 1, id.badge) + 4 : 11;
  g.fillRect(x, y, w, h, C(id.color));
  g.drawPixel(x, y, 0);
  g.drawPixel(x + w - 1, y, 0);
  g.drawPixel(x, y + h - 1, 0);
  g.drawPixel(x + w - 1, y + h - 1, 0);
  uint32_t ink = luminance(id.color) > 0.6f ? 0x101010 : 0xFFFFFF;
  if (id.badge[0]) {
    drawText(g, Font::Classic, 1, x + 2, y + 1, id.badge, ink);
  } else {
    g.drawBitmap(x + 2, y + 2, kPlaneRight, 7, 5, C(ink));
  }
  return w;
}

void drawPageDots(Adafruit_GFX& g, uint8_t index, uint8_t count) {
  if (count < 2) return;
  for (uint8_t i = 0; i < count; i++) {
    int16_t x = kWidth - (count - i) * 3 + 1;
    g.fillRect(x, 3, 2, 2, C(i == index ? kWhite : kLine));
  }
}

// Altitude (coloured) with a climb/descend arrow, left aligned. Returns right edge.
int16_t drawAltitude(Adafruit_GFX& g, int16_t x, int16_t top, const Flight& f, Units u, bool shortForm) {
  char buf[16];
  if (!f.hasAlt && !f.onGround) {
    copyStr(buf, "---");
  } else if (shortForm) {
    formatAltitudeShort(buf, sizeof(buf), f.altFt, f.onGround, u);
  } else {
    formatAltitude(buf, sizeof(buf), f.altFt, f.onGround, u);
  }
  drawText(g, Font::Classic, 1, x, top, buf, altitudeColor(f.altFt, f.onGround));
  int16_t right = x + textWidth(g, Font::Classic, 1, buf);
  if (f.hasVrate && !f.onGround && (f.vrateFpm > 300 || f.vrateFpm < -300)) {
    bool up = f.vrateFpm > 0;
    g.drawBitmap(right + 2, top + 2, up ? kArrowUp : kArrowDown, 5, 3, C(up ? kClimb : kDescend));
    right += 7;
  }
  return right;
}

void drawRouteLine(Adafruit_GFX& g, int16_t x0, int16_t x1, int16_t y, float progress) {
  if (x1 - x0 < 12) return;
  int16_t planeX = x0 + (int16_t)((x1 - x0 - 7) * progress + 0.5f);
  for (int16_t x = x0; x <= x1; x += 2) {
    if (x >= planeX - 1 && x <= planeX + 7) continue;
    g.drawPixel(x, y, C(x < planeX ? kLineDone : kLine));
  }
  g.drawBitmap(planeX, y - 2, kPlaneRight, 7, 5, C(kWhite));
}

const char* airportCode(const Airport& a) { return a.iata[0] ? a.iata : a.icao; }

}  // namespace

uint32_t altitudeColor(int32_t altFt, bool onGround) {
  if (onGround) return 0x9A9A9A;
  struct Stop {
    int32_t ft;
    uint32_t rgb;
  };
  static const Stop stops[] = {{0, 0xFF6A1A},     {4000, 0xFFC81E},  {10000, 0x8BE04A},
                               {20000, 0x1ED8C8}, {30000, 0x4A9BFF}, {40000, 0xC46BFF}};
  const size_t n = sizeof(stops) / sizeof(stops[0]);
  if (altFt <= stops[0].ft) return stops[0].rgb;
  for (size_t i = 1; i < n; i++) {
    if (altFt <= stops[i].ft) {
      float t = (float)(altFt - stops[i - 1].ft) / (float)(stops[i].ft - stops[i - 1].ft);
      return lerpRgb(stops[i - 1].rgb, stops[i].rgb, t);
    }
  }
  return stops[n - 1].rgb;
}

void flightCard(Adafruit_GFX& g, const Flight& f, const Settings& s, uint8_t index, uint8_t count,
                bool tracking) {
  g.fillScreen(0);
  char buf[48], fit[48];
  Identity id = identify(f);
  bool hasRoute = f.route.valid && f.routePlausible;

  // Row 1: badge, airline (or aircraft) name, page dots.
  int16_t bw = drawBadge(g, 0, 0, id);
  int16_t dotsW = count > 1 ? count * 3 + 2 : 0;
  fitText(g, Font::Classic, 1, id.name, kWidth - (bw + 3) - dotsW, fit, sizeof(fit));
  drawText(g, Font::Classic, 1, bw + 3, 1, fit, kWhite);
  drawPageDots(g, index, count);

  char aircraft[36];
  aircraftName(aircraft, sizeof(aircraft), f.typeCode, f.typeDesc);

  if (hasRoute) {
    // Row 2: LHR ----✈---- JFK
    const char* from = airportCode(f.route.origin);
    const char* to = airportCode(f.route.dest);
    int16_t fromW = textWidth(g, Font::Classic, 2, from);
    int16_t toW = textWidth(g, Font::Classic, 2, to);
    drawText(g, Font::Classic, 2, 0, 11, from, kAmber);
    drawRight(g, Font::Classic, 2, kWidth - 1, 11, to, kAmber);
    drawRouteLine(g, fromW + 4, kWidth - toW - 5, 18, routeProgress(f.route, f.lat, f.lon));

    // Row 3: cities.
    char oc[28], dc[28];
    Font cf = fitCities(g, f.route.origin.city, f.route.dest.city, oc, dc, sizeof(oc));
    int16_t cityTop = cf == Font::Tiny ? 28 : 27;
    drawText(g, cf, 1, 0, cityTop, oc, kCity);
    drawRight(g, cf, 1, kWidth - 1, cityTop, dc, kCity);

    // Row 4: aircraft.
    fitText(g, Font::Classic, 1, aircraft, kWidth, fit, sizeof(fit));
    drawText(g, Font::Classic, 1, 0, 37, fit, kType);
  } else {
    // Row 2: the flight number, big.
    fitText(g, Font::Classic, 2, id.flightNo, kWidth, fit, sizeof(fit));
    drawText(g, Font::Classic, 2, 0, 11, fit, kAmber);
    if (id.airline) {
      fitText(g, Font::Classic, 1, aircraft, kWidth, fit, sizeof(fit));
      drawText(g, Font::Classic, 1, 0, 27, fit, kType);
      drawText(g, Font::Classic, 1, 0, 37, "Route unknown", kDim);
    } else if (f.reg[0] && strcmp(f.reg, id.flightNo) != 0) {
      drawText(g, Font::Classic, 1, 0, 27, f.reg, kType);
    }
  }

  // Row 5: altitude and speed.
  drawAltitude(g, 0, 47, f, s.units, false);
  if (f.hasSpeed) {
    formatSpeed(buf, sizeof(buf), f.gsKt, s.units);
    drawRight(g, Font::Classic, 1, kWidth - 1, 47, buf, kWhite);
  }

  // Row 6: flight number / registration, and where it is from you.
  char where[64];
  formatDistance(buf, sizeof(buf), f.distKm, s.units);
  snprintf(where, sizeof(where), "%s %s", buf, geo::compass8(f.bearingDeg));
  int16_t whereW = textWidth(g, Font::Classic, 1, where);
  drawRight(g, Font::Classic, 1, kWidth - 1, 56, where, kCity);

  int16_t leftMax = kWidth - whereW - 5;
  if (tracking) {
    drawText(g, Font::Classic, 1, 0, 56, "TRACKING", kAccent);
  } else {
    const char* first = hasRoute ? id.flightNo : (strcmp(f.callsign, id.flightNo) ? f.callsign : "");
    const char* second = (f.reg[0] && strcmp(f.reg, id.flightNo) != 0) ? f.reg : "";
    if (*first && *second) {
      snprintf(buf, sizeof(buf), "%s %s", first, second);
      if (textWidth(g, Font::Classic, 1, buf) > leftMax) copyStr(buf, first);
    } else {
      copyStr(buf, *first ? first : second);
    }
    fitText(g, Font::Classic, 1, buf, leftMax, fit, sizeof(fit));
    drawText(g, Font::Classic, 1, 0, 56, fit, kDim);
  }
}

void flightList(Adafruit_GFX& g, const Flight* flights, size_t n, const Settings& s) {
  g.fillScreen(0);
  char buf[24], fit[24];
  for (size_t i = 0; i < n && i < MAX_FLIGHTS; i++) {
    const Flight& f = flights[i];
    Identity id = identify(f);
    int16_t top = 2 + 12 * (int16_t)i;

    g.fillRect(0, top - 1, 2, 9, C(id.color));
    fitText(g, Font::Classic, 1, id.flightNo, 43, fit, sizeof(fit));
    drawText(g, Font::Classic, 1, 4, top, fit, kWhite);

    if (f.route.valid && f.routePlausible) {
      snprintf(buf, sizeof(buf), "%s\x1a%s", airportCode(f.route.origin), airportCode(f.route.dest));
      drawText(g, Font::Classic, 1, 50, top, buf, kAmber);
    } else {
      drawText(g, Font::Classic, 1, 50, top, f.typeCode, kType);
    }

    if (!f.hasAlt && !f.onGround) {
      copyStr(buf, "---");
    } else {
      formatAltitudeShort(buf, sizeof(buf), f.altFt, f.onGround, s.units);
    }
    int16_t altW = textWidth(g, Font::Classic, 1, buf);
    drawRight(g, Font::Classic, 1, kWidth - 1, top, buf, altitudeColor(f.altFt, f.onGround));
    if (f.hasVrate && !f.onGround && (f.vrateFpm > 300 || f.vrateFpm < -300)) {
      bool up = f.vrateFpm > 0;
      g.drawBitmap(kWidth - altW - 7, top + 2, up ? kArrowUp : kArrowDown, 5, 3,
                   C(up ? kClimb : kDescend));
    }
  }
}

void idleStatus(char* buf, size_t size, const Settings& s) {
  char r[16];
  formatDistance(r, sizeof(r), s.radiusKm, s.units);
  snprintf(buf, size, "No planes within %s", r);
  if (strlen(buf) > 21) snprintf(buf, size, "No planes in %s", r);
}

void idle(Adafruit_GFX& g, const struct tm* now, const Settings& s, const char* status, bool blink) {
  g.fillScreen(0);
  char t[8] = "--:--";
  const char* ampm = nullptr;
  if (now) {
    int h = now->tm_hour;
    if (!s.clock24h) {
      ampm = h < 12 ? "AM" : "PM";
      h %= 12;
      if (h == 0) h = 12;
      snprintf(t, sizeof(t), "%d:%02d", h, now->tm_min);
    } else {
      snprintf(t, sizeof(t), "%02d:%02d", h, now->tm_min);
    }
  }
  int16_t tw = textWidth(g, Font::Classic, 3, t);
  int16_t aw = ampm ? textWidth(g, Font::Classic, 1, ampm) + 3 : 0;
  int16_t x = (kWidth - tw - aw) / 2;
  if (blink) {
    char* colon = strchr(t, ':');
    if (colon) *colon = ' ';
  }
  drawText(g, Font::Classic, 3, x, 8, t, kWhite);
  if (ampm) drawText(g, Font::Classic, 1, x + tw + 3, 8 + 21 - kClassicH, ampm, kDim);

  if (now) {
    static const char* const days[] = {"SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"};
    static const char* const months[] = {"JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                                         "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"};
    char d[20];
    snprintf(d, sizeof(d), "%s %d %s", days[now->tm_wday % 7], now->tm_mday, months[now->tm_mon % 12]);
    drawCentered(g, Font::Classic, 1, 35, d, kCity);
  }
  if (status && *status) {
    char fit[32];
    fitText(g, Font::Classic, 1, status, kWidth, fit, sizeof(fit));
    drawCentered(g, Font::Classic, 1, 52, fit, kDim);
  }
}

void message(Adafruit_GFX& g, const char* title, const char* const* lines, size_t nLines,
             uint32_t accentRgb) {
  g.fillScreen(0);
  char fit[32];
  fitText(g, Font::Classic, 1, title, kWidth, fit, sizeof(fit));
  drawCentered(g, Font::Classic, 1, 3, fit, accentRgb);
  g.drawFastHLine(24, 13, kWidth - 48, C(kLine));
  for (size_t i = 0; i < nLines && i < 4; i++) {
    fitText(g, Font::Classic, 1, lines[i], kWidth, fit, sizeof(fit));
    drawCentered(g, Font::Classic, 1, (int16_t)(19 + 11 * i), fit, i == 0 ? kWhite : kCity);
  }
}

}  // namespace render
