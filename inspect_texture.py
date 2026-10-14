"""Measure unlabeled input texture features used by candidate gates."""
import json
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent;result={}
for name,path,w,h,frames in [
    ('Beauty',root/'Beauty_1920x1080_120fps_420_8bit_YUV.yuv',1920,1080,[0,256,300,447,599]),
    ('Foreman',root/'datasets/foreman_cif.yuv',352,288,[0,149,299]),
    ('Mobile',root/'datasets/mobile_cif.yuv',352,288,[0,149,299])]:
    rows=[]
    with path.open('rb') as f:
        for t in frames:
            f.seek(t*w*h*3//2);y=np.frombuffer(f.read(w*h),dtype=np.uint8).reshape(h,w).astype(np.int16)
            g=np.zeros((h,w),dtype=np.int16)
            g[1:-1,1:-1]=np.abs(y[1:-1,:-2]-y[1:-1,2:])+np.abs(y[:-2,1:-1]-y[2:,1:-1])
            dense=tiles=0
            for by in range(0,h,16):
                for bx in range(0,w,16):
                    a=g[max(by,1):min(by+16,h-1):2,max(bx,1):min(bx+16,w-1):2]
                    if not a.size:continue
                    dense+=a.mean()>=12 or np.mean(a>=32)>=.25;tiles+=1
            rows.append({'frame':t,'mean_gradient':float(g.mean()),'strong_fraction':float(np.mean(g>=32)),'dense_tile_fraction':dense/tiles})
    result[name]=rows
(root/'results/texture_features.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
