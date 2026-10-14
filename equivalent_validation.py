"""Reuse quality only after hashing every processed byte at every quality point.
No inference from selected frames; borrowed encoder timings are explicitly marked.
"""
import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path
from benchmark_v5 import ROOT,run,summarize

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(8*1024*1024),b''):h.update(data)
    return h.hexdigest()

def reuse(oldfolder,profile,newfolder,oldexe,target_mode='content',target_exe='preprocess_content.exe',target_source='preprocess_content.cpp'):
    source=ROOT/'results'/oldfolder;out=ROOT/'results'/newfolder;out.mkdir(parents=True,exist_ok=True)
    mf=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    executable=ROOT/oldexe
    if digest(executable)!=mf['preprocess_sha256']:raise RuntimeError('Original preprocessor binary hash differs')
    om,oa=profile.split(':');rows=[];proof=[]
    quality_mode=mf.get('quality_mode','crf')
    for point in mf['crfs']:
        oldtag=f'{om}{oa}_{quality_mode}{point}'
        # v2 filenames retained the legacy crf label, including the VVC smoke path.
        rowpath=source/(oldtag+'.row.json')
        if not rowpath.exists():rowpath=source/f'{om}{oa}_crf{point}.row.json'
        baseline=source/f'identity0_{quality_mode}{point}.row.json'
        if not baseline.exists():baseline=source/f'identity0_crf{point}.row.json'
        base=json.loads(baseline.read_text());rows.append(base)
        pp=point if mf.get('preprocess_crf') is None else mf['preprocess_crf']
        candidate=out/'candidate.yuv';reference=out/'old_processed.yuv'
        pre,txt=run([ROOT/target_exe,'reference.yuv',os.path.relpath(candidate,source),mf['width'],mf['height'],pp,target_mode,2,mf['frames']],source/f'{target_mode}_equivalence_{point}.log')
        run([executable,'reference.yuv',os.path.relpath(reference,source),mf['width'],mf['height'],pp,om,oa,mf['frames']],source/f'old_equivalence_{point}.log')
        h1=digest(candidate);h2=digest(reference)
        if h1!=h2:raise RuntimeError(f'Processed bytes differ: {newfolder} point {point}; use fresh encoding')
        row=json.loads(rowpath.read_text());row.update(profile=target_mode+':2',preprocess_compute_seconds=json.loads(txt)['compute_seconds'],preprocess_wall_seconds=pre)
        rows.append(row)
        (out/f'{target_mode}2_{quality_mode}{point}.row.json').write_text(json.dumps(row,indent=2))
        (out/f'identity0_{quality_mode}{point}.row.json').write_text(json.dumps(base,indent=2))
        movie=source/(rowpath.name.removesuffix('.row.json')+'.mp4')
        proof.append({'point':point,'preprocess_crf':pp,'bytes':candidate.stat().st_size,'candidate_sha256':h1,'original_processed_sha256':h2,'equal':True,'original_row':str(rowpath),'original_movie_sha256':digest(movie)})
        print(newfolder,point,'all processed bytes equal',flush=True)
    mf.update(profiles=['identity:0',target_mode+':2'],out=str(out.relative_to(ROOT)),preprocessor=target_exe,preprocessor_source=target_source,preprocess_sha256=digest(ROOT/target_exe),preprocess_source_sha256=digest(ROOT/target_source),benchmark_sha256=digest(Path(__file__)),reuse_baseline=oldfolder,quality_reused_from=oldfolder,quality_reused_profile=profile,encoding_reused=True)
    (out/'manifest.json').write_text(json.dumps(mf,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'equivalence.json').write_text(json.dumps(proof,indent=2))
    with (out/'points.csv').open('w',newline='') as f:
        fields=sorted(set().union(*(r.keys() for r in rows)))
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(summarize(rows),indent=2))

if __name__=='__main__':
    reuse('v2_holdout_x265','balanced:2','v5_holdout_x265','results/code_snapshots/preprocess_scalar_v2.exe')
    reuse('v2_full_x265','balanced:2','v5_full_x265','results/code_snapshots/preprocess_scalar_v2.exe')
    reuse('v3_foreman_x265','adaptive:2','v5_foreman_x265','preprocess_adaptive.exe')
    reuse('v3_mobile_x265','adaptive:2','v5_mobile_x265','preprocess_adaptive.exe')
    for codec in ('x264','av1','vvc'):
        reuse('v4_holdout_'+codec,'context:2','v5_holdout_'+codec,'preprocess_context.exe')
