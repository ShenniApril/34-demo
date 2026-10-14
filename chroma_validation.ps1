$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $common = @('--preprocessor','preprocess.exe','--preprocessor-source','preprocess.cpp','--profiles','identity:0','chroma:4')
    & python benchmark_v5.py @common --out results/v6_full_x265 --frames 600 --preset medium --reuse-baseline results/full_x265
    if ($LASTEXITCODE -ne 0) { throw 'Chroma full HEVC failed' }
    & python benchmark_v5.py @common --out results/v6_holdout_x265 --start-frame 256 --frames 192 --preset medium --reuse-baseline results/holdout_x265
    if ($LASTEXITCODE -ne 0) { throw 'Chroma HEVC holdout failed' }
    & python benchmark_v5.py @common --out results/v6_foreman_x265 --input datasets/foreman_cif.yuv --width 352 --height 288 --fps 29.97002997002997 --frames 300 --preset medium --reuse-baseline results/foreman_x265
    if ($LASTEXITCODE -ne 0) { throw 'Chroma Foreman failed' }
    & python benchmark_v5.py @common --out results/v6_mobile_x265 --input datasets/mobile_cif.yuv --width 352 --height 288 --fps 29.97002997002997 --frames 300 --preset medium --reuse-baseline results/mobile_x265
    if ($LASTEXITCODE -ne 0) { throw 'Chroma Mobile failed' }
    foreach ($item in @('crowd_run_1080p50','ducks_take_off_1080p50')) {
        & python benchmark_v5.py @common --out "results/v6_$($item)_x265" --input "datasets/$($item)_prefix128.yuv" --width 1920 --height 1080 --fps 50 --frames 128 --preset medium --reuse-baseline "results/v4_$($item)_x265"
        if ($LASTEXITCODE -ne 0) { throw "Chroma HD failed: $item" }
    }
} finally { Pop-Location }
