"""Alternating repeated end-to-end timings, fixed source/config, without metrics."""
import json
import statistics
import subprocess
from pathlib import Path
from benchmark import FF, ROOT, run

def main():
    out=ROOT/'results/timing';out.mkdir(parents=True,exist_ok=True)
    ref=ROOT/'results/holdout_x265/reference.yuv'
    n=1920*1080*3//2
    with ref.open('rb') as f: (out/'reference.yuv').write_bytes(f.read(n*192))
    results=[]
    for repeat in range(3):
        for mode in (['identity','sharp'] if repeat%2==0 else ['sharp','identity']):
            tag=f'{repeat}_{mode}';pre=compute=0.;source='reference.yuv'
            if mode=='sharp':
                source='processed.yuv'
                pre,txt=run([ROOT/'preprocess.exe','reference.yuv',source,1920,1080,26,'sharp',1,192],out/(tag+'.pre.log'))
                compute=json.loads(txt)['compute_seconds']
            enc,_=run([FF,'-hide_banner','-nostdin','-y','-f','rawvideo','-pix_fmt','yuv420p','-s','1920x1080','-r',120,'-i',source,'-frames:v',192,'-an','-c:v','libx265','-preset','medium','-crf',26,'-threads',4,'-x265-params','pools=4:frame-threads=1:keyint=120:min-keyint=120:scenecut=0:log-level=error',tag+'.mp4'],out/(tag+'.encode.log'))
            results.append({'repeat':repeat,'mode':mode,'preprocess_wall_seconds':pre,'preprocess_compute_seconds':compute,'encode_seconds':enc,'total_seconds':pre+enc})
            print(tag,round(pre+enc,3),flush=True)
    base=[r['total_seconds'] for r in results if r['mode']=='identity'];opt=[r['total_seconds'] for r in results if r['mode']=='sharp']
    report={'source':'Beauty original frames 256..447, 1080p120','codec':'libx265','preset':'medium','crf':26,'gop':120,'threads':4,'profile':'sharp:1','repeats':results,
            'median_total_change_percent':100*(statistics.median(opt)/statistics.median(base)-1),'baseline_range_seconds':[min(base),max(base)],'opt_range_seconds':[min(opt),max(opt)],
            'notice':'Single source and CRF; three alternating trials. Includes process startup and file I/O; not official in-memory timing or full statistical confidence interval.'}
    (out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
