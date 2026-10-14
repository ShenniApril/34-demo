import json
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parent;result={}
for name,path,w,h,frames in [('Beauty',root/'Beauty_1920x1080_120fps_420_8bit_YUV.yuv',1920,1080,600),('Foreman',root/'datasets/foreman_cif.yuv',352,288,300),('Mobile',root/'datasets/mobile_cif.yuv',352,288,300)]:
    means=[]
    with path.open('rb') as f:
        for t in range(frames):
            f.seek(t*w*h*3//2);y=np.frombuffer(f.read(w*h),dtype=np.uint8).reshape(h,w).astype(np.int16)
            g=np.abs(y[1:h-1:4,0:w-2:4]-y[1:h-1:4,2:w:4])+np.abs(y[0:h-2:4,1:w-1:4]-y[2:h:4,1:w-1:4])
            means.append(float(g.mean()))
    a=np.array(means)
    result[name]={'min':float(a.min()),'max':float(a.max()),'below9':int((a<9).sum()),'below12':int((a<12).sum()),'atleast40':int((a>=40).sum()),'frames':frames,'means':means}
(root/'results/context_features_all_frames.json').write_text(json.dumps(result,indent=2))
print({k:{x:v for x,v in d.items() if x!='means'} for k,d in result.items()})
