"""Reproducible 8-bit YUV420P preprocessing RD evaluation (Python + SciPy).
No spatial scaling or temporal subsampling. All metrics reference original YUV.
"""
import argparse
import csv
import hashlib
import json
import math
import platform
import re
import subprocess
import time
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator

ROOT = Path(__file__).resolve().parent
FF = ROOT / 'ffmpeg-2026-10-12-git-615b07170e-full_build/bin/ffmpeg.exe'
PROBE = FF.with_name('ffprobe.exe')

def run(cmd, log):
    start = time.perf_counter()
    result = subprocess.run([str(x) for x in cmd], cwd=log.parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    wall = time.perf_counter() - start
    output = result.stdout.decode('utf-8', errors='replace') + result.stderr.decode('utf-8', errors='replace')
    log.write_text(output, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'Command failed; see {log}\n{output[-1800:]}')
    return wall, output

def bd_rate(base, opt, metric, method='pchip'):
    curves = []
    for rows in (base, opt):
        rows = sorted(rows, key=lambda r:r['bitrate'])
        q = np.array([r[metric] for r in rows])
        lr = np.log([r['bitrate'] for r in rows])
        if len(q)<4 or not np.all(np.isfinite(q)) or np.any(np.diff(q)<=0):
            raise ValueError(f'{metric}: need >=4 strictly increasing quality points (no silent sorting/pruning)')
        curves.append((q, lr))
    lo = max(c[0][0] for c in curves); hi = min(c[0][-1] for c in curves)
    if hi<=lo: raise ValueError('No overlapping quality interval')
    integrals=[]
    for q,lr in curves:
        if method=='pchip': integrals.append(PchipInterpolator(q,lr).integrate(lo,hi))
        else:
            p=np.polyint(np.polyfit(q,lr,3)); integrals.append(np.polyval(p,hi)-np.polyval(p,lo))
    return dict(percent=100*math.expm1((integrals[1]-integrals[0])/(hi-lo)), quality_min=float(lo), quality_max=float(hi))

def summarize(rows):
    base=[r for r in rows if r['profile']=='identity:0']
    results=[]
    for profile in sorted({r['profile'] for r in rows} - {'identity:0'}):
        opt=[r for r in rows if r['profile']==profile]
        entry={'profile':profile}
        for metric in ('psnr','psnr_y','vmaf','vmaf_neg'):
            for method in ('pchip','cubic'):
                try: entry[f'{metric}_{method}']=bd_rate(base,opt,metric,method)
                except ValueError as e: entry[f'{metric}_{method}']={'error':str(e)}
        ps=entry['psnr_pchip'].get('percent'); py=entry['psnr_y_pchip'].get('percent')
        vm=entry['vmaf_pchip'].get('percent')
        entry['passes_psnr_all']=ps is not None and ps<=0.3
        entry['passes_psnr_y']=py is not None and py<=0.3
        entry['vmaf_gain']=vm is not None and vm<0
        guards=[entry[f'{m}_{method}'].get('percent') for m in ('psnr','psnr_y') for method in ('pchip','cubic')]
        entry['psnr_worst_percent']=max(guards) if all(v is not None for v in guards) else None
        entry['passes_psnr_robust']=all(v is not None and v<=0.3 for v in guards)
        entry['eligible_gain']=entry['passes_psnr_robust'] and entry['vmaf_gain']
        entry['total_wall_change_percent']=100*(sum(r['encode_seconds']+r['preprocess_wall_seconds'] for r in opt)/sum(r['encode_seconds'] for r in base)-1)
        results.append(entry)
    return results

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',default='Beauty_1920x1080_120fps_420_8bit_YUV.yuv')
    ap.add_argument('--width',type=int,default=1920);ap.add_argument('--height',type=int,default=1080)
    ap.add_argument('--fps',type=float,default=120);ap.add_argument('--frames',type=int,default=64)
    ap.add_argument('--start-frame',type=int,default=0)
    ap.add_argument('--crfs','--points',dest='crfs',nargs='+',type=int,default=[22,26,30,34])
    ap.add_argument('--preprocess-crf',type=int,help='Explicit preprocessing hint; required for codecs whose quality parameter is not x26x CRF')
    ap.add_argument('--preprocessor',default='preprocess.exe')
    ap.add_argument('--preprocessor-source',default='preprocess.cpp')
    ap.add_argument('--profiles',nargs='+',default=['identity:0','guarded:2'])
    ap.add_argument('--codec',choices=['libx265','libx264','libsvtav1','libvvenc'],default='libx265')
    ap.add_argument('--preset',default='veryfast');ap.add_argument('--out',default='results/screen')
    ap.add_argument('--reuse-baseline',help='Reuse completed identity points with identical source/encoder/metric configuration')
    args=ap.parse_args()
    if args.width<=0 or args.height<=0 or args.width%2 or args.height%2 or args.frames<=0 or args.fps<=0 or args.start_frame<0: ap.error('Invalid input geometry/timing')
    maxq=51 if args.codec in ('libx264','libx265') else 63
    if len(set(args.crfs))<4 or any(q<0 or q>maxq for q in args.crfs): ap.error(f'Need >=4 distinct quality points in 0..{maxq}')
    if args.codec in ('libvvenc','libsvtav1') and args.preprocess_crf is None:ap.error('Specify --preprocess-crf 0..51 independently of encoder QP/CRF')
    if args.preprocess_crf is not None and not 0<=args.preprocess_crf<=51:ap.error('Invalid preprocessing hint')
    if 'identity:0' not in args.profiles: ap.error('Include identity:0 baseline')
    for p in args.profiles:
        m,a=p.split(':')
        if m not in ('identity','legacy','smooth','chroma','sharp','hybrid','perceptual','balanced','adaptive','context','content','guarded') or not 0<=int(a)<=16: ap.error('Invalid profile')
    inp=(ROOT/args.input).resolve(); out=(ROOT/args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    n=args.width*args.height*3//2
    if inp.stat().st_size%n or inp.stat().st_size<(args.start_frame+args.frames)*n: ap.error('Incomplete/insufficient raw input')
    ff_version=subprocess.check_output([str(FF),'-version']).decode(errors='replace').splitlines()[0]
    manifest={**vars(args),'input':str(inp),'input_size':inp.stat().st_size,'input_mtime_ns':inp.stat().st_mtime_ns,
              'ffmpeg':ff_version,'machine':platform.platform(),'processor':platform.processor(),
              'preprocess_sha256':hashlib.sha256((ROOT/args.preprocessor).read_bytes()).hexdigest(),
              'benchmark_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'metric_models':['vmaf_v0.6.1','vmaf_v0.6.1neg'],'threads':4,'gop':128 if args.codec=='libvvenc' else 120,
              'quality_mode':'qp' if args.codec=='libvvenc' else 'crf',
              'metric_pixel_format':'yuv420p',
              'vvc_conversion':'8->10 for both inputs; decoded 10->8 with bitexact, accurate_rnd, no dithering' if args.codec=='libvvenc' else None,
              'preprocess_source_sha256':hashlib.sha256((ROOT/args.preprocessor_source).read_bytes()).hexdigest()}
    mf=out/'manifest.json'
    if mf.exists() and json.loads(mf.read_text())!=manifest: raise RuntimeError('Manifest differs: choose a new --out directory')
    mf.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    ref=out/'reference.yuv'
    if not ref.exists():
        with inp.open('rb') as f, ref.open('wb') as g:
            f.seek(args.start_frame*n)
            for _ in range(args.frames): g.write(f.read(n))
    if ref.stat().st_size!=args.frames*n: raise RuntimeError('Reference length mismatch')
    conversion='scale=in_range=tv:out_range=tv:flags=bitexact+accurate_rnd:sws_dither=none'
    if args.codec=='libvvenc':
        # Validate conversion with all 256 codes before using this metric domain.
        ramp=out/'conversion_ramp.yuv';rt=out/'conversion_roundtrip.yuv'
        ramp.write_bytes(bytes(range(256))*6)
        run([FF,'-v','error','-y','-f','rawvideo','-pix_fmt','yuv420p','-s','32x32','-i',ramp.name,'-vf',f'{conversion},format=yuv420p10le,{conversion},format=yuv420p','-frames:v',1,'-f','rawvideo',rt.name],out/'conversion.log')
        if ramp.read_bytes()!=rt.read_bytes():raise RuntimeError('8/10-bit roundtrip is not exact')
    reused=None
    if args.reuse_baseline:
        reused=(ROOT/args.reuse_baseline).resolve()
        prior=json.loads((reused/'manifest.json').read_text(encoding='utf-8'))
        for key in ('input','input_size','input_mtime_ns','width','height','fps','frames','start_frame','crfs','codec','preset','ffmpeg','metric_models','threads','gop'):
            if prior[key]!=manifest[key]: raise RuntimeError(f'Baseline configuration mismatch: {key}')
        if args.preprocess_crf is not None or args.codec not in ('libx264','libx265'):raise RuntimeError('Cached v1 baselines only supported for unchanged x26x measurement protocol')
        def digest(path):
            h=hashlib.sha256()
            with path.open('rb') as f:
                for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
            return h.hexdigest()
        if digest(ref)!=digest(reused/'reference.yuv'): raise RuntimeError('Baseline reference mismatch')
    rows=[]
    for profile in args.profiles:
        mode,amount=profile.split(':')
        for crf in args.crfs:
            tag=f"{mode}{amount}_{manifest['quality_mode']}{crf}"; rowfile=out/f'{tag}.row.json'
            if rowfile.exists():
                rows.append(json.loads(rowfile.read_text()));print(f'resume {tag}',flush=True);continue
            if reused and mode=='identity':
                row=json.loads((reused/f'{tag}.row.json').read_text())
                if row['profile']!='identity:0' or row['crf']!=crf or row['frames']!=args.frames:raise RuntimeError('Invalid cached baseline row')
                row.update(quality_mode=manifest['quality_mode'],quality_value=crf,preprocess_crf=crf)
                rowfile.write_text(json.dumps(row,indent=2));rows.append(row)
                print(f'reuse baseline {tag} from {reused.name}',flush=True);continue
            pre_wall=compute=0.; source=ref
            if mode!='identity':
                source=out/'processed.yuv'
                pcrf=crf if args.preprocess_crf is None else args.preprocess_crf
                pre_wall,txt=run([ROOT/args.preprocessor,ref.name,source.name,args.width,args.height,pcrf,mode,amount,args.frames],out/f'{tag}.pre.log')
                compute=json.loads(txt)['compute_seconds']
            movie=out/f'{tag}.mp4'
            if args.codec=='libx265':params=['-crf',crf,'-x265-params','pools=4:frame-threads=1:keyint=120:min-keyint=120:scenecut=0:log-level=error']
            elif args.codec=='libx264':params=['-crf',crf,'-x264-params','threads=4:keyint=120:min-keyint=120:scenecut=0']
            elif args.codec=='libsvtav1':params=['-crf',crf,'-g',120,'-svtav1-params','lp=4:film-grain=0']
            else:params=['-vf',f'{conversion},format=yuv420p10le','-pix_fmt','yuv420p10le','-qp',crf,'-qpa',1,'-period',1,'-vvenc-params','Threads=4:IntraPeriod=128:GOPSize=32']
            command=[FF,'-hide_banner','-y','-nostdin','-f','rawvideo','-pix_fmt','yuv420p','-s',f'{args.width}x{args.height}','-r',args.fps,'-i',source.name,'-frames:v',args.frames,'-an','-c:v',args.codec,'-preset',args.preset,'-threads','4',*params,movie.name]
            (out/f'{tag}.encode.command.json').write_text(json.dumps(list(map(str,command)),indent=2))
            enc,_=run(command,out/f'{tag}.encode.log')
            packet=json.loads(subprocess.check_output([str(PROBE),'-v','error','-select_streams','v:0','-show_entries','packet=size','-show_entries','stream=nb_frames,width,height,avg_frame_rate','-of','json',str(movie)]))
            stream=packet['streams'][0]
            if int(stream['nb_frames'])!=args.frames or int(stream['width'])!=args.width or int(stream['height'])!=args.height:raise RuntimeError('Encoded geometry/frame count mismatch')
            num,den=map(int,stream['avg_frame_rate'].split('/'))
            if abs(num/den-args.fps)>1e-6:raise RuntimeError('Encoded FPS mismatch')
            bitrate=sum(int(p['size']) for p in packet['packets'])*8*args.fps/args.frames
            normalize=f'{conversion},format=yuv420p,' if args.codec=='libvvenc' else ''
            graph=f"[0:v]{normalize}settb=AVTB,setpts=PTS-STARTPTS,split=2[d1][d2];[1:v]settb=AVTB,setpts=PTS-STARTPTS,split=2[r1][r2];[d1][r1]psnr=stats_file={tag}.psnr.log:shortest=1[p];[d2][r2]libvmaf=model='version=vmaf_v0.6.1\\:name=vmaf|version=vmaf_v0.6.1neg\\:name=vmaf_neg':log_fmt=json:log_path={tag}.vmaf.json:n_threads=4:shortest=1[v]"
            _,txt=run([FF,'-hide_banner','-nostdin','-threads','4','-i',movie.name,'-f','rawvideo','-pixel_format','yuv420p','-video_size',f'{args.width}x{args.height}','-framerate',args.fps,'-i',ref.name,'-filter_complex',graph,'-map','[p]','-map','[v]','-f','null','-'],out/f'{tag}.metrics.log')
            match=re.search(r'PSNR y:([\d.]+) u:([\d.]+) v:([\d.]+) average:([\d.]+)',txt)
            if not match: raise RuntimeError('Missing PSNR summary')
            vj=json.loads((out/f'{tag}.vmaf.json').read_text())
            if len(vj['frames'])!=args.frames or len((out/f'{tag}.psnr.log').read_text().splitlines())!=args.frames: raise RuntimeError('Metric frame count mismatch')
            row={'profile':profile,'crf':crf,'bitrate':bitrate,'psnr_y':float(match[1]),'psnr':float(match[4]),
                 'vmaf':vj['pooled_metrics']['vmaf']['mean'],'vmaf_neg':vj['pooled_metrics']['vmaf_neg']['mean'],
                 'encode_seconds':enc,'preprocess_compute_seconds':compute,'preprocess_wall_seconds':pre_wall,'frames':args.frames,
                 'quality_mode':manifest['quality_mode'],'quality_value':crf,'preprocess_crf':crf if args.preprocess_crf is None else args.preprocess_crf}
            rowfile.write_text(json.dumps(row,indent=2));rows.append(row)
            with (out/'points.csv').open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerows(rows)
            print(f'{tag}: {bitrate/1000:.1f}kbps PSNR={row["psnr"]:.4f} VMAF={row["vmaf"]:.3f} enc={enc:.2f}s',flush=True)
    summary=summarize(rows)
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__': main()
