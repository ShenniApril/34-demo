#pragma once
#include <cstdint>

// Planar 8-bit YUV420P, even dimensions. src/dst may alias.
// Default is identity until a profile is validated on held-out content.
void processYUVFrame(const uint8_t* src, uint8_t* dst, int width, int height, int crf);
void configurePreprocess(const char* mode, int amount);
