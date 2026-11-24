// Hardware configuration. Override any of these with build_flags in
// platformio.ini instead of editing this file.
#pragma once

// ---- Panels -----------------------------------------------------------
// Two 64x64 HUB75 panels side by side make the 128x64 display.
#ifndef PANEL_WIDTH
#define PANEL_WIDTH 64
#endif
#ifndef PANEL_HEIGHT
#define PANEL_HEIGHT 64
#endif
#ifndef PANEL_CHAIN
#define PANEL_CHAIN 2
#endif

// Driver chip on the panels. Most panels work with SHIFTREG. If yours stays
// dark or shows noise, try FM6126A (common on P2.5 64x64 panels).
#ifndef PANEL_DRIVER
#define PANEL_DRIVER HUB75_I2S_CFG::SHIFTREG
#endif

// Some panels need the clock phase flipped (symptom: every other column
// shifted, or text looks doubled). Set to false to try it.
#ifndef PANEL_CLKPHASE
#define PANEL_CLKPHASE true
#endif

// Bits per colour channel. 6 is plenty for text and saves RAM for WiFi/TLS.
#ifndef PANEL_COLOR_DEPTH
#define PANEL_COLOR_DEPTH 6
#endif

// ---- Pins -------------------------------------------------------------
// Defaults are the ESP32 Trinity board, which is also the HUB75 DMA
// library's default wiring (plus E on GPIO 18, which 64x64 panels need).
#ifndef PIN_R1
#define PIN_R1 25
#endif
#ifndef PIN_G1
#define PIN_G1 26
#endif
#ifndef PIN_B1
#define PIN_B1 27
#endif
#ifndef PIN_R2
#define PIN_R2 14
#endif
#ifndef PIN_G2
#define PIN_G2 12
#endif
#ifndef PIN_B2
#define PIN_B2 13
#endif
#ifndef PIN_A
#define PIN_A 23
#endif
#ifndef PIN_B
#define PIN_B 19
#endif
#ifndef PIN_C
#define PIN_C 5
#endif
#ifndef PIN_D
#define PIN_D 17
#endif
#ifndef PIN_E
#define PIN_E 18
#endif
#ifndef PIN_LAT
#define PIN_LAT 4
#endif
#ifndef PIN_OE
#define PIN_OE 15
#endif
#ifndef PIN_CLK
#define PIN_CLK 16
#endif

// ---- Network ----------------------------------------------------------
#define HOSTNAME "flyby"              // http://flyby.local
#define SETUP_AP_NAME "Flyby-Setup"   // WiFi network shown during setup
#define USER_AGENT "Flyby/1.0"
