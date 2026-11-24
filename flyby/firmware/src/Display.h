// The two chained HUB75 panels, drawn through an off-screen canvas.
#pragma once

#include <Adafruit_GFX.h>

class MatrixPanel_I2S_DMA;

class Display {
 public:
  bool begin();

  // Draw the next frame here...
  GFXcanvas16& canvas() { return *canvas_; }
  // ...then copy it to the panels. Only changed pixels are sent, so a
  // mostly-static screen costs almost nothing and never flickers.
  void show();

  void setBrightness(uint8_t level);

 private:
  MatrixPanel_I2S_DMA* matrix_ = nullptr;
  GFXcanvas16* canvas_ = nullptr;
  uint16_t* shown_ = nullptr;
  int brightness_ = -1;
};
