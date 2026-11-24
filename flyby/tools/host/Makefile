# Builds the Flyby firmware's portable code on a desktop computer.
#
#   make test      run the unit tests
#   make preview   render every screen to PNG in ./previews (needs python3 + Pillow)
#
# Pinned library versions match firmware/platformio.ini. They're cloned into
# .deps on first use.

SRC     := ../../firmware/src
DEPS    := .deps
JSON    := $(DEPS)/ArduinoJson
GFX     := $(DEPS)/Adafruit-GFX-Library

JSON_TAG := v7.4.2
GFX_TAG  := 1.12.6

CXX      ?= g++
CXXFLAGS := -std=c++17 -O1 -g -Wall -Wextra -Wno-unused-parameter -Wno-missing-field-initializers -Wno-maybe-uninitialized \
            -DARDUINO=10819 -DHOST_BUILD \
            -DARDUINOJSON_ENABLE_ARDUINO_STRING=0 -DARDUINOJSON_ENABLE_ARDUINO_STREAM=0 \
            -DARDUINOJSON_ENABLE_ARDUINO_PRINT=0 -DARDUINOJSON_ENABLE_PROGMEM=0 \
            -Ishim -I$(SRC) -isystem $(JSON)/src -isystem $(GFX) \
            -DFIXTURES='"$(CURDIR)/fixtures"'
SANITIZE := -fsanitize=address,undefined -fno-omit-frame-pointer

CORE := $(SRC)/FlightParser.cpp $(SRC)/Format.cpp $(SRC)/AircraftNames.cpp $(SRC)/Airlines.cpp \
        $(SRC)/Settings.cpp $(SRC)/Sources.cpp
DRAW := $(SRC)/Render.cpp $(GFX)/Adafruit_GFX.cpp

.PHONY: test preview clean

test: build/tests
	./build/tests

preview: build/preview
	mkdir -p previews
	./build/preview previews
	python3 led_png.py previews

build/tests: tests.cpp $(CORE) $(wildcard $(SRC)/*.h) | $(JSON) build
	$(CXX) $(CXXFLAGS) $(SANITIZE) tests.cpp $(CORE) -o $@

build/preview: preview.cpp $(CORE) $(DRAW) $(wildcard $(SRC)/*.h) | $(JSON) build
	$(CXX) $(CXXFLAGS) $(SANITIZE) preview.cpp $(CORE) $(DRAW) -o $@

build:
	mkdir -p build

$(JSON):
	git -c advice.detachedHead=false clone -q --depth 1 --branch $(JSON_TAG) https://github.com/bblanchon/ArduinoJson.git $@

$(GFX)/Adafruit_GFX.cpp:
	git -c advice.detachedHead=false clone -q --depth 1 --branch $(GFX_TAG) https://github.com/adafruit/Adafruit-GFX-Library.git $(GFX)

clean:
	rm -rf build previews
