$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & python benchmark_v3.py --out results/v3_holdout_x265 --start-frame 256 --frames 192 --preset medium --profiles identity:0 adaptive:2 --reuse-baseline results/holdout_x265
    if ($LASTEXITCODE -ne 0) { throw 'Adaptive HEVC holdout failed' }
    & python benchmark_v3.py --out results/v3_foreman_x265 --input datasets/foreman_cif.yuv --width 352 --height 288 --fps 29.97002997002997 --frames 300 --preset medium --profiles identity:0 adaptive:2 --reuse-baseline results/foreman_x265
    if ($LASTEXITCODE -ne 0) { throw 'Adaptive Foreman failed' }
    & python benchmark_v3.py --out results/v3_mobile_x265 --input datasets/mobile_cif.yuv --width 352 --height 288 --fps 29.97002997002997 --frames 300 --preset medium --profiles identity:0 adaptive:2 --reuse-baseline results/mobile_x265
    if ($LASTEXITCODE -ne 0) { throw 'Adaptive Mobile failed' }
    & python benchmark_v3.py --out results/v3_full_x265 --frames 600 --preset medium --profiles identity:0 adaptive:2 --reuse-baseline results/full_x265
    if ($LASTEXITCODE -ne 0) { throw 'Adaptive full HEVC failed' }
    & python benchmark_v3.py --out results/v3_holdout_x264 --codec libx264 --preset medium --start-frame 256 --frames 192 --profiles identity:0 adaptive:2 --reuse-baseline results/holdout_x264
    if ($LASTEXITCODE -ne 0) { throw 'Adaptive AVC failed' }
    & python benchmark_v3.py --out results/v3_screen_av1 --codec libsvtav1 --preset 8 --points 24 30 36 42 --preprocess-crf 28 --profiles identity:0 adaptive:2
    if ($LASTEXITCODE -ne 0) { throw 'Adaptive AV1 failed' }
    & python benchmark_v3.py --out results/v3_screen_vvc --codec libvvenc --preset faster --points 22 27 32 37 --preprocess-crf 28 --profiles identity:0 adaptive:2
    if ($LASTEXITCODE -ne 0) { throw 'Adaptive VVC failed' }
} finally { Pop-Location }
