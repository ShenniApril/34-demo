$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & python verify_final_simd.py
    if ($LASTEXITCODE -ne 0) { throw 'Final guarded SIMD check failed' }
    & python guarded_validation.py
    if ($LASTEXITCODE -ne 0) { throw 'Guarded regression equivalence failed' }
    foreach ($item in @('crowd_run_1080p50','ducks_take_off_1080p50')) {
        & python benchmark_v6.py --out "results/v7_$($item)_x265" --input "datasets/$($item)_prefix128.yuv" --width 1920 --height 1080 --fps 50 --frames 128 --preset medium --reuse-baseline "results/v4_$($item)_x265"
        if ($LASTEXITCODE -ne 0) { throw "Guarded HD failed: $item" }
    }
} finally { Pop-Location }
