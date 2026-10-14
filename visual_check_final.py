import subprocess
from pathlib import Path
from benchmark_v6 import ROOT,FF

out=ROOT/'results/visual_check_final';out.mkdir(parents=True,exist_ok=True)
def extract(label,path,raw=False,fps=120):
    args=[str(FF),'-v','error','-nostdin','-y']
    if raw:args+=['-f','rawvideo','-pix_fmt','yuv420p','-s','1920x1080','-r',str(fps)]
    args+=['-i',str(path),'-vf',r'select=eq(n\,64),format=rgb24','-frames:v','1','-update','1',str(out/(label+'.png'))]
    subprocess.run(args,check=True)

extract('beauty_reference',ROOT/'results/holdout_x265/reference.yuv',True)
extract('av1_hybrid',ROOT/'results/v4_holdout_av1/hybrid2_crf30.mp4')
extract('vvc_perceptual',ROOT/'results/v4_holdout_vvc/perceptual2_qp27.mp4')
extract('ducks_reference',ROOT/'datasets/ducks_take_off_1080p50_prefix128.yuv',True,50)
extract('ducks_guarded',ROOT/'results/v7_ducks_take_off_1080p50_x265/guarded2_crf26.mp4')
print('Five aligned frames extracted for inspection.')
