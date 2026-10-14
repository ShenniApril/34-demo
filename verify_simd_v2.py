import json
import subprocess
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent
tmp=root/'results/v2_simd_check';tmp.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(3414);count=0
for w,h in [(2,2),(16,16),(18,10),(34,18),(1920,1080)]:
    n=w*h*3//2
    raw=rng.integers(0,256,n*2,dtype=np.uint8)
    # Low activity structures exercise the adaptive branches, unlike only random pixels.
    y=np.fromfunction(lambda y,x: 64+(x%16)+(y%8),(h,w)).astype(np.uint8)
    y[2::5,2::5]+=4;raw[:w*h]=y.ravel()
    (tmp/'input.yuv').write_bytes(raw.tobytes())
    for mode in ('perceptual','balanced'):
        for amount in (1,2,4,16):
            for q in (0,25,26,51):
                for exe,output in [('preprocess.exe','scalar.yuv'),('preprocess_simd_v2.exe','simd.yuv')]:
                    p=subprocess.run([str(root/exe),'input.yuv',output,str(w),str(h),str(q),mode,str(amount)],cwd=tmp,capture_output=True)
                    assert p.returncode==0,p.stderr
                assert (tmp/'scalar.yuv').read_bytes()==(tmp/'simd.yuv').read_bytes(),(w,h,mode,amount,q)
                count+=1
(tmp/'verified.json').write_text(json.dumps({'cases':count,'bit_exact':True,'modes':['perceptual','balanced'],'crfs':[0,25,26,51],'amounts':[1,2,4,16],'includes_low_activity_and_1080p':True},indent=2))
print(count,'scalar/SIMD cases passed')
