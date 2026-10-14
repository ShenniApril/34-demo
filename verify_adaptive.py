import json
import argparse
import subprocess
from pathlib import Path
import numpy as np

ap=argparse.ArgumentParser();ap.add_argument('--mode',default='adaptive');ap.add_argument('--exe',default='preprocess_adaptive.exe');ap.add_argument('--out',default='results/v3_correctness');args=ap.parse_args()
root=Path(__file__).resolve().parent;out=root/args.out;out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(341403);cases=0
for w,h in [(2,2),(16,16),(18,18),(34,26),(1920,1080)]:
    n=w*h*3//2
    src=rng.integers(0,256,n*2,dtype=np.uint8);src[:n]=128
    (out/'source.yuv').write_bytes(src.tobytes())
    for q in (0,25,26,51):
        result=subprocess.run([str(root/args.exe),'source.yuv','result.yuv',str(w),str(h),str(q),args.mode,'2'],cwd=out,capture_output=True)
        assert result.returncode==0,result.stderr
        dst=np.frombuffer((out/'result.yuv').read_bytes(),dtype=np.uint8)
        assert len(dst)==len(src) and np.array_equal(dst[:n],src[:n])
        assert np.max(np.abs(dst.astype(int)-src.astype(int)))<=1
        for t in range(2):
            y=src[t*n:t*n+w*h];d=dst[t*n:t*n+w*h]
            assert np.array_equal(d[(y<24)|(y>231)],y[(y<24)|(y>231)])
            assert np.array_equal(dst[t*n+w*h:(t+1)*n],src[t*n+w*h:(t+1)*n])
        cases+=1
(out/'verified.json').write_text(json.dumps({'cases':cases,'constant':True,'luma_max_delta':1,'chroma_unchanged':True,'shadows_highlights_unchanged':True,'complete_frames':True},indent=2))
print(cases,'adaptive invariants passed')
