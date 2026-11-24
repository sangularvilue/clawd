#include "WebPortal.h"

#include <ArduinoJson.h>
#include <WebServer.h>
#include <WiFi.h>
#include <WiFiManager.h>

#include "Airlines.h"
#include "Config.h"
#include "Format.h"
#include "Sources.h"

namespace portal {
namespace {

WebServer server(80);
Settings settings;  // what the page shows; kept in sync with main through onSave
FlightService* flightService = nullptr;
SaveHandler saveHandler;

struct TzOption {
  const char* label;
  const char* posix;
};
const TzOption kTimeZones[] = {
    {"US Eastern (New York, Toronto)", "EST5EDT,M3.2.0,M11.1.0"},
    {"US Central (Chicago, Dallas)", "CST6CDT,M3.2.0,M11.1.0"},
    {"US Mountain (Denver)", "MST7MDT,M3.2.0,M11.1.0"},
    {"Arizona (Phoenix)", "MST7"},
    {"US Pacific (Los Angeles, Vancouver)", "PST8PDT,M3.2.0,M11.1.0"},
    {"Alaska", "AKST9AKDT,M3.2.0,M11.1.0"},
    {"Hawaii", "HST10"},
    {"UK, Ireland, Portugal", "GMT0BST,M3.5.0/1,M10.5.0"},
    {"Central Europe (Paris, Berlin)", "CET-1CEST,M3.5.0,M10.5.0/3"},
    {"Eastern Europe (Athens, Helsinki)", "EET-2EEST,M3.5.0/3,M10.5.0/4"},
    {"Gulf (Dubai)", "<+04>-4"},
    {"India", "IST-5:30"},
    {"China, Singapore, Perth", "<+08>-8"},
    {"Japan, Korea", "JST-9"},
    {"Australia East (Sydney, Melbourne)", "AEST-10AEDT,M10.1.0,M4.1.0/3"},
    {"Australia (Brisbane)", "AEST-10"},
    {"New Zealand", "NZST-12NZDT,M9.5.0,M4.1.0/3"},
    {"Brazil (Sao Paulo)", "<-03>3"},
    {"UTC", "UTC0"},
};

// ---- HTML helpers -------------------------------------------------------

void esc(String& out, const char* s) {
  for (; s && *s; s++) {
    switch (*s) {
      case '&': out += F("&amp;"); break;
      case '<': out += F("&lt;"); break;
      case '>': out += F("&gt;"); break;
      case '"': out += F("&quot;"); break;
      case '\'': out += F("&#39;"); break;
      default: out += *s;
    }
  }
}

void option(String& out, int value, int selected, const char* label) {
  out += F("<option value=\"");
  out += value;
  out += '"';
  if (value == selected) out += F(" selected");
  out += '>';
  esc(out, label);
  out += F("</option>");
}

void radio(String& out, const char* name, int value, int selected, const char* label) {
  out += F("<label class=r><input type=radio name=\"");
  out += name;
  out += F("\" value=\"");
  out += value;
  out += '"';
  if (value == selected) out += F(" checked");
  out += F("> ");
  esc(out, label);
  out += F("</label>");
}

void checkbox(String& out, const char* name, bool on, const char* label) {
  out += F("<label class=r><input type=checkbox name=\"");
  out += name;
  out += '"';
  if (on) out += F(" checked");
  out += F("> ");
  esc(out, label);
  out += F("</label>");
}

void hourSelect(String& out, const char* name, int selected) {
  out += F("<select name=\"");
  out += name;
  out += F("\">");
  for (int h = 0; h < 24; h++) {
    char label[8];
    snprintf(label, sizeof(label), "%02d:00", h);
    option(out, h, selected, label);
  }
  out += F("</select>");
}

const char kHead[] PROGMEM = R"HTML(<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Flyby</title><style>
:root{color-scheme:dark;--bg:#0f1115;--card:#181b22;--line:#2a2f3a;--text:#e8e8e8;--dim:#9aa3af;--accent:#ffc65a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,sans-serif}
main{max-width:640px;margin:0 auto;padding:16px}h1{font-size:20px;margin:8px 0 16px;color:var(--accent);letter-spacing:.04em}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 14px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin:0 0 10px}
label{display:block;margin:10px 0 4px}label.r{display:inline-flex;gap:6px;align-items:center;margin:4px 14px 4px 0}
input[type=text],input[type=number],select{width:100%;padding:8px 10px;border-radius:7px;border:1px solid var(--line);background:#0c0e12;color:var(--text);font:inherit}
input[type=range]{width:100%}.row{display:flex;gap:10px}.row>*{flex:1}small{color:var(--dim);display:block;margin-top:4px}
button{font:inherit;padding:10px 18px;border-radius:8px;border:0;background:var(--accent);color:#111;font-weight:600;cursor:pointer}
button.ghost{background:transparent;border:1px solid var(--line);color:var(--text)}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:5px 4px;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-weight:500}a{color:var(--accent)}.ok{color:#5be37d}.note{background:#2a2410;border-color:#5a4a1a}
</style></head><body><main><h1>&#9992; FLYBY</h1>
)HTML";

const char kScript[] PROGMEM = R"HTML(<script>
const tz=document.getElementById('tzpick'),tt=document.getElementById('tz');
tz.onchange=()=>{if(tz.value)tt.value=tz.value};
for(const id of ['bright','nbright']){const r=document.getElementById(id),o=document.getElementById(id+'v');r.oninput=()=>o.textContent=r.value;}
async function poll(){try{const s=await (await fetch('/api/status')).json();
const b=document.getElementById('flights');b.innerHTML='';
if(!s.flights.length){const tr=b.insertRow(),td=tr.insertCell();td.colSpan=5;td.textContent=s.status||'Nothing in range right now'}
for(const f of s.flights){const tr=document.createElement('tr');
for(const v of [f.flight,f.route||'',f.type||'',f.alt,f.dist]){const td=document.createElement('td');td.textContent=v;tr.appendChild(td)}b.appendChild(tr)}
document.getElementById('seen').textContent=s.seen+' aircraft in the feed'+(s.ok?'':' (last update failed)');}catch(e){}}
poll();setInterval(poll,5000);
</script>)HTML";

void sendPage(const char* banner) {
  const Settings& s = settings;
  String h;
  h.reserve(9000);
  h += FPSTR(kHead);

  if (banner) {
    h += F("<section class=note>");
    esc(h, banner);
    h += F("</section>");
  }

  // Live view.
  h += F("<section><h2>On the display</h2><table><thead><tr><th>Flight</th><th>Route</th><th>Aircraft</th>"
         "<th>Alt</th><th>Dist</th></tr></thead><tbody id=flights></tbody></table><small id=seen></small></section>");

  h += F("<form method=post action=/save>");

  // Location.
  char buf[64];
  h += F("<section><h2>Location</h2><label>Your coordinates</label><input type=text name=coords "
         "placeholder=\"40.7128, -74.0060\" value=\"");
  if (s.locationSet()) {
    snprintf(buf, sizeof(buf), "%.5f, %.5f", s.lat, s.lon);
    h += buf;
  }
  h += F("\"><small>In Google Maps, right-click your home and click the numbers at the top to copy them.</small>");
  h += F("<div class=row><div><label>Radius (");
  h += radiusUnitLabel(s.units);
  h += F(")</label><input type=number name=radius min=1 max=120 step=0.5 value=\"");
  snprintf(buf, sizeof(buf), "%.1f", radiusInUnits(s));
  h += buf;
  h += F("\"></div><div><label>Lowest (ft)</label><input type=number name=minalt min=0 max=60000 step=100 value=\"");
  h += s.minAltFt;
  h += F("\"></div><div><label>Highest (ft)</label><input type=number name=maxalt min=0 max=99999 step=100 value=\"");
  h += s.maxAltFt;
  h += F("\"></div></div>");
  checkbox(h, "ground", s.includeGround, "Include aircraft on the ground");
  h += F("</section>");

  // Mode.
  h += F("<section><h2>What to show</h2>");
  radio(h, "mode", 0, (int)s.mode, "Flights near me");
  radio(h, "mode", 1, (int)s.mode, "Track one flight");
  h += F("<label>Flight to track</label><input type=text name=track maxlength=15 placeholder=\"BA117, UAL2002 or N12345\" value=\"");
  esc(h, s.trackQuery);
  h += F("\"><small>Flight number, callsign or tail number. Used when tracking one flight.</small>");
  h += F("<label>Layout</label>");
  radio(h, "view", 0, (int)s.view, "One flight at a time");
  radio(h, "view", 1, (int)s.view, "List of up to 5");
  h += F("<div class=row><div><label>Seconds per flight</label><input type=number name=cycle min=3 max=60 value=\"");
  h += s.cycleSeconds;
  h += F("\"></div><div><label>Units</label><select name=units>");
  option(h, 1, (int)s.units, "ft, mph, miles");
  option(h, 0, (int)s.units, "ft, knots, nm");
  option(h, 2, (int)s.units, "m, km/h, km");
  h += F("</select></div></div>");
  checkbox(h, "idleclock", s.clockWhenIdle, "Show a clock when nothing is overhead");
  checkbox(h, "clock24", s.clock24h, "24-hour clock");
  h += F("<label>Time zone</label><select id=tzpick><option value=\"\">Choose...</option>");
  for (const TzOption& z : kTimeZones) {
    h += F("<option value=\"");
    esc(h, z.posix);
    h += '"';
    if (strcmp(z.posix, s.tz) == 0) h += F(" selected");
    h += '>';
    esc(h, z.label);
    h += F("</option>");
  }
  h += F("</select><input type=text id=tz name=tz maxlength=47 style=\"margin-top:6px\" value=\"");
  esc(h, s.tz);
  h += F("\"><small>POSIX time zone. Pick from the list or type your own.</small></section>");

  // Brightness.
  h += F("<section><h2>Brightness</h2><label>Day: <span id=brightv>");
  h += s.brightness;
  h += F("</span></label><input type=range id=bright name=bright min=1 max=255 value=\"");
  h += s.brightness;
  h += F("\"><label>Night: <span id=nbrightv>");
  h += s.nightBrightness;
  h += F("</span> (0 turns the display off)</label><input type=range id=nbright name=nbright min=0 max=255 value=\"");
  h += s.nightBrightness;
  h += F("\"><div class=row><div><label>Night starts</label>");
  hourSelect(h, "nstart", s.nightStartHour);
  h += F("</div><div><label>Night ends</label>");
  hourSelect(h, "nend", s.nightEndHour);
  h += F("</div></div><small>Set both to the same hour to turn night mode off.</small></section>");

  // Data.
  h += F("<section><h2>Flight data</h2><div class=row><div><label>Source</label><select name=source>");
  option(h, 0, (int)s.source, "adsb.lol");
  option(h, 1, (int)s.source, "airplanes.live");
  option(h, 2, (int)s.source, "adsb.fi");
  h += F("</select></div><div><label>Refresh (seconds)</label><input type=number name=refresh min=5 max=120 value=\"");
  h += s.refreshSeconds;
  h += F("\"></div></div><small>Positions from the free community networks <a href=\"https://adsb.lol\">adsb.lol</a>, "
         "<a href=\"https://airplanes.live\">airplanes.live</a> and <a href=\"https://adsb.fi\">adsb.fi</a>. "
         "Routes from <a href=\"https://www.adsbdb.com\">adsbdb.com</a>.</small></section>");

  h += F("<p><button type=submit>Save</button></p></form>");

  // Device.
  h += F("<section><h2>Device</h2><small>IP ");
  h += WiFi.localIP().toString();
  h += F(" &middot; WiFi ");
  esc(h, WiFi.SSID().c_str());
  h += F(" (");
  h += (int)WiFi.RSSI();
  h += F(" dBm) &middot; free memory ");
  h += ESP.getFreeHeap() / 1024;
  h += F(" KB &middot; up ");
  h += millis() / 60000;
  h += F(" min</small><p class=row><button form=restart class=ghost>Restart</button>"
         "<button form=forget class=ghost>Forget WiFi</button></p></section>"
         "<form id=restart method=post action=/restart></form>"
         "<form id=forget method=post action=/forget onsubmit=\"return confirm('Forget this WiFi network and "
         "go back to setup mode?')\"></form>");

  h += FPSTR(kScript);
  h += F("</main></body></html>");
  server.send(200, "text/html; charset=utf-8", h);
}

void handleRoot() { sendPage(server.hasArg("saved") ? "Saved." : nullptr); }

void handleSave() {
  Settings s = settings;
  const char* error = nullptr;

  String coords = server.arg("coords");
  coords.trim();
  if (coords.length()) {
    double lat, lon;
    if (parseCoordinates(coords.c_str(), lat, lon)) {
      s.lat = lat;
      s.lon = lon;
    } else {
      error = "Couldn't read those coordinates. Use the form 40.7128, -74.0060";
    }
  }
  if (server.hasArg("units")) s.units = (Units)server.arg("units").toInt();
  // The radius box is in the units shown when the page loaded.
  if (server.hasArg("radius")) s.radiusKm = radiusToKm(server.arg("radius").toFloat(), settings.units);
  if (server.hasArg("minalt")) s.minAltFt = server.arg("minalt").toInt();
  if (server.hasArg("maxalt")) s.maxAltFt = server.arg("maxalt").toInt();
  s.includeGround = server.hasArg("ground");
  if (server.hasArg("mode")) s.mode = (TrackMode)server.arg("mode").toInt();
  if (server.hasArg("track")) {
    String t = server.arg("track");
    t.trim();
    t.toUpperCase();
    copyStr(s.trackQuery, t.c_str());
  }
  if (server.hasArg("view")) s.view = (ViewMode)server.arg("view").toInt();
  if (server.hasArg("cycle")) s.cycleSeconds = (uint8_t)constrain(server.arg("cycle").toInt(), 3, 60);
  s.clockWhenIdle = server.hasArg("idleclock");
  s.clock24h = server.hasArg("clock24");
  if (server.hasArg("tz")) {
    String tz = server.arg("tz");
    tz.trim();
    if (tz.length()) copyStr(s.tz, tz.c_str());
  }
  if (server.hasArg("bright")) s.brightness = (uint8_t)constrain(server.arg("bright").toInt(), 1, 255);
  if (server.hasArg("nbright")) s.nightBrightness = (uint8_t)constrain(server.arg("nbright").toInt(), 0, 255);
  if (server.hasArg("nstart")) s.nightStartHour = (int8_t)server.arg("nstart").toInt();
  if (server.hasArg("nend")) s.nightEndHour = (int8_t)server.arg("nend").toInt();
  if (server.hasArg("source")) s.source = (DataSource)server.arg("source").toInt();
  if (server.hasArg("refresh")) s.refreshSeconds = (uint8_t)constrain(server.arg("refresh").toInt(), 5, 120);

  if (error) {
    sendPage(error);
    return;
  }
  sanitizeSettings(s);
  settings = s;
  if (saveHandler) saveHandler(s);
  server.sendHeader("Location", "/?saved=1");
  server.send(303);
}

void handleStatus() {
  static FlightSnapshot snap;  // static: too big for the loop task's stack
  if (flightService) flightService->copySnapshot(snap);
  JsonDocument doc;
  doc["ok"] = snap.lastOk;
  doc["status"] = snap.status;
  doc["seen"] = snap.aircraftSeen;
  JsonArray list = doc["flights"].to<JsonArray>();
  char buf[32];
  for (uint8_t i = 0; i < snap.count; i++) {
    const Flight& f = snap.flights[i];
    JsonObject o = list.add<JsonObject>();
    o["flight"] = f.route.flightIata[0] ? f.route.flightIata : (f.callsign[0] ? f.callsign : f.reg);
    if (f.route.valid && f.routePlausible) {
      snprintf(buf, sizeof(buf), "%s → %s", f.route.origin.iata[0] ? f.route.origin.iata : f.route.origin.icao,
               f.route.dest.iata[0] ? f.route.dest.iata : f.route.dest.icao);
      o["route"] = buf;
    }
    aircraftName(buf, sizeof(buf), f.typeCode, f.typeDesc);
    o["type"] = buf;
    formatAltitude(buf, sizeof(buf), f.altFt, f.onGround, settings.units);
    o["alt"] = f.hasAlt || f.onGround ? buf : "";
    formatDistance(buf, sizeof(buf), f.distKm, settings.units);
    o["dist"] = buf;
  }
  String out;
  serializeJson(doc, out);
  server.send(200, "application/json", out);
}

void handleRestart() {
  server.send(200, "text/plain", "Restarting...");
  delay(300);
  ESP.restart();
}

void handleForget() {
  server.send(200, "text/plain",
              "WiFi forgotten. Join the " SETUP_AP_NAME " network to set it up again.");
  delay(300);
  WiFiManager wm;
  wm.resetSettings();
  ESP.restart();
}

}  // namespace

void begin(const Settings& current, FlightService& flights, SaveHandler onSave) {
  settings = current;
  flightService = &flights;
  saveHandler = onSave;
  server.on("/", HTTP_GET, handleRoot);
  server.on("/save", HTTP_POST, handleSave);
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/restart", HTTP_POST, handleRestart);
  server.on("/forget", HTTP_POST, handleForget);
  server.onNotFound([] {
    server.sendHeader("Location", "/");
    server.send(302);
  });
  server.begin();
}

void handle() { server.handleClient(); }

}  // namespace portal
