"""Generate complete, source-backed experiment coverage and decision tables."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parent
CODECS={'libx265':'HEVC / x265','libx264':'AVC / x264','libsvtav1':'AV1 / SVT-AV1','libvvenc':'VVC / VVenC'}
MODES={
    'identity':'原样复制；各组基线',
    'legacy':'Y/U/V范围门控均值；复现旧版，无新方案的±1限制',
    'smooth':'Y/U/V弱混合保边平滑，±1限幅',
    'chroma':'仅U/V平滑，Y复制，±1限幅',
    'sharp':'仅Y十字高通增强，梯度门控，±1限幅',
    'hybrid':'Y增强＋U/V平滑，±1限幅',
    'perceptual':'亮度保护＋活动度/结构一致性门控增强，仅Y',
    'balanced':'perceptual＋弱梯度孤立小峰抑制，仅Y',
    'adaptive':'16×16纹理块在balanced与弱sharp间选择，仅Y',
    'context':'整帧纹理上下文＋局部块选择，暗部/高亮保护，仅Y',
    'content':'低活动帧balanced、其余局部adaptive，固定阈值9，仅Y',
    'guarded':'高活动高清仅色度轻平滑；其余content，回归风险门控',
}
OLD_ORDER=['screen_v3','screen_hybrid','holdout_x265','full_x265','full_sharp1','holdout_x264','foreman_x265','mobile_x265']

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def link(path,label=None):return f'[{label or path.name}]({path.as_posix()})'
def percent(value):return '无有效曲线' if value is None else f'{value:+.4f}%'
def guard(s):
    values=[s.get(f'{m}_{method}',{}).get('percent') for m in ('psnr','psnr_y') for method in ('pchip','cubic')]
    if any(v is None for v in values):return None,False
    worst=max(values);return worst,worst<=0.3

def dataset(mf):
    name=Path(mf['input']).name.lower()
    for token,label in [('crowd_run','CrowdRun HD'),('ducks_take_off','DucksTakeOff HD'),('foreman','Foreman CIF'),('mobile','Mobile CIF'),('beauty','Beauty HD')]:
        if token in name:return label
    return Path(mf['input']).stem

def load_records():
    records=[]
    directories=list((ROOT/'results').iterdir())
    def order(p):return (0,OLD_ORDER.index(p.name)) if p.name in OLD_ORDER else (1,p.name)
    for directory in sorted(directories,key=order):
        if not directory.is_dir() or not (directory/'summary.json').exists() or not (directory/'manifest.json').exists():continue
        summaries=read(directory/'summary.json')
        if not summaries or not isinstance(summaries,list):continue # exclude backend-only smoke and timing
        if directory.name not in OLD_ORDER and not directory.name.startswith(('v2_','v3_','v4_','v5_','v6_','v7_')):continue
        mf=read(directory/'manifest.json')
        if mf.get('codec') not in CODECS:continue
        rows=list(csv.DictReader((directory/'points.csv').open(encoding='utf-8')))
        records.append({'directory':directory,'manifest':mf,'summaries':summaries,'rows':rows,'dataset':dataset(mf)})
    return records

def plot_screens(records):
    screen_names=['v2_screen_x265','v2_screen_x264','v2_screen_av1','v2_screen_vvc']
    by_name={r['directory'].name:r for r in records}
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for ax,name in zip(axes.flat,screen_names):
        if name not in by_name:ax.set_visible(False);continue
        r=by_name[name];data=[s for s in r['summaries'] if s['vmaf_pchip'].get('percent') is not None]
        values=[s['vmaf_pchip']['percent'] for s in data]
        colors=['#cf4f47' if not guard(s)[1] else '#d49735' if v>=0 else '#278777' for s,v in zip(data,values)]
        ax.barh([s['profile'] for s in data],values,color=colors)
        ax.axvline(0,color='black',lw=.8);ax.grid(axis='x',alpha=.2)
        ax.set_title(CODECS[r['manifest']['codec']]+' / Beauty 64 frames')
        ax.set_xlabel('VMAF BD-Rate (%) — negative saves bitrate')
    fig.legend(handles=[Patch(color='#278777',label='PSNR passes, VMAF gain'),Patch(color='#d49735',label='PSNR passes, VMAF loss'),Patch(color='#cf4f47',label='PSNR rejected')],loc='lower center',ncol=3)
    fig.tight_layout(rect=[0,.05,1,1]);fig.savefig(ROOT/'results/four_standard_screening.png',dpi=160);plt.close(fig)

def plot_regression(records):
    names=['v7_full_x265','v7_holdout_x265','v7_foreman_x265','v7_mobile_x265','v7_crowd_run_1080p50_x265','v7_ducks_take_off_1080p50_x265']
    labels=['Beauty full 600','Beauty segment 192','Foreman CIF 300','Mobile CIF 300','CrowdRun HD 128','DucksTakeOff HD 128']
    by_name={r['directory'].name:r for r in records};data=[]
    for name,label in zip(names,labels):
        if name not in by_name:continue
        s=by_name[name]['summaries'][0];data.append((label,guard(s)[0],s['vmaf_pchip']['percent']))
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    axes[0].barh([d[0] for d in data],[d[1] for d in data],color='#477baf');axes[0].axvline(.3,color='#bb4338',ls='--',label='0.3% limit')
    axes[0].set_xlabel('Worst PSNR BD-Rate (%)');axes[0].legend()
    axes[1].barh([d[0] for d in data],[d[2] for d in data],color='#278777');axes[1].axvline(0,color='black',lw=.8)
    axes[1].set_xlabel('VMAF BD-Rate (%) — negative saves bitrate')
    for ax in axes:ax.grid(axis='x',alpha=.2)
    fig.suptitle('guarded:2 / HEVC medium — regression data used in design')
    fig.tight_layout();fig.savefig(ROOT/'results/guarded_regression.png',dpi=160);plt.close(fig)

def latest_table(records):
    names=['v7_full_x265','v7_holdout_x265','v7_foreman_x265','v7_mobile_x265','v7_crowd_run_1080p50_x265','v7_ducks_take_off_1080p50_x265','v7_holdout_x264','v7_holdout_av1','v7_holdout_vvc','v4_holdout_av1','v4_holdout_vvc']
    by_name={r['directory'].name:r for r in records}
    lines=['## 当前候选与硬约束检查','',
           '接受条件：YUV综合与Y-PSNR的PCHIP、三次插值四个结果全部≤+0.3%，同时普通VMAF BD-Rate<0。表中的“PSNR最坏值”为这四项的最大值，判定使用未舍入数值；NEG另列诊断，不替代主指标。', '',
           '| 内容/范围 | 标准 | 前处理 | PSNR最坏值 | VMAF BD-Rate | NEG BD-Rate | 本条件下接受 |',
           '|---|---|---|---:|---:|---:|---|']
    accepted=failed=0
    for name in names:
        if name not in by_name:continue
        r=by_name[name];mf=r['manifest']
        for s in r['summaries']:
            if name in ('v4_holdout_av1','v4_holdout_vvc') and s['profile']=='context:2':continue # same pixel output already shown as guarded
            worst,passes=guard(s);v=s['vmaf_pchip'].get('percent');valid=passes and v is not None and v<0
            accepted+=valid;failed+=not valid
            lines.append(f"| {r['dataset']}，帧{mf['start_frame']}–{mf['start_frame']+mf['frames']-1} | {CODECS[mf['codec']]} | {s['profile']} | {percent(worst)} | {percent(v)} | {percent(s['vmaf_neg_pchip'].get('percent'))} | {'是' if valid else '否'} |")
    lines += ['',f'上述最新验证条目中，{accepted}项同时过保真约束并取得VMAF收益，{failed}项未满足联合条件。这里只统计列出的条件，不作为不同标准、帧数或分辨率的混合平均分。', '',
              '最终HEVC候选guarded:2在当前五段素材的六组条件中均过本地保真筛选并取得VMAF收益。前四组经过每个质量点全部处理字节相等后复用原编码质量，两组高清重新编码；这是回归结果，不是六次新独立编码验证。content原先在DucksTakeOff未过PSNR、CrowdRun未取得VMAF收益，失败记录仍保留。','',
              '风险门控是在观察新增高清失败、补测chroma:4后设计，因此CrowdRun/DucksTakeOff已经参与最终方案设计，不能再称最终guarded的独立盲测集。它只使用分辨率与输入梯度，不查询视频名称/标签，但仍可能对这五段素材过拟合。需要新的独立全长高清集及官方配置复核。','',
              '更稳妥的局部条件候选：Beauty/x264 medium 192帧的sharp:1（最坏PSNR +0.1861%、VMAF −0.2481%）；Beauty/SVT-AV1 preset8 192帧的hybrid:2（最坏PSNR −9.8182%、VMAF −11.8006%）；Beauty/VVenC faster 192帧的perceptual:2（最坏PSNR −0.0182%、VMAF −0.8884%）。这些是不同标准各自相对基线的收益，不能把AV1大收益当作正式HEVC赛题收益。','']
    return lines

def main():
    records=load_records()
    report=['# 34题赛前开发与验证报告','',
            '更新日期：2026-10-14。保留2026-10-13历史实验，并新增感知门控、内容自适应、四标准覆盖与独立高清验证。所有数值来自已完成结果文件；未完成、无有效曲线和未实现方法不会标成达标。','']
    report+=latest_table(records)
    report+=['![HEVC回归结果]('+(ROOT/'results/guarded_regression.png').as_posix()+')','']
    report += ['## 方案如何结合人眼感知理论','',
               '本模块部署在编码器外部，不修改编码器源码；每组baseline/opt使用相同编码配置，都相对未处理原始帧评测。优化目标是在PSNR BD-Rate硬约束内降低VMAF BD-Rate。像素限幅是输入扰动控制，不是编码后BD-Rate保证。', '',
               '### 新增的可执行策略','',
               '| 方案 | 理论启发与实际规则 | 当前实现边界 |',
               '|---|---|---|',
               '| perceptual | 用亮度、邻域活动度和方向一致性保护结构；深暗/高亮保持原值，只增强有邻域支持的低至中等对比细节 | 不是完整JND/CSF模型，不检测人脸或文字 |',
               '| balanced | 在perceptual外，抑制弱梯度邻域中四方向一致的小孤立峰/谷，尝试减少随机扰动 | 单帧处理；不能把真实颗粒都看作噪声 |',
               '| adaptive | 16×16块纹理密度较高时回退到更弱增强，其余使用balanced；保护真实纹理 | 局部块决策可能改变收益，已保留失败结果 |',
               '| context | 整帧均值<12用balanced，≥40用弱增强，中间用局部adaptive；保护暗部/高亮，U/V复制 | 探索性阈值，非JND标定 |',
               '| content | 整帧均值<9用balanced，否则用局部adaptive，取消整帧弱增强分支 | 固定后独立高清验证失效，未调整该阈值 |',
               '| guarded | 宽≥1280、高≥720且整帧平均梯度≥10时保留输入Y，只执行chroma:4；其他情况采用content:2 | 后续回归风险门控，不保证未知内容/分辨率必然过BD-Rate |','',
               '令中心为c，四邻点为L/R/U/D：g=|L−R|+|U−D|，A=Σ|c−邻点|，h=4c−L−R−U−D。增强要求24≤c≤231、6≤g<32、2g≥A，A≤36（中间亮度）或48（较暗/亮区域）；|h|达到强度阈值才修改±1。balanced小峰抑制要求g≤4、8≤A≤20、|h|≥12且四方向同为峰或谷。', '',
               'amount=2时，前处理CRF提示<26会把增强降到强度1；其他提示使用强度2。局部adaptive按输入块梯度均值≥12或强梯度比例≥25%选择弱增强。context/content的整帧均值每4像素采样，局部每2像素采样；仅保存复用工作缓冲，不保存过去帧状态。', '',
               '这些规则借鉴亮度掩蔽、纹理掩蔽与结构保护，但真实纹理也可能重要，因此高活动区域采用保护优先的弱处理。当前没有复现完整NLM、双边滤波、时域运动补偿、自适应DCT或神经网络；这些仍属于文献/后续方向。论文依据和数据选取见'+link(ROOT/'KNOWLEDGE.md')+'。', '',
               '### 迭代过程与选择偏差','',
               '初版弱增强在Beauty全长有小收益，但在另一片段和Foreman失效。结构门控与小峰抑制改善Beauty/Foreman，却在Mobile失效；局部纹理回退改善Mobile，但损失了Beauty片段收益。context据此引入整帧上下文，但Foreman有12/300帧跨过阈值12，混合策略效果变差；该观察提示切换与编码参考的耦合，尚未做专门因果消融。', '',
               'content将阈值改为9并取消整帧弱增强分支；全帧梯度记录保存在results/context_features_all_frames.json。Beauty/Foreman/Mobile参与设计，不是盲测集。CrowdRun/DucksTakeOff最初在固定参数后验证content并暴露失效；之后色度补测通过它们，但在Beauty/Foreman失效，故新增guarded风险门控。它们各128连续帧，最终已成为回归素材，并非未参与设计的独立集或完整500帧。','']
    # Standard and method coverage from completed data only.
    coverage={mode:{} for mode in MODES}
    for r in records:
        for profile in {row['profile'] for row in r['rows']}:
            mode,amount=profile.split(':');coverage[mode].setdefault(r['manifest']['codec'],set()).add(int(amount))
    report += ['## 压缩标准与前处理覆盖','',
               '已完成的评测分别使用x265、x264、SVT-AV1与VVenC。这里补齐的是已实现方法在四标准上的代表性强度；并非每个强度、每个视频、每种preset的全组合。AV1其他实现libaom/rav1e未评测，算法文献方向也不能算作已测试方法。','',
               '| 模式/思路 | HEVC/x265 amount | AVC/x264 amount | AV1/SVT-AV1 amount | VVC/VVenC amount |',
               '|---|---|---|---|---|']
    for mode,description in MODES.items():
        values=['、'.join(map(str,sorted(coverage[mode].get(codec,set())))) or '未测试' for codec in CODECS]
        # CODECS order is HEVC, AVC, AV1, VVC.
        report.append(f'| {mode}：{description} | '+' | '.join(values)+' |')
    report += ['', '### 不同标准的固定评测协议','',
               '| 标准 | 质量控制/测试点 | preset与线程 | 输入/评价像素域 | 其他固定设置 |',
               '|---|---|---|---|---|',
               '| HEVC/x265 | CRF 22/26/30/34 | veryfast或medium；pools=4、frame-threads=1 | 8-bit YUV420P | keyint=min-keyint=120、scenecut=0 |',
               '| AVC/x264 | CRF 22/26/30/34 | veryfast或medium；threads=4 | 8-bit YUV420P | keyint=min-keyint=120、scenecut=0 |',
               '| AV1/SVT-AV1 | CRF 24/30/36/42 | preset=8、lp=4 | 8-bit YUV420P | GOP=120、film-grain=0；日志确认默认PSNR tune，内部过滤保持库默认 |',
               '| VVC/VVenC | QP 22/27/32/37 | faster、Threads=4 | 两路8→10编码；解码统一10→8后与原始8-bit比较 | QPA=1、IntraPeriod=128、GOPSize=32；固定无抖动位深转换 |', '',
               'AV1/VVC的前处理CRF提示显式固定为28，不把它与AV1 CRF或VVC QP宣称等价。VVC转换已对0–255全部代码验证8→10→8原样返回，但有损VVC输出仍可能产生正常的舍入误差。VVC结果仅适用于本轮10-bit编码包装和8-bit评价口径，不能当成官方原生8-bit评测已复现。', '',
               'VMAF固定为v0.6.1，NEG固定为v0.6.1neg，所有帧均评价。码率由视频包字节和真实帧数/FPS计算，不含MP4封装。模型、共同质量区间、插值、解码位深和baseline复用均记录在manifest/summary中。不同标准的同值数值不能直接比较质量，本报告不排名其绝对压缩效率。', '',
               '旧脚本沿用crf字段/部分文件名；VVC的真实质量参数以manifest/quality_mode=qp及编码命令中的-qp为准。新context脚本已将VVC结果文件命名为qp。','',
               '![四标准代表性筛选]('+ (ROOT/'results/four_standard_screening.png').as_posix()+')','',
               '## 全部已完成实验结果','',
               '以下保留历史、筛选、验证及失败方案。PSNR/YUV、Y、VMAF、NEG列为PCHIP BD-Rate百分比；最坏PSNR同时考虑两个平面口径与两种插值。质量无有效曲线时不判定达标。']
    for r in records:
        directory=r['directory'];mf=r['manifest'];mode=mf.get('quality_mode','crf')
        report += ['',f"### {directory.name}：{r['dataset']} / {CODECS[mf['codec']]}",'',
                   f"输入{mf['width']}×{mf['height']}、{mf['fps']}fps；帧{mf['start_frame']}–{mf['start_frame']+mf['frames']-1}，共{mf['frames']}帧；{mode.upper()}点{mf['crfs']}；preset={mf['preset']}；GOP={mf['gop']}；前处理提示={mf.get('preprocess_crf') if mf.get('preprocess_crf') is not None else '随x26x CRF'}。",'',
                   '| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |',
                   '|---|---:|---:|---:|---:|---:|---|---|---:|']
        for s in r['summaries']:
            worst,passed=guard(s);v=s['vmaf_pchip'].get('percent');valid=passed and v is not None and v<0
            vals=[s[m+'_pchip'].get('percent') for m in ('psnr','psnr_y','vmaf','vmaf_neg')]
            report.append('| '+s['profile']+' | '+' | '.join(percent(v) for v in vals)+f" | {percent(worst)} | {'是' if passed else '否'} | {'是' if valid else '否'} | {s['total_wall_change_percent']:+.2f}% |")
        report += ['',link(directory/'points.csv')+'；'+link(directory/'summary.json')+'；'+link(directory/'manifest.json')+'。']
        if mf.get('reuse_baseline'):report += ['baseline复用自`'+mf['reuse_baseline']+'`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。']
        if mf.get('encoding_reused'):
            report += ['**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`'+mf['quality_reused_from']+'`中的`'+mf['quality_reused_profile']+'`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见'+link(directory/'equivalence.json')+'。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。']
        report += ['*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。']
    report += ['', '## 正确性、加速与重复计时','',
               '逐帧接口保持processYUVFrame(const uint8_t*, uint8_t*, int, int, int)，输入为紧密排列的8-bit YUV420P，支持src==dst。当前实现使用局部输入和工作缓冲，不使用视频文件名、未来帧或原始参考评分。未改变分辨率、FPS或帧数。', '',
               '旧检查覆盖恒等、常数帧、像素上限、色度不改亮度、旧版一致性、文件保护与解析BD-Rate；初版SIMD通过192组、门控SIMD通过160组。最终平滑/色度阈值与guarded共通过144组标量/SIMD等价检查，含奇数色度尺寸、舍入、限幅和1080p。adaptive/context/content各20组不变量检查；guarded另验证高清分支原地/分离缓冲一致、Y原样及整体限幅。证据位于results/correctness、simd_check、v2_simd_check、final_simd_check、v3/v4/v5_correctness。']
    for name in ('timing','v7_timing'):
        path=ROOT/'results'/name/'summary.json'
        if path.exists():
            t=read(path)
            report += ['',f"重复计时 `{name}`：{t['profile']}、{t['codec']}、preset={t['preset']}、CRF={t['crf']}，三轮交替；总墙钟中位数变化{t['median_total_change_percent']:+.2f}%。详见"+link(path)+'。']
            if t.get('median_kernel_seconds') is not None:
                report += [f"192帧前处理内核中位数{t['median_kernel_seconds']:.6f}秒，约{t['median_kernel_seconds']/192*1000:.3f}毫秒/帧；包含文件I/O的端到端约增加11%，仍需在官方内存接口中评估并优化。"]
    report += ['', '### 抽帧目视检查','',
               '已对齐查看Beauty原始片段第64帧（原序列320）与AV1 hybrid/VVC perceptual解码帧，以及DucksTakeOff原始第64帧与HEVC guarded解码帧。主体位置、轮廓、分辨率和整体颜色正常，存在正常有损编码的纹理变化，未发现黑帧、错位或明显异常色块。文件位于results/visual_check_final/。这不是全视频主观评分，也不能仅据此宣称人眼质量提升。']
    report += ['', '## 数据来源与结论边界','',
               '历史Beauty为1080p120、600帧；Foreman/Mobile为CIF、300帧，仅作低分辨率迁移诊断。新增CrowdRun、DucksTakeOff来自Xiph托管的SVT测试集，按Y4M头保持1080p50，只取前128个连续完整帧，剥离容器，不缩放、不抽帧、不重编码。源URL、头、HTTP范围状态、帧数与SHA256保存于datasets对应JSON。', '',
               'UVG Jockey/HoneyBee服务器连接超时，未取得可用文件，故未写成已评测数据；改用上述独立高清内容。SVT原始技术/使用限制文档链接保存在数据清单；Beauty、Xiph等来源信息见KNOWLEDGE.md及datasets/README.md。', '',
               '参考已有CRF28单点：baseline VMAF69.163722，opt68.754333；按旧日志已舍入MSE重算PSNR约38.296932→38.360033dB。单点不能算BD-Rate，旧模型/配置记录不完整，不与新四点结果混用。', '',
               '接受仅指当前内容、帧区间、编码配置、质量点和度量口径。0.3%门槛很窄，四点插值结果未建立统计置信区间；短片段、CIF、不同GOP上下文和官方未知配置都限制泛化。后续须覆盖独立视频全长、更多内容/质量点，并按官方PSNR平面、模型、码率与汇总算法复核。', '',
               '恒等/低强度回退可以保护正确性，但不自动构成正向收益。不得按已知视频标签切换参数，不得因某个条件失败就删除其结果；未过保真约束的候选不推荐，即使VMAF收益较大。','']
    plot_screens(records)
    plot_regression(records)
    (ROOT/'REPORT.md').write_text('\n'.join(report),encoding='utf-8')
    print('Completed experiment groups:',len(records))

if __name__=='__main__':main()
