#include "Airlines.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "Flight.h"

namespace {
// Colours are brightened where the real brand colour is too dark to read on LEDs.
const AirlineInfo kAirlines[] = {
    // North America
    {"AAL", "AA", "American", 0x2E8BEF},       {"DAL", "DL", "Delta", 0xE01933},
    {"UAL", "UA", "United", 0x1E7FD6},         {"SWA", "WN", "Southwest", 0xFFBF27},
    {"JBU", "B6", "JetBlue", 0x3B6FE0},        {"ASA", "AS", "Alaska", 0x48A9C5},
    {"FFT", "F9", "Frontier", 0x2FA37F},       {"NKS", "NK", "Spirit", 0xFFE000},
    {"HAL", "HA", "Hawaiian", 0x9B4FB5},       {"SCX", "SY", "Sun Country", 0xF7941D},
    {"AAY", "G4", "Allegiant", 0xF68B1F},      {"MXY", "MX", "Breeze", 0x35B6E8},
    {"ACA", "AC", "Air Canada", 0xF01428},     {"JZA", "QK", "Air Canada Jazz", 0xF01428},
    {"WJA", "WS", "WestJet", 0x00A3AD},        {"POE", "PD", "Porter", 0x5B7FD1},
    {"TSC", "TS", "Air Transat", 0x2F8FE0},    {"FLE", "F8", "Flair", 0xA6CE39},
    {"SKW", "OO", "SkyWest", 0x4A90C2},        {"RPA", "YX", "Republic", 0x3F7FBF},
    {"ENY", "MQ", "Envoy", 0x2E8BEF},          {"EDV", "9E", "Endeavor", 0xE01933},
    {"JIA", "OH", "PSA", 0x2E8BEF},            {"PDT", "PT", "Piedmont", 0x2E8BEF},
    {"QXE", "QX", "Horizon", 0x48A9C5},        {"ASH", "YV", "Mesa", 0x1E7FD6},
    {"GJS", "G7", "GoJet", 0x1E7FD6},          {"AMX", "AM", "Aeromexico", 0x2A6EBB},
    {"VOI", "Y4", "Volaris", 0xC0309E},        {"VIV", "VB", "Viva Aerobus", 0x00B050},
    {"FDX", "FX", "FedEx", 0xFF6600},          {"UPS", "5X", "UPS", 0xFFB500},
    {"GTI", "5Y", "Atlas Air", 0x3C6FCF},
    // Europe
    {"BAW", "BA", "British Airways", 0x2E6EDB}, {"VIR", "VS", "Virgin Atlantic", 0xE0103A},
    {"EZY", "U2", "easyJet", 0xFF6600},        {"EJU", "EC", "easyJet", 0xFF6600},
    {"EZS", "DS", "easyJet", 0xFF6600},        {"RYR", "FR", "Ryanair", 0xF1C933},
    {"DLH", "LH", "Lufthansa", 0xF9BA00},      {"AFR", "AF", "Air France", 0xE1001E},
    {"KLM", "KL", "KLM", 0x00A1DE},            {"IBE", "IB", "Iberia", 0xD7192D},
    {"VLG", "VY", "Vueling", 0xFFCC00},        {"AEA", "UX", "Air Europa", 0x2F6FD0},
    {"SWR", "LX", "Swiss", 0xE30613},          {"AUA", "OS", "Austrian", 0xE2001A},
    {"SAS", "SK", "SAS", 0x3D5AFE},            {"FIN", "AY", "Finnair", 0x3D6FD9},
    {"EIN", "EI", "Aer Lingus", 0x00A388},     {"TAP", "TP", "TAP Portugal", 0xE3001B},
    {"ITY", "AZ", "ITA Airways", 0x1A6FD6},    {"LOT", "LO", "LOT", 0x2C5BB8},
    {"WZZ", "W6", "Wizz Air", 0xD6008A},       {"NAX", "DY", "Norwegian", 0xD81939},
    {"EWG", "EW", "Eurowings", 0xB0226A},      {"TOM", "BY", "TUI", 0x70CBF4},
    {"EXS", "LS", "Jet2", 0xE8112D},           {"BEL", "SN", "Brussels", 0xC4122F},
    {"CFG", "DE", "Condor", 0xFFC20E},         {"ICE", "FI", "Icelandair", 0x2F6FD0},
    {"THY", "TK", "Turkish", 0xE81932},        {"PGT", "PC", "Pegasus", 0xFFB800},
    {"AEE", "A3", "Aegean", 0x4F7CC2},         {"DHK", "D0", "DHL", 0xFFCC00},
    {"BCS", "QY", "DHL", 0xFFCC00},
    // Middle East, Asia, Pacific
    {"UAE", "EK", "Emirates", 0xD71921},       {"QTR", "QR", "Qatar Airways", 0xA0185A},
    {"ETD", "EY", "Etihad", 0xC9971C},         {"SVA", "SV", "Saudia", 0x00A060},
    {"ELY", "LY", "El Al", 0x2F6FD0},          {"SIA", "SQ", "Singapore", 0xF99F1C},
    {"CPA", "CX", "Cathay Pacific", 0x00A09E}, {"JAL", "JL", "Japan Airlines", 0xE00000},
    {"ANA", "NH", "ANA", 0x2F6FD0},            {"KAL", "KE", "Korean Air", 0x00A3E0},
    {"AAR", "OZ", "Asiana", 0xC4161C},         {"CCA", "CA", "Air China", 0xE60012},
    {"CES", "MU", "China Eastern", 0xD0102E},  {"CSN", "CZ", "China Southern", 0x0090D9},
    {"QFA", "QF", "Qantas", 0xE0001B},         {"VOZ", "VA", "Virgin Australia", 0xD0103A},
    {"ANZ", "NZ", "Air New Zealand", 0x12B5CB},{"JST", "JQ", "Jetstar", 0xFF5115},
    {"AIC", "AI", "Air India", 0xE12B38},      {"IGO", "6E", "IndiGo", 0x3D5AFE},
    {"THA", "TG", "Thai", 0x8B4FB5},           {"MAS", "MH", "Malaysia", 0x1868B3},
    {"GIA", "GA", "Garuda", 0x0096C8},         {"PAL", "PR", "Philippine", 0x2F5BD6},
    {"CEB", "5J", "Cebu Pacific", 0xFFC72C},   {"AXM", "AK", "AirAsia", 0xFF0000},
    {"EVA", "BR", "EVA Air", 0x00A060},        {"CAL", "CI", "China Airlines", 0xD9418E},
    // Latin America, Africa
    {"LAN", "LA", "LATAM", 0xED1650},          {"TAM", "JJ", "LATAM", 0xED1650},
    {"AVA", "AV", "Avianca", 0xDA291C},        {"CMP", "CM", "Copa", 0x2C59C9},
    {"GLO", "G3", "Gol", 0xFF6600},            {"AZU", "AD", "Azul", 0x2C6AD0},
    {"ARG", "AR", "Aerolineas", 0x0094D4},     {"ETH", "ET", "Ethiopian", 0x0BA040},
    {"RAM", "AT", "Royal Air Maroc", 0xD0102E},{"SAA", "SA", "South African", 0x1F6FC4},
    {"KQA", "KQ", "Kenya Airways", 0xD0102E},  {"MSR", "MS", "EgyptAir", 0x3C6EB4},
};
}  // namespace

const AirlineInfo* findAirlineByIcao(const char* icao) {
  if (!icao || !*icao) return nullptr;
  for (const AirlineInfo& a : kAirlines) {
    if (strcmp(a.icao, icao) == 0) return &a;
  }
  return nullptr;
}

const AirlineInfo* findAirlineByIata(const char* iata) {
  if (!iata || !*iata) return nullptr;
  for (const AirlineInfo& a : kAirlines) {
    if (strcmp(a.iata, iata) == 0) return &a;
  }
  return nullptr;
}

void airlineIcaoFromCallsign(char* out, size_t size, const char* cs) {
  if (cs && isalpha((unsigned char)cs[0]) && isalpha((unsigned char)cs[1]) &&
      isalpha((unsigned char)cs[2]) && isdigit((unsigned char)cs[3])) {
    char code[4] = {(char)toupper((unsigned char)cs[0]), (char)toupper((unsigned char)cs[1]),
                    (char)toupper((unsigned char)cs[2]), 0};
    copyStr(out, size, code);
  } else {
    copyStr(out, size, "");
  }
}

static uint32_t hsvToRgb(float h, float s, float v) {
  float c = v * s, hp = h / 60.0f;
  float x = c * (1 - fabsf(fmodf(hp, 2.0f) - 1));
  float r = 0, g = 0, b = 0;
  if (hp < 1) { r = c; g = x; }
  else if (hp < 2) { r = x; g = c; }
  else if (hp < 3) { g = c; b = x; }
  else if (hp < 4) { g = x; b = c; }
  else if (hp < 5) { r = x; b = c; }
  else { r = c; b = x; }
  float m = v - c;
  auto to8 = [](float f) { return (uint32_t)(f * 255.0f + 0.5f); };
  return (to8(r + m) << 16) | (to8(g + m) << 8) | to8(b + m);
}

uint32_t airlineColor(const char* icao) {
  const AirlineInfo* a = findAirlineByIcao(icao);
  if (a) return a->rgb;
  if (!icao || !*icao) return 0x5A6270;  // no airline: slate grey
  uint32_t h = 2166136261u;            // FNV-1a
  for (const char* p = icao; *p; p++) h = (h ^ (uint8_t)*p) * 16777619u;
  return hsvToRgb((float)(h % 360), 0.75f, 0.9f);
}

bool flightNumberToCallsign(char* out, size_t size, const char* input) {
  char s[16];
  size_t n = 0;
  for (const char* p = input; p && *p && n + 1 < sizeof(s); p++) {
    if (*p == ' ' || *p == '-') continue;
    s[n++] = (char)toupper((unsigned char)*p);
  }
  s[n] = 0;
  if (n < 3) return false;

  // Already ICAO style: three letters then digits.
  if (isalpha((unsigned char)s[0]) && isalpha((unsigned char)s[1]) && isalpha((unsigned char)s[2]) &&
      isdigit((unsigned char)s[3])) {
    copyStr(out, size, s);
    return true;
  }
  // IATA style: two-character airline code (may contain one digit, e.g. "6E"), then digits.
  if (isalnum((unsigned char)s[0]) && isalnum((unsigned char)s[1]) && isdigit((unsigned char)s[2]) &&
      !(isdigit((unsigned char)s[0]) && isdigit((unsigned char)s[1]))) {
    char iata[3] = {s[0], s[1], 0};
    const AirlineInfo* a = findAirlineByIata(iata);
    if (!a) return false;
    // Callsigns drop leading zeros: "BA0117" -> "BAW117".
    const char* num = s + 2;
    while (*num == '0' && num[1]) num++;
    snprintf(out, size, "%s%s", a->icao, num);
    return true;
  }
  return false;
}
