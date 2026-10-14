from equivalent_validation import reuse

if __name__=='__main__':
    for old,profile,new,exe in [
        ('v2_holdout_x265','balanced:2','v7_holdout_x265','results/code_snapshots/preprocess_scalar_v2.exe'),
        ('v2_full_x265','balanced:2','v7_full_x265','results/code_snapshots/preprocess_scalar_v2.exe'),
        ('v3_foreman_x265','adaptive:2','v7_foreman_x265','preprocess_adaptive.exe'),
        ('v3_mobile_x265','adaptive:2','v7_mobile_x265','preprocess_adaptive.exe')]:
        reuse(old,profile,new,exe,'guarded','preprocess.exe','preprocess.cpp')
