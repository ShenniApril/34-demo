$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & g++ -O3 -std=c++17 -DNOMINMAX -fopenmp preprocess.cpp -o preprocess.exe
    if ($LASTEXITCODE -ne 0) { throw 'C++ build failed' }
    & g++ -O3 -std=c++17 -DNOMINMAX -fopenmp -DPREPROCESS_LIBRARY preprocess.cpp interface_test.cpp -o interface_test.exe
    if ($LASTEXITCODE -ne 0) { throw 'Interface check build failed' }
    & .\interface_test.exe
    if ($LASTEXITCODE -ne 0) { throw 'Interface checks failed' }
    & python verify_preprocess.py
    if ($LASTEXITCODE -ne 0) { throw 'Correctness checks failed' }
} finally { Pop-Location }
