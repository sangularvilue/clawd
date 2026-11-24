// Airline codes, short names and badge colours.
#pragma once

#include <stddef.h>
#include <stdint.h>

struct AirlineInfo {
  const char* icao;   // "BAW"
  const char* iata;   // "BA"
  const char* name;   // "British Airways"
  uint32_t rgb;       // badge colour, 0xRRGGBB
};

const AirlineInfo* findAirlineByIcao(const char* icao);
const AirlineInfo* findAirlineByIata(const char* iata);

// "BAW117" -> "BAW". Empty if the callsign isn't airline-style
// (3 letters then a digit), e.g. registrations like "N172SP".
void airlineIcaoFromCallsign(char* out, size_t size, const char* callsign);

// Badge colour for an airline ICAO code: the table's colour if known,
// otherwise a stable colour derived from the code. Returns 0xRRGGBB.
uint32_t airlineColor(const char* icao);

// Turns what someone types into an ICAO callsign where possible:
// "BA117" / "ba 117" -> "BAW117"; "BAW117" stays. Returns false when the
// input doesn't look like a flight number (e.g. it's a registration).
bool flightNumberToCallsign(char* out, size_t size, const char* input);

// Pure rgb888 -> rgb565.
inline uint16_t rgb565(uint32_t rgb) {
  return (uint16_t)(((rgb >> 8) & 0xF800) | ((rgb >> 5) & 0x07E0) | ((rgb >> 3) & 0x001F));
}
