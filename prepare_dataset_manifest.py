import hashlib
import json
import subprocess
from pathlib import Path
from benchmark import PROBE

root=Path(__file__).resolve().parent
rows=[]
for name in ('foreman_cif','mobile_cif'):
    path=root/'datasets'/(name+'.y4m');raw=path.with_suffix('.yuv')
    info=json.loads(subprocess.check_output([str(PROBE),'-v','error','-show_entries','stream=width,height,pix_fmt,r_frame_rate','-of','json',str(path)]))['streams'][0]
    n=info['width']*info['height']*3//2
    assert info['pix_fmt']=='yuv420p' and raw.stat().st_size%n==0
    rows.append({'name':name,'source_url':'https://media.xiph.org/video/derf/y4m/'+name+'.y4m','source_page':'https://media.xiph.org/video/derf/',
                 **info,'frames':raw.stat().st_size//n,'download_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
                 'conversion':'FFmpeg -c:v copy -f rawvideo (strip Y4M container; no resampling)',
                 'notice':'Xiph lists publicly hosted sequences believed freely redistributable, subject to original restrictions. Some source FPS values may be inferred; this experiment follows the Y4M header. Not a guaranteed license for every use.'})
(root/'datasets/manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
