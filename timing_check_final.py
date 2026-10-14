import json
import statistics
from benchmark_v6 import ROOT,FF,run

out=ROOT/'results/v7_timing';out.mkdir(parents=True,exist_ok=True)
src=ROOT/'results/holdout_x265/reference.yuv'
(out/'reference.yuv').write_bytes(src.read_bytes())
rows=[]
for repeat in range(3):
    for mode in (['identity','guarded'] if repeat%2==0 else ['guarded','identity']):
        tag=f'{repeat}_{mode}';pre=compute=0.;source='reference.yuv'
        if mode=='guarded':
            source='processed.yuv'
            pre,txt=run([ROOT/'preprocess.exe','reference.yuv',source,1920,1080,26,'guarded',2,192],out/(tag+'.pre.log'))
            compute=json.loads(txt)['compute_seconds']
        enc,_=run([FF,'-hide_banner','-nostdin','-y','-f','rawvideo','-pix_fmt','yuv420p','-s','1920x1080','-r',120,'-i',source,'-frames:v',192,'-an','-c:v','libx265','-preset','medium','-crf',26,'-threads',4,'-x265-params','pools=4:frame-threads=1:keyint=120:min-keyint=120:scenecut=0:log-level=error',tag+'.mp4'],out/(tag+'.encode.log'))
        rows.append({'repeat':repeat,'mode':mode,'preprocess_wall_seconds':pre,'preprocess_compute_seconds':compute,'encode_seconds':enc,'total_seconds':pre+enc})
        print(tag,round(pre+enc,3),flush=True)
base=[r['total_seconds'] for r in rows if r['mode']=='identity'];opt=[r['total_seconds'] for r in rows if r['mode']=='guarded']
report={'source':'Beauty frames 256..447, 1080p120','codec':'libx265','preset':'medium','crf':26,'profile':'guarded:2','repeats':rows,'median_total_change_percent':100*(statistics.median(opt)/statistics.median(base)-1),'baseline_range_seconds':[min(base),max(base)],'opt_range_seconds':[min(opt),max(opt)],'median_kernel_seconds':statistics.median(r['preprocess_compute_seconds'] for r in rows if r['mode']=='guarded'),'notice':'Three alternating trials after other encoding/download jobs completed. Includes startup and file I/O; one content and CRF, not official in-memory timing.'}
(out/'summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
