"""Compare runtime AVX2 implementation against scalar on adversarial geometry."""
import subprocess
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent
tmp=root/'results/simd_check';tmp.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(3402)
cases=0
for w,h in [(2,2),(16,16),(18,10),(32,18),(34,10),(1920,1080)]:
    n=w*h*3//2
    src=rng.integers(0,256,n*2,dtype=np.uint8)
    (tmp/'input.yuv').write_bytes(src.tobytes())
    for mode in ('sharp','hybrid'):
        for amount in range(1,17):
            for name in ('preprocess','preprocess_simd'):
                result=subprocess.run([str(root/(name+'.exe')),'input.yuv',name+'.yuv',str(w),str(h),'28',mode,str(amount)],cwd=tmp,capture_output=True)
                assert not result.returncode,result.stderr
            assert (tmp/'preprocess.yuv').read_bytes()==(tmp/'preprocess_simd.yuv').read_bytes(),(w,h,mode,amount)
            cases+=1
(tmp/'verified.txt').write_text(f'{cases} scalar/AVX2 bit-exact cases passed. Includes SIMD boundary tails, extrema, and 1080p.\n')
print((tmp/'verified.txt').read_text())
