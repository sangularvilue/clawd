#include "Display.h"

#include <ESP32-HUB75-MatrixPanel-I2S-DMA.h>

#include "Config.h"
#include "Render.h"

static_assert(PANEL_WIDTH * PANEL_CHAIN == render::kWidth, "panels must add up to 128 pixels wide");
static_assert(PANEL_HEIGHT == render::kHeight, "panels must be 64 pixels tall");

bool Display::begin() {
  // The canvas exists even if the panels fail, so drawing code never crashes.
  canvas_ = new GFXcanvas16(render::kWidth, render::kHeight);
  shown_ = (uint16_t*)calloc(render::kWidth * render::kHeight, sizeof(uint16_t));

  HUB75_I2S_CFG::i2s_pins pins = {PIN_R1, PIN_G1, PIN_B1, PIN_R2, PIN_G2, PIN_B2, PIN_A,
                                  PIN_B,  PIN_C,  PIN_D,  PIN_E,  PIN_LAT, PIN_OE, PIN_CLK};
  HUB75_I2S_CFG cfg(PANEL_WIDTH, PANEL_HEIGHT, PANEL_CHAIN, pins);
  cfg.driver = PANEL_DRIVER;
  cfg.clkphase = PANEL_CLKPHASE;
  cfg.setPixelColorDepthBits(PANEL_COLOR_DEPTH);

  MatrixPanel_I2S_DMA* m = new MatrixPanel_I2S_DMA(cfg);
  if (!m->begin()) return false;  // leave it: not safe to destroy after a failed begin()
  m->clearScreen();
  matrix_ = m;
  return canvas_->getBuffer() && shown_;
}

void Display::show() {
  if (!matrix_ || !shown_ || !canvas_->getBuffer()) return;
  const uint16_t* next = canvas_->getBuffer();
  for (int16_t y = 0; y < render::kHeight; y++) {
    for (int16_t x = 0; x < render::kWidth; x++) {
      int i = y * render::kWidth + x;
      if (next[i] != shown_[i]) {
        matrix_->drawPixel(x, y, next[i]);
        shown_[i] = next[i];
      }
    }
  }
}

void Display::setBrightness(uint8_t level) {
  if (!matrix_ || level == brightness_) return;
  brightness_ = level;
  matrix_->setBrightness8(level);
}
