"""Small correctness checks plus analytical BD-Rate checks."""
import json
import subprocess
from pathlib import Path
import numpy as np
from benchmark import bd_rate

def main():
    root=Path(__file__).resolve().parent;tmp=root/'results/correctness';tmp.mkdir(parents=True,exist_ok=True)
    w=h=16;n=w*h*3//2
    rng=np.random.default_rng(34)
    frames=np.concatenate([np.full(n,127,dtype=np.uint8),rng.integers(0,256,n*3,dtype=np.uint8)])
    (tmp/'in.yuv').write_bytes(frames.tobytes())
    def run(mode,amount,src='in.yuv',dst='out.yuv',expect=0):
        p=subprocess.run([str(root/'preprocess.exe'),src,dst,str(w),str(h),'28',mode,str(amount)],cwd=tmp,capture_output=True)
        assert (p.returncode==0)==(expect==0),p.stderr
        return np.frombuffer((tmp/dst).read_bytes(),dtype=np.uint8) if not p.returncode else None
    assert np.array_equal(run('identity',0),frames)
    for m in ['smooth','chroma','sharp','hybrid','perceptual','balanced','adaptive','context','content','guarded']:
        result=run(m,4)
        assert len(result)==len(frames)
        assert np.array_equal(result[:n],frames[:n]),'Constant frame changed'
        assert np.max(np.abs(result.astype(int)-frames.astype(int)))<=1
        if m in ('perceptual','balanced','sharp','adaptive','context','content'):
            for k in range(4):assert np.array_equal(result[k*n+w*h:(k+1)*n],frames[k*n+w*h:(k+1)*n])
        if m=='chroma':
            for k in range(4):assert np.array_equal(result[k*n:k*n+w*h],frames[k*n:k*n+w*h])
    legacy=run('legacy',16)
    p=subprocess.run([str(root/'34_demo.exe'),'in.yuv','old.yuv',str(w),str(h),'28'],cwd=tmp,capture_output=True)
    assert p.returncode==0,p.stderr
    assert legacy.tobytes()==(tmp/'old.yuv').read_bytes(),'Legacy does not reproduce previous implementation'
    run('identity',0,dst='in.yuv',expect=1)
    assert (tmp/'in.yuv').read_bytes()==frames.tobytes()
    (tmp/'partial.yuv').write_bytes(b'incomplete')
    run('smooth',2,src='partial.yuv',dst='rejected.yuv',expect=1)
    assert not (tmp/'rejected.yuv').exists()
    base=[{'bitrate':r,'q':q} for q,r in zip([30,32,34,36],[100,200,400,800])]
    opt=[{**r,'bitrate':r['bitrate']*.9} for r in base]
    for method in ['pchip','cubic']:
        assert abs(bd_rate(base,base,'q',method)['percent'])<1e-9
        assert abs(bd_rate(base,opt,'q',method)['percent']+10)<1e-9
    bad=[{**r,'q':30} for r in base]
    try:bd_rate(base,bad,'q');raise AssertionError('Nonmonotonic quality accepted')
    except ValueError:pass
    (tmp/'verified.json').write_text(json.dumps({'identity':True,'constant':True,'bounded_delta':True,'chroma_keeps_luma':True,'legacy_exact':True,'same_path_guard':True,'partial_frame_guard':True,'bdrate_analytic':True},indent=2))
    print('Correctness and analytical BD-Rate checks passed.')

if __name__=='__main__':main()
