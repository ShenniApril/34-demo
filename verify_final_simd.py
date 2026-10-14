import json
import subprocess
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent;out=root/'results/final_simd_check';out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(341405);cases=0
for w,h in [(2,2),(18,18),(34,26),(1920,1080)]:
    n=w*h*3//2
    src=rng.integers(0,256,n*2,dtype=np.uint8)
    src[:n]=rng.integers(110,130,n,dtype=np.uint8) # smooth eligible, including ties
    (out/'source.yuv').write_bytes(src.tobytes())
    for mode in ('smooth','chroma','hybrid','perceptual','balanced','adaptive','context','content','guarded'):
        for amount,q in [(1,0),(2,25),(4,26),(16,51)]:
            for exe,target in [('preprocess_scalar.exe','scalar.yuv'),('preprocess.exe','simd.yuv')]:
                p=subprocess.run([str(root/exe),'source.yuv',target,str(w),str(h),str(q),mode,str(amount)],cwd=out,capture_output=True)
                assert p.returncode==0,p.stderr
            assert (out/'scalar.yuv').read_bytes()==(out/'simd.yuv').read_bytes(),(w,h,mode,amount,q)
            cases+=1
(out/'verified.json').write_text(json.dumps({'cases':cases,'bit_exact':True,'includes_rounding_and_clipping':True,'includes_odd_chroma_planes_and_1080p':True},indent=2))
print(cases,'final scalar/SIMD cases passed')
