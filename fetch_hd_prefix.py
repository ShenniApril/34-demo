"""Fetch continuous Y4M prefixes, without spatial/temporal resampling."""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'datasets'
def fetch(name,url,frames=128):
    out=ROOT/(name+'_prefix128.yuv');manifest=out.with_suffix('.json')
    if out.exists() and manifest.exists():return
    req=urllib.request.Request(url,headers={'Range':'bytes=0-403000000','User-Agent':'Video-preprocessing-research/1.0'})
    tmp=out.with_suffix('.partial')
    h=hashlib.sha256()
    with urllib.request.urlopen(req,timeout=45) as response:
        header=response.readline(4096).decode('ascii').strip()
        if not header.startswith('YUV4MPEG2 '):raise RuntimeError('Missing Y4M header')
        fields={s[0]:s[1:] for s in header.split()[1:]}
        w=int(fields['W']);height=int(fields['H']);fps=fields['F'];chroma=fields.get('C','420jpeg')
        if not chroma.startswith('420') or 'p10' in chroma or 'p12' in chroma:raise RuntimeError('Expected 8-bit 420 input')
        n=w*height*3//2
        with tmp.open('wb') as f:
            for i in range(frames):
                line=response.readline(4096)
                if not line.startswith(b'FRAME'):raise RuntimeError(f'Missing frame {i}')
                remaining=n
                while remaining:
                    data=response.read(min(remaining,1024*1024))
                    if not data:raise RuntimeError(f'Truncated frame {i}')
                    f.write(data);h.update(data);remaining-=len(data)
                if (i+1)%32==0:print(name,i+1,flush=True)
        status=response.status
    tmp.replace(out)
    manifest.write_text(json.dumps({'source_url':url,'source_page':'https://media.xiph.org/video/derf/','header':header,'width':w,'height':height,'fps_rational':fps,'frames':frames,'start_frame':0,'pix_fmt':'yuv420p','sha256':h.hexdigest(),'http_status':status,'extraction':'First 128 complete consecutive original frames; strip Y4M frame markers only, no resampling. Not the complete source sequence.','license_reference':'https://media.xiph.org/video/derf/vqeg.its.bldrdoc.gov/HDTV/SVT_MultiFormat/SVT_MultiFormat_v10.pdf'},indent=2))
    print('Saved',out.name,flush=True)

if __name__=='__main__':
    fetch('crowd_run_1080p50','https://media.xiph.org/video/derf/y4m/crowd_run_1080p50.y4m')
    fetch('ducks_take_off_1080p50','https://media.xiph.org/video/derf/y4m/ducks_take_off_1080p50.y4m')

