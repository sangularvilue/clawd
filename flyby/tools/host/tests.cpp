// Host-side tests for the Flyby firmware's portable code.
//   make test
#include <stdio.h>
#include <string.h>

#include <fstream>
#include <sstream>
#include <string>

#include "Airlines.h"
#include "FlightParser.h"
#include "Format.h"
#include "Geo.h"
#include "Settings.h"
#include "Sources.h"

static int failures = 0, checks = 0;

#define CHECK(cond)                                                    \
  do {                                                                 \
    checks++;                                                          \
    if (!(cond)) {                                                     \
      failures++;                                                      \
      printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);           \
    }                                                                  \
  } while (0)

#define CHECK_STR(a, b)                                                          \
  do {                                                                           \
    checks++;                                                                    \
    if (strcmp((a), (b)) != 0) {                                                 \
      failures++;                                                                \
      printf("FAIL %s:%d: %s == \"%s\", expected \"%s\"\n", __FILE__, __LINE__, #a, \
             (a), (b));                                                          \
    }                                                                            \
  } while (0)

#define CHECK_NEAR(a, b, tol)                                                   \
  do {                                                                          \
    checks++;                                                                   \
    double _a = (a), _b = (b);                                                  \
    if (fabs(_a - _b) > (tol)) {                                                \
      failures++;                                                               \
      printf("FAIL %s:%d: %s == %f, expected %f\n", __FILE__, __LINE__, #a, _a, _b); \
    }                                                                           \
  } while (0)

static std::string readFile(const char* path) {
  std::ifstream f(path);
  std::stringstream ss;
  ss << f.rdbuf();
  return ss.str();
}

static std::string fixture(const char* name) { return readFile((std::string(FIXTURES) + "/" + name).c_str()); }

static void testGeo() {
  // JFK -> LHR is about 5,540 km.
  CHECK_NEAR(geo::distanceKm(40.6398, -73.7789, 51.4706, -0.4619), 5540, 15);
  CHECK_NEAR(geo::distanceKm(10, 10, 10, 10), 0, 1e-9);
  CHECK_NEAR(geo::bearingDeg(0, 0, 1, 0), 0, 0.01);    // north
  CHECK_NEAR(geo::bearingDeg(0, 0, 0, 1), 90, 0.01);   // east
  CHECK_NEAR(geo::bearingDeg(0, 0, -1, 0), 180, 0.01); // south
  CHECK_NEAR(geo::bearingDeg(0, 0, 0, -1), 270, 0.01); // west
  CHECK_STR(geo::compass16(0), "N");
  CHECK_STR(geo::compass16(359), "N");
  CHECK_STR(geo::compass16(22.5), "NNE");
  CHECK_STR(geo::compass16(200), "SSW");
  CHECK_STR(geo::compass8(44), "NE");
  CHECK_STR(geo::compass8(300), "NW");
}

static void testFeed() {
  std::string json = fixture("feed_point.json");
  JsonDocument filter;
  buildFeedFilter(filter);
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, json, DeserializationOption::Filter(filter));
  CHECK(!err);

  FeedFilter f;
  f.homeLat = 40.70;
  f.homeLon = -73.83;
  f.radiusKm = 10;
  f.maxAltFt = 60000;

  Flight out[MAX_FLIGHTS];
  size_t seen = 0;
  size_t n = selectFlights(doc, f, out, MAX_FLIGHTS, &seen);
  CHECK(seen == 7);  // one aircraft has no position
  CHECK(n == 5);
  // Nearest first; the grounded JetBlue and the far-away American are excluded.
  CHECK_STR(out[0].hex, "a1b2c3");  // TIS-B "~" prefix stripped
  CHECK_STR(out[0].callsign, "");
  CHECK(out[0].hasAlt && out[0].altFt == 800);  // from alt_geom
  CHECK_STR(out[1].callsign, "N172SP");
  CHECK_STR(out[2].callsign, "UAL2002");
  CHECK_STR(out[3].callsign, "BAW117");
  CHECK_STR(out[4].callsign, "DAL1234");
  for (size_t i = 1; i < n; i++) CHECK(out[i - 1].distKm <= out[i].distKm);

  const Flight& ba = out[3];
  CHECK_STR(ba.reg, "G-XWBA");
  CHECK_STR(ba.typeCode, "A35K");
  CHECK_STR(ba.typeDesc, "AIRBUS A-350-1000");
  CHECK(ba.altFt == 3025);
  CHECK_NEAR(ba.gsKt, 182.4, 0.01);
  CHECK(ba.hasVrate && ba.vrateFpm == -768);
  CHECK_NEAR(ba.distKm, 6.3, 0.3);
  CHECK_STR(geo::compass8(ba.bearingDeg), "E");  // ~110 degrees
  CHECK_STR(geo::compass16(ba.bearingDeg), "ESE");
  CHECK(out[2].hasVrate && out[2].vrateFpm == 64);  // geom_rate fallback

  // Smaller output buffer keeps only the nearest.
  Flight three[3];
  CHECK(selectFlights(doc, f, three, 3) == 3);
  CHECK_STR(three[2].callsign, "UAL2002");

  // Altitude window and ground traffic.
  FeedFilter high = f;
  high.minAltFt = 10000;
  n = selectFlights(doc, high, out, MAX_FLIGHTS);
  CHECK(n == 2);
  CHECK_STR(out[0].callsign, "UAL2002");
  CHECK_STR(out[1].callsign, "DAL1234");

  FeedFilter ground = f;
  ground.includeGround = true;
  ground.requireCallsign = true;
  n = selectFlights(doc, ground, out, MAX_FLIGHTS);
  CHECK(n == 5);
  bool sawJbu = false;
  for (size_t i = 0; i < n; i++) {
    CHECK(out[i].callsign[0]);
    if (!strcmp(out[i].callsign, "JBU1")) sawJbu = out[i].onGround;
  }
  CHECK(sawJbu);

  // Tracking mode: no radius limit.
  FeedFilter any = f;
  any.radiusKm = 0;
  any.includeGround = true;
  n = selectFlights(doc, any, out, MAX_FLIGHTS, &seen);
  CHECK(n == 5);
  CHECK(seen == 7);

  // The "aircraft" key some mirrors use.
  std::string alt = json;
  alt.replace(alt.find("\"ac\""), 4, "\"aircraft\"");
  JsonDocument doc2;
  CHECK(!deserializeJson(doc2, alt, DeserializationOption::Filter(filter)));
  CHECK(selectFlights(doc2, f, out, MAX_FLIGHTS) == 5);

  // Garbage and empty feeds.
  JsonDocument empty;
  CHECK(!deserializeJson(empty, "{\"ac\":[]}"));
  CHECK(selectFlights(empty, f, out, MAX_FLIGHTS) == 0);
  CHECK(!deserializeJson(empty, "{\"msg\":\"rate limited\"}"));
  CHECK(selectFlights(empty, f, out, MAX_FLIGHTS) == 0);
}

static void testRoute() {
  JsonDocument filter;
  buildRouteFilter(filter);
  JsonDocument doc;
  CHECK(!deserializeJson(doc, fixture("route_BAW117.json"), DeserializationOption::Filter(filter)));
  Route r;
  CHECK(parseRoute(doc, r));
  CHECK(r.valid);
  CHECK_STR(r.airlineName, "British Airways");
  CHECK_STR(r.airlineIata, "BA");
  CHECK_STR(r.airlineIcao, "BAW");
  CHECK_STR(r.flightIata, "BA117");
  CHECK_STR(r.callsignIcao, "BAW117");
  CHECK(!r.midpoint.valid);
  CHECK_STR(r.origin.iata, "LHR");
  CHECK_STR(r.origin.city, "London");
  CHECK_STR(r.dest.iata, "JFK");
  CHECK_STR(r.dest.icao, "KJFK");
  CHECK_NEAR(r.dest.lat, 40.6398, 1e-3);

  // On approach to JFK: plausible and nearly done.
  CHECK(routeIsPlausible(r, 40.68, -73.76));
  CHECK(routeProgress(r, 40.68, -73.76) > 0.99f);
  // Mid-Atlantic.
  CHECK(routeIsPlausible(r, 52.0, -30.0));
  float p = routeProgress(r, 52.0, -30.0);
  CHECK(p > 0.3f && p < 0.7f);
  // Over Los Angeles: this route can't be right.
  CHECK(!routeIsPlausible(r, 34.05, -118.25));

  JsonDocument unk;
  CHECK(!deserializeJson(unk, fixture("route_unknown.json"), DeserializationOption::Filter(filter)));
  CHECK(!parseRoute(unk, r));
  CHECK(!r.valid);
}

static void testFormat() {
  char b[32];
  formatAltitude(b, sizeof(b), 34000, false, Units::Imperial);
  CHECK_STR(b, "34,000ft");
  formatAltitude(b, sizeof(b), 3025, false, Units::Aviation);
  CHECK_STR(b, "3,025ft");
  formatAltitude(b, sizeof(b), 34000, false, Units::Metric);
  CHECK_STR(b, "10,360m");
  formatAltitude(b, sizeof(b), 0, true, Units::Metric);
  CHECK_STR(b, "GND");

  formatAltitudeShort(b, sizeof(b), 38975, false, Units::Imperial);
  CHECK_STR(b, "39k");
  formatAltitudeShort(b, sizeof(b), 8540, false, Units::Imperial);
  CHECK_STR(b, "8.5k");
  formatAltitudeShort(b, sizeof(b), 9980, false, Units::Imperial);
  CHECK_STR(b, "10k");
  formatAltitudeShort(b, sizeof(b), 800, false, Units::Imperial);
  CHECK_STR(b, "800");

  formatSpeed(b, sizeof(b), 480, Units::Aviation);
  CHECK_STR(b, "480kt");
  formatSpeed(b, sizeof(b), 480, Units::Imperial);
  CHECK_STR(b, "552mph");
  formatSpeed(b, sizeof(b), 480, Units::Metric);
  CHECK_STR(b, "889km/h");

  formatDistance(b, sizeof(b), 6.3f, Units::Metric);
  CHECK_STR(b, "6.3km");
  formatDistance(b, sizeof(b), 18.52f, Units::Aviation);
  CHECK_STR(b, "10nm");
  formatDistance(b, sizeof(b), 5540, Units::Imperial);
  CHECK_STR(b, "3,442mi");

  formatDistance(b, sizeof(b), 10 * 1.609344f, Units::Imperial);
  CHECK_STR(b, "10mi");
  formatDistance(b, sizeof(b), 9.9f * 1.609344f, Units::Imperial);
  CHECK_STR(b, "9.9mi");

  formatThousands(b, sizeof(b), 1234567);
  CHECK_STR(b, "1,234,567");
  formatThousands(b, sizeof(b), -999);
  CHECK_STR(b, "-999");

  aircraftName(b, sizeof(b), "B789", "");
  CHECK_STR(b, "Boeing 787-9");
  aircraftName(b, sizeof(b), "ZZZZ", "PILATUS PC-6 PORTER");
  CHECK_STR(b, "Pilatus Pc-6 Porter");
  aircraftName(b, sizeof(b), "ZZZZ", "");
  CHECK_STR(b, "ZZZZ");

  // Truncation never overflows.
  char tiny[4];
  formatAltitude(tiny, sizeof(tiny), 34000, false, Units::Imperial);
  CHECK(strlen(tiny) == 3);
}

static void testAirlines() {
  char b[16];
  airlineIcaoFromCallsign(b, sizeof(b), "BAW117");
  CHECK_STR(b, "BAW");
  airlineIcaoFromCallsign(b, sizeof(b), "N172SP");
  CHECK_STR(b, "");
  airlineIcaoFromCallsign(b, sizeof(b), "");
  CHECK_STR(b, "");

  CHECK(findAirlineByIcao("DAL") && !strcmp(findAirlineByIcao("DAL")->iata, "DL"));
  CHECK(findAirlineByIata("6E") && !strcmp(findAirlineByIata("6E")->icao, "IGO"));
  CHECK(findAirlineByIcao("XYZ") == nullptr);
  CHECK(airlineColor("DAL") == 0xE01933);
  CHECK(airlineColor("XYZ") == airlineColor("XYZ"));  // stable
  CHECK(airlineColor("XYZ") != airlineColor("XYW"));

  CHECK(flightNumberToCallsign(b, sizeof(b), "BA117"));
  CHECK_STR(b, "BAW117");
  CHECK(flightNumberToCallsign(b, sizeof(b), "ba 0117"));
  CHECK_STR(b, "BAW117");
  CHECK(flightNumberToCallsign(b, sizeof(b), "6E2042"));
  CHECK_STR(b, "IGO2042");
  CHECK(flightNumberToCallsign(b, sizeof(b), "UAL2002"));
  CHECK_STR(b, "UAL2002");
  CHECK(!flightNumberToCallsign(b, sizeof(b), "N172SP"));
  CHECK(!flightNumberToCallsign(b, sizeof(b), "G-XWBA"));
  CHECK(!flightNumberToCallsign(b, sizeof(b), "QQ123"));  // unknown airline

  char cs[9];
  normalizeCallsign(cs, sizeof(cs), "  ual12 ");
  CHECK_STR(cs, "UAL12");
  normalizeCallsign(cs, sizeof(cs), "ABCDEFGHIJK");
  CHECK_STR(cs, "ABCDEFGH");
}

static void testMultiLeg() {
  Route r;
  r.valid = true;
  auto ap = [](const char* code, float lat, float lon) {
    Airport a;
    a.valid = true;
    copyStr(a.iata, code);
    a.lat = lat;
    a.lon = lon;
    return a;
  };
  // Sydney -> Singapore -> London (QF1).
  Route leg = r;
  leg.origin = ap("SYD", -33.95f, 151.18f);
  leg.midpoint = ap("SIN", 1.36f, 103.99f);
  leg.dest = ap("LHR", 51.47f, -0.46f);
  Route first = leg;
  selectLeg(first, -20.0, 130.0);  // over Australia
  CHECK_STR(first.origin.iata, "SYD");
  CHECK_STR(first.dest.iata, "SIN");
  CHECK(!first.midpoint.valid);
  CHECK(routeIsPlausible(first, -20.0, 130.0));
  Route second = leg;
  selectLeg(second, 30.0, 60.0);  // over Iran
  CHECK_STR(second.origin.iata, "SIN");
  CHECK_STR(second.dest.iata, "LHR");
  // No midpoint: unchanged.
  Route direct = leg;
  direct.midpoint = Airport();
  selectLeg(direct, 30.0, 60.0);
  CHECK_STR(direct.origin.iata, "SYD");
  CHECK_STR(direct.dest.iata, "LHR");
}

static void testSettings() {
  double lat = 0, lon = 0;
  CHECK(parseCoordinates("40.7128, -74.0060", lat, lon));
  CHECK_NEAR(lat, 40.7128, 1e-9);
  CHECK_NEAR(lon, -74.006, 1e-9);
  CHECK(parseCoordinates(" 51.5 -0.12 ", lat, lon));
  CHECK_NEAR(lon, -0.12, 1e-9);
  CHECK(!parseCoordinates("40.7128", lat, lon));
  CHECK(!parseCoordinates("91, 0", lat, lon));
  CHECK(!parseCoordinates("10, 200", lat, lon));
  CHECK(!parseCoordinates("10, 20 metres", lat, lon));
  CHECK(!parseCoordinates("", lat, lon));

  Settings s;
  s.nightStartHour = 23;
  s.nightEndHour = 7;
  s.brightness = 100;
  s.nightBrightness = 5;
  CHECK(isNightHour(s, 23));
  CHECK(isNightHour(s, 0));
  CHECK(isNightHour(s, 6));
  CHECK(!isNightHour(s, 7));
  CHECK(!isNightHour(s, 12));
  CHECK(!isNightHour(s, -1));  // time unknown
  CHECK(brightnessForHour(s, 2) == 5);
  CHECK(brightnessForHour(s, 14) == 100);
  s.nightStartHour = 1;
  s.nightEndHour = 5;
  CHECK(isNightHour(s, 3) && !isNightHour(s, 5) && !isNightHour(s, 0));
  s.nightEndHour = 1;
  CHECK(!isNightHour(s, 1));  // same hour: night mode off

  Settings bad;
  bad.lat = 123;
  bad.radiusKm = NAN;
  bad.minAltFt = 5000;
  bad.maxAltFt = 1000;
  bad.cycleSeconds = 0;
  bad.refreshSeconds = 1;
  bad.units = (Units)9;
  bad.tz[0] = '\0';
  sanitizeSettings(bad);
  CHECK(bad.lat == 0);
  CHECK(bad.radiusKm == 1);
  CHECK(bad.maxAltFt == 5000);
  CHECK(bad.cycleSeconds == 3);
  CHECK(bad.refreshSeconds == 5);
  CHECK(bad.units == Units::Imperial);
  CHECK_STR(bad.tz, "UTC0");

  Settings m;
  m.units = Units::Imperial;
  m.radiusKm = radiusToKm(10, Units::Imperial);
  CHECK_NEAR(radiusInUnits(m), 10, 1e-4);
  CHECK_STR(radiusUnitLabel(Units::Aviation), "nm");
}

static void testSources() {
  char url[160];
  Settings s;
  s.lat = 40.7;
  s.lon = -73.83;
  s.radiusKm = 10;
  areaUrl(url, sizeof(url), s);
  CHECK_STR(url, "https://api.adsb.lol/v2/point/40.7000/-73.8300/7");  // 10 km = 5.4 nm, +1, rounded up
  s.source = DataSource::AirplanesLive;
  areaUrl(url, sizeof(url), s);
  CHECK_STR(url, "https://api.airplanes.live/v2/point/40.7000/-73.8300/7");
  s.source = DataSource::AdsbFi;
  areaUrl(url, sizeof(url), s);
  CHECK_STR(url, "https://opendata.adsb.fi/api/v3/lat/40.7000/lon/-73.8300/dist/7");
  s.radiusKm = 2000;
  areaUrl(url, sizeof(url), s);
  CHECK(strstr(url, "/dist/250") != nullptr);  // feeds cap at 250 nm

  callsignUrl(url, sizeof(url), DataSource::AdsbLol, "baw117");
  CHECK_STR(url, "https://api.adsb.lol/v2/callsign/BAW117");
  registrationUrl(url, sizeof(url), DataSource::AdsbLol, "G-XWBA");
  CHECK_STR(url, "https://api.adsb.lol/v2/registration/G-XWBA");
  registrationUrl(url, sizeof(url), DataSource::AirplanesLive, "N12345");
  CHECK_STR(url, "https://api.airplanes.live/v2/reg/N12345");
  registrationUrl(url, sizeof(url), DataSource::AdsbFi, "N12345");
  CHECK_STR(url, "https://opendata.adsb.fi/api/v2/registration/N12345");
  // Nothing odd gets into a URL path.
  callsignUrl(url, sizeof(url), DataSource::AdsbLol, "../x?y=1 2");
  CHECK_STR(url, "https://api.adsb.lol/v2/callsign/XY12");
  routeUrl(url, sizeof(url), "BAW117");
  CHECK_STR(url, "https://api.adsbdb.com/v0/callsign/BAW117");
}

int main() {
  testGeo();
  testFeed();
  testRoute();
  testFormat();
  testAirlines();
  testMultiLeg();
  testSettings();
  testSources();
  printf("%d checks, %d failures\n", checks, failures);
  return failures ? 1 : 0;
}
