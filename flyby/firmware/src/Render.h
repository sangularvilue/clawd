// Draws every screen of the 128x64 display onto any Adafruit_GFX surface.
// The device draws into an off-screen canvas and copies it to the panels;
// tools/host draws the same screens to PNG files for previewing.
#pragma once

#include <Adafruit_GFX.h>
#include <time.h>

#include "Flight.h"
#include "Settings.h"

namespace render {

static const int16_t kWidth = 128;
static const int16_t kHeight = 64;

// One flight, large. `index`/`count` draw the page dots when cycling.
// `tracking` labels the card for single-flight tracking mode.
void flightCard(Adafruit_GFX& g, const Flight& f, const Settings& s, uint8_t index, uint8_t count,
                bool tracking);

// Up to five flights, one per row.
void flightList(Adafruit_GFX& g, const Flight* flights, size_t n, const Settings& s);

// Clock for when nothing is overhead. `now` is null until the time is known.
// `blink` toggles the colon.
void idle(Adafruit_GFX& g, const struct tm* now, const Settings& s, const char* status, bool blink);

// "No planes within 10mi", sized to fit the idle screen.
void idleStatus(char* buf, size_t size, const Settings& s);

// Title plus up to four centred lines (setup instructions, errors...).
void message(Adafruit_GFX& g, const char* title, const char* const* lines, size_t nLines,
             uint32_t accentRgb = 0x4FC3F7);

// Colour for an altitude, orange near the ground through to violet at cruise.
uint32_t altitudeColor(int32_t altFt, bool onGround);

}  // namespace render
