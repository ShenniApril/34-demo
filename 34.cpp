#include <algorithm>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

namespace {

// Lightweight edge-aware denoising for one 8-bit image plane.
// Flat areas are smoothed; strong edges and textures are kept unchanged.
void processPlane(const uint8_t* src, uint8_t* dst, int width, int height,
                  int strength, int edgeThreshold) {
    const std::size_t planeBytes =
        static_cast<std::size_t>(width) * static_cast<std::size_t>(height);
    std::copy(src, src + planeBytes, dst);

    if (width < 3 || height < 3 || strength <= 0) {
        return;
    }

    for (int y = 1; y < height - 1; ++y) {
        for (int x = 1; x < width - 1; ++x) {
            const int p = y * width + x;
            const int center = src[p];
            const int gx = std::abs(static_cast<int>(src[p + 1]) -
                                    static_cast<int>(src[p - 1]));
            const int gy = std::abs(static_cast<int>(src[p + width]) -
                                    static_cast<int>(src[p - width]));
            if (gx + gy >= edgeThreshold) {
                continue;
            }

            int sum = center * 4;
            int weight = 4;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    if (dx == 0 && dy == 0) {
                        continue;
                    }
                    const int value = src[p + dy * width + dx];
                    if (std::abs(value - center) <= strength) {
                        sum += value;
                        ++weight;
                    }
                }
            }
            dst[p] = static_cast<uint8_t>((sum + weight / 2) / weight);
        }
    }
}

bool parsePositiveInt(const char* text, int& value) {
    try {
        std::size_t used = 0;
        const long parsed = std::stol(text, &used);
        if (text[used] != '\0' || parsed <= 0 ||
            parsed > std::numeric_limits<int>::max()) {
            return false;
        }
        value = static_cast<int>(parsed);
        return true;
    } catch (...) {
        return false;
    }
}

}  // namespace

// Both buffers contain one complete 8-bit planar YUV420P frame:
// Y plane, followed by U and V planes.
void processYUVFrame(const uint8_t* src, uint8_t* dst, int width, int height,
                     int crf) {
    const std::size_t yBytes =
        static_cast<std::size_t>(width) * static_cast<std::size_t>(height);
    const int chromaWidth = width / 2;
    const int chromaHeight = height / 2;
    const std::size_t chromaBytes = yBytes / 4;

    // Higher CRF permits slightly stronger preprocessing. These values stay
    // conservative because excessive smoothing hurts PSNR and VMAF.
    const int clampedCrf = std::clamp(crf, 0, 51);
    const int lumaStrength = 3 + clampedCrf / 6;
    const int lumaEdgeThreshold = 18 + clampedCrf / 2;
    const int chromaStrength = lumaStrength + 3;
    const int chromaEdgeThreshold = lumaEdgeThreshold + 8;

    processPlane(src, dst, width, height, lumaStrength, lumaEdgeThreshold);
    processPlane(src + yBytes, dst + yBytes, chromaWidth, chromaHeight,
                 chromaStrength, chromaEdgeThreshold);
    processPlane(src + yBytes + chromaBytes,
                 dst + yBytes + chromaBytes, chromaWidth, chromaHeight,
                 chromaStrength, chromaEdgeThreshold);
}

int main(int argc, char* argv[]) {
    if (argc != 5 && argc != 6) {
        std::cerr << "Usage: " << argv[0]
                  << " <input.yuv> <output.yuv> <width> <height> [crf]\n"
                  << "Input format: 8-bit planar YUV420P; default CRF: 28\n";
        return 1;
    }

    int width = 0;
    int height = 0;
    int crf = 28;
    if (!parsePositiveInt(argv[3], width) ||
        !parsePositiveInt(argv[4], height) ||
        (argc == 6 && !parsePositiveInt(argv[5], crf))) {
        std::cerr << "Width, height and CRF must be positive integers.\n";
        return 1;
    }
    if ((width & 1) != 0 || (height & 1) != 0) {
        std::cerr << "YUV420P requires even width and height.\n";
        return 1;
    }
    if (crf > 51) {
        std::cerr << "CRF must be in the range 1..51.\n";
        return 1;
    }

    std::ifstream input(argv[1], std::ios::binary);
    if (!input) {
        std::cerr << "Cannot open input file: " << argv[1] << '\n';
        return 1;
    }
    std::ofstream output(argv[2], std::ios::binary);
    if (!output) {
        std::cerr << "Cannot open output file: " << argv[2] << '\n';
        return 1;
    }

    const std::size_t pixels =
        static_cast<std::size_t>(width) * static_cast<std::size_t>(height);
    if (pixels > std::numeric_limits<std::size_t>::max() / 2) {
        std::cerr << "Frame dimensions are too large.\n";
        return 1;
    }
    const std::size_t frameBytes = pixels + pixels / 2;
    std::vector<uint8_t> src(frameBytes);
    std::vector<uint8_t> dst(frameBytes);

    std::size_t frameCount = 0;
    const auto start = std::chrono::steady_clock::now();
    while (input.read(reinterpret_cast<char*>(src.data()),
                      static_cast<std::streamsize>(frameBytes))) {
        processYUVFrame(src.data(), dst.data(), width, height, crf);
        output.write(reinterpret_cast<const char*>(dst.data()),
                     static_cast<std::streamsize>(frameBytes));
        if (!output) {
            std::cerr << "Failed while writing output file.\n";
            return 1;
        }
        ++frameCount;
    }

    if (input.gcount() != 0) {
        std::cerr << "Input ends with an incomplete YUV420P frame ("
                  << input.gcount() << " trailing bytes).\n";
        return 1;
    }

    const auto end = std::chrono::steady_clock::now();
    const double seconds =
        std::chrono::duration<double>(end - start).count();
    const double fps = seconds > 0.0 ? frameCount / seconds : 0.0;

    std::cout << "Processed " << frameCount << " frame(s), " << frameBytes
              << " bytes/frame, " << seconds << " s, " << fps << " fps\n";
    return 0;
}
