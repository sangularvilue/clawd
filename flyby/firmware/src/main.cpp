// Flyby: a 128x64 LED display showing the flights going over your home.
//
//   Core 1 (this loop): draws the display ~10 times a second, serves the web page.
//   Core 0 (FlightService): fetches flights and routes every few seconds.
#include <Arduino.h>
#include <ESPmDNS.h>
#include <WiFi.h>
#include <WiFiManager.h>
#include <time.h>

#include <initializer_list>

#include "Config.h"
#include "Display.h"
#include "FlightService.h"
#include "Render.h"
#include "SettingsStore.h"
#include "WebPortal.h"

namespace {

Display display;
FlightService flights;
Settings settings;
FlightSnapshot snap;  // the display's copy of the latest data
uint32_t snapVersion = UINT32_MAX;

// Which card is showing, kept on the same aircraft across refreshes.
uint8_t cardIndex = 0;
uint32_t cardSince = 0;
char cardHex[8] = "";

void showMessage(const char* title, std::initializer_list<const char*> lines, uint32_t accent = 0x4FC3F7) {
  const char* arr[4] = {nullptr, nullptr, nullptr, nullptr};
  size_t n = 0;
  for (const char* l : lines) {
    if (n < 4) arr[n++] = l;
  }
  render::message(display.canvas(), title, arr, n, accent);
  display.show();
}

void applyTimeZone() {
  setenv("TZ", settings.tz, 1);
  tzset();
}

void onSettingsSaved(const Settings& s) {
  settings = s;
  settings_store::save(settings);
  applyTimeZone();
  flights.setSettings(settings);
}

void drawFlights(GFXcanvas16& c, uint32_t now) {
  if (settings.view == ViewMode::List) {
    render::flightList(c, snap.flights, snap.count, settings);
    return;
  }
  if (now - cardSince >= settings.cycleSeconds * 1000UL) {
    cardIndex++;
    cardSince = now;
  }
  if (cardIndex >= snap.count) cardIndex = 0;
  copyStr(cardHex, snap.flights[cardIndex].hex);
  render::flightCard(c, snap.flights[cardIndex], settings, cardIndex, snap.count, false);
}

void drawScreen(GFXcanvas16& c, const struct tm* t, uint32_t now) {
  char ip[24];
  snprintf(ip, sizeof(ip), "or %s", WiFi.localIP().toString().c_str());

  if (settings.mode == TrackMode::Flight) {
    if (!settings.trackQuery[0]) {
      const char* l[] = {"Enter a flight at", HOSTNAME ".local", ip};
      render::message(c, "TRACK A FLIGHT", l, 3, 0xFFC65A);
    } else if (snap.count) {
      render::flightCard(c, snap.flights[0], settings, 0, 1, true);
    } else {
      const char* l[] = {settings.trackQuery,
                         snap.status[0] ? snap.status : (snap.haveData ? "Not in the air" : "Searching..."),
                         snap.haveData && !snap.status[0] ? "or out of coverage" : ""};
      render::message(c, "TRACKING", l, 3);
    }
    return;
  }

  if (!settings.locationSet()) {
    const char* l[] = {"Open this address:", HOSTNAME ".local", ip, "to set your location"};
    render::message(c, "ALMOST THERE", l, 4, 0xFFC65A);
    return;
  }

  if (snap.count) {
    drawFlights(c, now);
    return;
  }

  if (!settings.clockWhenIdle) {
    c.fillScreen(0);
    return;
  }
  char status[40];
  if (snap.status[0]) {
    copyStr(status, snap.status);
  } else if (!snap.haveData) {
    copyStr(status, "Scanning the sky...");
  } else {
    render::idleStatus(status, sizeof(status), settings);
  }
  render::idle(c, t, settings, status, (now % 1000) >= 500);
}

}  // namespace

void setup() {
  Serial.begin(115200);
  settings_store::load(settings);
  applyTimeZone();

  if (!display.begin()) Serial.println("Display failed to start: check PANEL_* settings in Config.h");
  display.setBrightness(settings.brightness);
  showMessage("FLYBY", {"", "Starting up..."});

  WiFi.mode(WIFI_STA);
  WiFiManager wm;
  wm.setHostname(HOSTNAME);
  wm.setTitle("Flyby");
  wm.setConfigPortalTimeout(10 * 60);
  wm.setAPCallback([](WiFiManager*) {
    showMessage("WIFI SETUP", {"Join WiFi network", SETUP_AP_NAME, "on your phone to", "connect me to WiFi"});
  });
  showMessage("CONNECTING", {"", "Joining WiFi..."});
  if (!wm.autoConnect(SETUP_AP_NAME)) {
    showMessage("NO WIFI", {"Setup timed out.", "Restarting..."}, 0xFF6A1A);
    delay(3000);
    ESP.restart();
  }
  WiFi.setAutoReconnect(true);

  configTzTime(settings.tz, "pool.ntp.org", "time.google.com");
  if (MDNS.begin(HOSTNAME)) MDNS.addService("http", "tcp", 80);
  portal::begin(settings, flights, onSettingsSaved);
  flights.begin(settings);
  Serial.printf("Flyby ready: http://%s.local or http://%s\n", HOSTNAME,
                WiFi.localIP().toString().c_str());
}

void loop() {
  portal::handle();

  static uint32_t lastFrame = 0;
  uint32_t now = millis();
  if (now - lastFrame < 100) {
    delay(5);
    return;
  }
  lastFrame = now;

  if (flights.version() != snapVersion) {
    flights.copySnapshot(snap);
    snapVersion = snap.version;
    // Keep showing the same aircraft if it's still in the list.
    for (uint8_t i = 0; i < snap.count; i++) {
      if (cardHex[0] && strcmp(snap.flights[i].hex, cardHex) == 0) cardIndex = i;
    }
  }

  struct tm t;
  bool timeOk = getLocalTime(&t, 0);
  uint8_t level = brightnessForHour(settings, timeOk ? t.tm_hour : -1);
  GFXcanvas16& c = display.canvas();
  if (level == 0) {
    c.fillScreen(0);  // night mode set to "off"
  } else {
    display.setBrightness(level);
    drawScreen(c, timeOk ? &t : nullptr, now);
  }
  display.show();
}
