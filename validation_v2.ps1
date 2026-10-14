$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & python benchmark_v2.py --out results/v2_full_x265 --frames 600 --preset medium --profiles identity:0 sharp:1 balanced:2 --reuse-baseline results/full_x265
    if ($LASTEXITCODE -ne 0) { throw 'Full HEVC validation failed' }
    & python benchmark_v2.py --out results/v2_foreman_x265 --input datasets/foreman_cif.yuv --width 352 --height 288 --fps 29.97002997002997 --frames 300 --preset medium --profiles identity:0 sharp:1 perceptual:2 balanced:2 --reuse-baseline results/foreman_x265
    if ($LASTEXITCODE -ne 0) { throw 'Foreman validation failed' }
    & python benchmark_v2.py --out results/v2_mobile_x265 --input datasets/mobile_cif.yuv --width 352 --height 288 --fps 29.97002997002997 --frames 300 --preset medium --profiles identity:0 sharp:1 perceptual:2 balanced:2 --reuse-baseline results/mobile_x265
    if ($LASTEXITCODE -ne 0) { throw 'Mobile validation failed' }
    & python benchmark_v2.py --out results/v2_screen_x264 --codec libx264 --preset veryfast --profiles identity:0 legacy:16 smooth:4 chroma:4 sharp:1 hybrid:2 perceptual:2 balanced:2
    if ($LASTEXITCODE -ne 0) { throw 'AVC screening failed' }
    & python benchmark_v2.py --out results/v2_screen_av1 --codec libsvtav1 --preset 8 --points 24 30 36 42 --preprocess-crf 28 --profiles identity:0 legacy:16 smooth:4 chroma:4 sharp:1 hybrid:2 perceptual:2 balanced:2
    if ($LASTEXITCODE -ne 0) { throw 'AV1 screening failed' }
    & python benchmark_v2.py --out results/v2_screen_vvc --codec libvvenc --preset faster --points 22 27 32 37 --preprocess-crf 28 --profiles identity:0 legacy:16 smooth:4 chroma:4 sharp:1 hybrid:2 perceptual:2 balanced:2
    if ($LASTEXITCODE -ne 0) { throw 'VVC screening failed' }
    & python benchmark_v2.py --out results/v2_holdout_x264 --codec libx264 --preset medium --start-frame 256 --frames 192 --profiles identity:0 sharp:1 balanced:2 --reuse-baseline results/holdout_x264
    if ($LASTEXITCODE -ne 0) { throw 'AVC holdout validation failed' }
} finally { Pop-Location }
