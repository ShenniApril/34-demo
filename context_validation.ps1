$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & python benchmark_v4.py --out results/v4_holdout_x265 --start-frame 256 --frames 192 --preset medium --reuse-baseline results/holdout_x265
    if ($LASTEXITCODE -ne 0) { throw 'Context HEVC holdout failed' }
    & python benchmark_v4.py --out results/v4_foreman_x265 --input datasets/foreman_cif.yuv --width 352 --height 288 --fps 29.97002997002997 --frames 300 --preset medium --reuse-baseline results/foreman_x265
    if ($LASTEXITCODE -ne 0) { throw 'Context Foreman failed' }
    & python benchmark_v4.py --out results/v4_mobile_x265 --input datasets/mobile_cif.yuv --width 352 --height 288 --fps 29.97002997002997 --frames 300 --preset medium --reuse-baseline results/mobile_x265
    if ($LASTEXITCODE -ne 0) { throw 'Context Mobile failed' }
    & python benchmark_v4.py --out results/v4_full_x265 --frames 600 --preset medium --reuse-baseline results/full_x265
    if ($LASTEXITCODE -ne 0) { throw 'Context full HEVC failed' }
    & python benchmark_v4.py --out results/v4_holdout_x264 --codec libx264 --preset medium --start-frame 256 --frames 192 --reuse-baseline results/holdout_x264
    if ($LASTEXITCODE -ne 0) { throw 'Context AVC failed' }
    & python benchmark_v4.py --out results/v4_holdout_av1 --codec libsvtav1 --preset 8 --start-frame 256 --frames 192 --points 24 30 36 42 --preprocess-crf 28 --profiles identity:0 hybrid:2 perceptual:2 context:2
    if ($LASTEXITCODE -ne 0) { throw 'AV1 longer validation failed' }
    & python benchmark_v4.py --out results/v4_holdout_vvc --codec libvvenc --preset faster --start-frame 256 --frames 192 --points 22 27 32 37 --preprocess-crf 28 --profiles identity:0 perceptual:2 context:2
    if ($LASTEXITCODE -ne 0) { throw 'VVC longer validation failed' }
    foreach ($item in @('crowd_run_1080p50','ducks_take_off_1080p50')) {
        if (-not (Test-Path -LiteralPath "datasets/$($item)_prefix128.json")) { throw "HD prefix not ready: $item" }
        & python benchmark_v4.py --out "results/v4_$($item)_x265" --input "datasets/$($item)_prefix128.yuv" --width 1920 --height 1080 --fps 50 --frames 128 --preset medium --profiles identity:0 sharp:1 balanced:2 context:2
        if ($LASTEXITCODE -ne 0) { throw "HD validation failed: $item" }
    }
} finally { Pop-Location }
