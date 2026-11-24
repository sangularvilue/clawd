// Just enough of the Arduino API to build Adafruit GFX and the Flyby
// display code on a desktop computer, for tests and screen previews.
#pragma once

#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <string>

typedef bool boolean;
typedef uint8_t byte;

#define PROGMEM
#define pgm_read_byte(addr) (*(const uint8_t*)(addr))
#define pgm_read_word(addr) (*(const uint16_t*)(addr))
#define pgm_read_dword(addr) (*(const uint32_t*)(addr))

inline void yield() {}
inline float radians(float deg) { return deg * 0.017453292519943295f; }
inline float degrees(float rad) { return rad * 57.29577951308232f; }

class __FlashStringHelper;
#define F(s) (reinterpret_cast<const __FlashStringHelper*>(s))

class String {
 public:
  String(const char* s = "") : s_(s ? s : "") {}
  const char* c_str() const { return s_.c_str(); }
  unsigned int length() const { return (unsigned int)s_.size(); }

 private:
  std::string s_;
};

#include "Print.h"
