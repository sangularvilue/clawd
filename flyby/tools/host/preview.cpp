// Renders every Flyby screen with the firmware's own drawing code and
// writes them as 128x64 PPM images. led_png.py turns those into PNGs that
// look like a lit LED matrix.
//   make preview
#include <stdio.h>
#include <string.h>
#include <time.h>

#include <fstream>
#include <sstream>
#include <string>

#include "FlightParser.h"
#include "Geo.h"
#include "Render.h"

static std::string outDir = ".";

static void save(GFXcanvas16& c, const char* name) {
  std::string path = outDir + "/" + name + ".ppm";
  FILE* f = fopen(path.c_str(), "wb");
  if (!f) {
    perror(path.c_str());
    return;
  }
  fprintf(f, "P6\n%d %d\n255\n", c.width(), c.height());
  const uint16_t* px = c.getBuffer();
  for (int i = 0; i < c.width() * c.height(); i++) {
    uint16_t v = px[i];
    uint8_t r = (uint8_t)(((v >> 11) & 0x1F) * 255 / 31);
    uint8_t g = (uint8_t)(((v >> 5) & 0x3F) * 255 / 63);
    uint8_t b = (uint8_t)((v & 0x1F) * 255 / 31);
    fputc(r, f);
    fputc(g, f);
    fputc(b, f);
  }
  fclose(f);
  printf("wrote %s\n", path.c_str());
}

static std::string readFile(const std::string& path) {
  std::ifstream f(path);
  std::stringstream ss;
  ss << f.rdbuf();
  return ss.str();
}

static Airport airport(const char* iata, const char* icao, const char* city, float lat, float lon) {
  Airport a;
  a.valid = true;
  copyStr(a.iata, iata);
  copyStr(a.icao, icao);
  copyStr(a.city, city);
  a.lat = lat;
  a.lon = lon;
  return a;
}

static void attach(Flight& f, const Route& r) {
  f.route = r;
  f.routePlausible = routeIsPlausible(r, f.lat, f.lon);
}

static Flight* find(Flight* list, size_t n, const char* callsign) {
  for (size_t i = 0; i < n; i++)
    if (!strcmp(list[i].callsign, callsign)) return &list[i];
  return nullptr;
}

int main(int argc, char** argv) {
  if (argc > 1) outDir = argv[1];
  GFXcanvas16 canvas(render::kWidth, render::kHeight);

  Settings s;
  s.lat = 40.70;
  s.lon = -73.83;
  s.radiusKm = 10;
  s.units = Units::Imperial;

  // Flights from the test feed, as the device would select them.
  JsonDocument filter, doc;
  buildFeedFilter(filter);
  deserializeJson(doc, readFile(std::string(FIXTURES) + "/feed_point.json"),
                  DeserializationOption::Filter(filter));
  FeedFilter ff;
  ff.homeLat = s.lat;
  ff.homeLon = s.lon;
  ff.radiusKm = s.radiusKm;
  Flight flights[MAX_FLIGHTS];
  size_t n = selectFlights(doc, ff, flights, MAX_FLIGHTS);

  // Routes: one parsed from the adsbdb fixture, the rest built by hand.
  JsonDocument rfilter, rdoc;
  buildRouteFilter(rfilter);
  deserializeJson(rdoc, readFile(std::string(FIXTURES) + "/route_BAW117.json"),
                  DeserializationOption::Filter(rfilter));
  Route ba;
  parseRoute(rdoc, ba);

  Route dl;
  dl.valid = true;
  copyStr(dl.airlineName, "Delta Air Lines");
  copyStr(dl.airlineIata, "DL");
  copyStr(dl.airlineIcao, "DAL");
  copyStr(dl.flightIata, "DL1234");
  dl.origin = airport("LGA", "KLGA", "New York", 40.7772f, -73.8726f);
  dl.dest = airport("ATL", "KATL", "Atlanta", 33.6367f, -84.4281f);

  if (Flight* f = find(flights, n, "BAW117")) attach(*f, ba);
  if (Flight* f = find(flights, n, "DAL1234")) attach(*f, dl);

  for (size_t i = 0; i < n; i++) {
    if (!strcmp(flights[i].callsign, "BAW117")) {
      render::flightCard(canvas, flights[i], s, 1, (uint8_t)n, false);
      save(canvas, "01_card_route");
    }
    if (!strcmp(flights[i].callsign, "DAL1234")) {
      render::flightCard(canvas, flights[i], s, 4, (uint8_t)n, false);
      save(canvas, "02_card_climbing");
    }
    if (!strcmp(flights[i].callsign, "UAL2002")) {
      render::flightCard(canvas, flights[i], s, 2, (uint8_t)n, false);
      save(canvas, "03_card_no_route");
    }
    if (!strcmp(flights[i].callsign, "N172SP")) {
      render::flightCard(canvas, flights[i], s, 0, (uint8_t)n, false);
      save(canvas, "04_card_private");
    }
    if (!strcmp(flights[i].hex, "a1b2c3")) {
      render::flightCard(canvas, flights[i], s, 0, 1, false);
      save(canvas, "05_card_unidentified");
    }
  }

  render::flightList(canvas, flights, n, s);
  save(canvas, "06_list");

  // Long city names switch to the small font.
  Flight lax;
  copyStr(lax.callsign, "AAL2");
  copyStr(lax.reg, "N719AN");
  copyStr(lax.typeCode, "B77W");
  lax.hasAlt = true;
  lax.altFt = 36000;
  lax.hasSpeed = true;
  lax.gsKt = 512;
  lax.lat = 39.5;
  lax.lon = -100.0;
  lax.distKm = 2210;
  lax.bearingDeg = 268;
  Route aa;
  aa.valid = true;
  copyStr(aa.airlineIcao, "AAL");
  copyStr(aa.flightIata, "AA2");
  aa.origin = airport("LAX", "KLAX", "Los Angeles", 33.9425f, -118.408f);
  aa.dest = airport("JFK", "KJFK", "New York", 40.6398f, -73.7789f);
  attach(lax, aa);
  render::flightCard(canvas, lax, s, 0, 1, false);
  {
    // Two long names: the longer one loses words first.
    Flight jnb = lax;
    Route r = aa;
    copyStr(r.flightIata, "SA203");
    copyStr(r.airlineIcao, "SAA");
    r.origin = airport("JNB", "FAOR", "Johannesburg", -26.1392f, 28.246f);
    r.dest = airport("EWR", "KEWR", "Newark Liberty Intl", 40.6925f, -74.1687f);
    jnb.lat = 10.0;
    jnb.lon = -20.0;
    attach(jnb, r);
    render::flightCard(canvas, jnb, s, 0, 1, false);
    save(canvas, "11_card_long_names");
  }
  Settings aviation = s;
  aviation.units = Units::Aviation;
  render::flightCard(canvas, lax, aviation, 0, 1, true);
  save(canvas, "07_card_tracking");

  struct tm t = {};
  t.tm_hour = 21;
  t.tm_min = 41;
  t.tm_wday = 2;
  t.tm_mday = 24;
  t.tm_mon = 10;
  Settings tenMiles = s;
  tenMiles.radiusKm = 10 * 1.609344f;
  char status[32];
  render::idleStatus(status, sizeof(status), tenMiles);
  render::idle(canvas, &t, s, status, false);
  save(canvas, "08_idle_clock");

  const char* setup[] = {"Join WiFi network", "Flyby-Setup", "on your phone to", "connect me to WiFi"};
  render::message(canvas, "WIFI SETUP", setup, 4);
  save(canvas, "09_setup");

  const char* loc[] = {"Open this address:", "flyby.local", "or 192.168.1.42", "to set your location"};
  render::message(canvas, "ALMOST THERE", loc, 4, 0xFFC65A);
  save(canvas, "10_set_location");
  return 0;
}
