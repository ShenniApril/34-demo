"""Build a readable Chinese report and RD figure from completed experiments."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent

def experiment_scope(stages):
    """Describe only combinations backed by completed manifests and point records."""
    standards={'libx265':'HEVC / H.265（x265）','libx264':'AVC / H.264（x264）'}
    modes={
        'identity':('恒等参考','Y/U/V 原样复制，用于各组 baseline'),
        'legacy':('原版范围门控平滑','Y/U/V 邻域均值，跳过强梯度；保持旧版修正，不设新方案的±1上限'),
        'smooth':('弱混合保边平滑','Y/U/V 使用原平滑修正的 amount/16，舍入后每样本限幅±1'),
        'chroma':('仅色度平滑','Y 原样复制；只处理 U/V，修正混合比例 amount/16，每样本限幅±1'),
        'sharp':('限幅亮度细节增强','仅处理 Y；十字邻域高通修正 amount×残差/64，梯度门控并限幅±1；U/V复制'),
        'hybrid':('亮度增强+色度平滑','Y 用指定强度增强；U/V 用16/16平滑修正，均限幅±1'),
    }
    records=[];coverage={m:{} for m in modes}
    for folder,_ in stages:
        directory=ROOT/'results'/folder
        if not (directory/'summary.json').exists():continue
        mf=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        rows=list(csv.DictReader((directory/'points.csv').open()))
        profiles=sorted({r['profile'] for r in rows})
        for profile in profiles:
            m,a=profile.split(':');coverage[m].setdefault(mf['codec'],set()).add(int(a))
        records.append((folder,mf,profiles,len(rows)))
    section=['## 实验范围：压缩标准、编码器与前处理思路','',
             '**明确回答：已实际采用 HEVC/H.265（x265）与 AVC/H.264（x264）两种压缩标准，并比较多种独立前处理思路。VVC/H.266 与 AV1 只确认本地可用，尚未开展编码和质量评测。**', '',
             '处理位于编码器外部：baseline 为“原始帧→编码→解码”，opt 为“原始帧→本项目前处理→同配置编码→解码”；两者都与未处理原始帧比较。没有修改编码器源码，没有只给 opt 调整内部 AQ、PSY-RD、SAO、Deblocking 等参数。当前模块也不是对这些内部技术的实现或替换。', '',
             '| 压缩标准 | 实现 | 实际用途与范围 | 状态 |',
             '|---|---|---|---|',
             '| HEVC / H.265 | FFmpeg libx265 | 主筛选、Beauty片段/600帧全长、Foreman/Mobile；veryfast和medium分别建立baseline | 已评测 |',
             '| AVC / H.264 | FFmpeg libx264 | Beauty帧256–447、medium；仅检验identity、sharp:1、sharp:2 | 已评测 |',
             '| VVC / H.266 | FFmpeg libvvenc / VVenC | 查询可用性和输入支持，尚未建立独立QP/位深转换评测路径 | 未评测 |',
             '| AV1 | libaom / SVT-AV1 / rav1e | 查询编码器可用性，尚未适配和运行评测 | 未评测 |', '',
             '### 前处理方案与标准覆盖','',
             '`mode:amount` 是本项目前处理配置，不是编码器参数。下表中的数值是实际测试强度；“未测试”不能理解为无效。实现支持更宽的强度范围，但这里仅报告已有记录。', '',
             '| 配置模式 | 思路与作用 | HEVC/x265已测amount | AVC/x264已测amount |',
             '|---|---|---|---|']
    for m,(name,description) in modes.items():
        values=[]
        for codec in ('libx265','libx264'):
            amounts=coverage[m].get(codec,set())
            values.append('、'.join(map(str,sorted(amounts))) if amounts else '未测试')
        section.append(f'| {m}（{name}） | {description} | {values[0]} | {values[1]} |')
    section += ['',
                '空间平滑属于范围门控邻域均值，没有复现完整双边滤波或NLM。当前门控仅使用CRF相关阈值和局部梯度，不是完整JND、人脸/文字检测或时域运动模型。时域去噪、JND/显著性模型、自适应DCT、亮度映射及学习型前处理均未实现或测试。OpenMP/AVX2是计算加速，未改变候选像素输出，不作为新的前处理思路计数。', '',
                '### 实际实验组合','',
                '| 结果目录 | 标准/实现 | preset | 输入尺寸、FPS | 连续帧区间（0起始） | 已测前处理 |',
                '|---|---|---|---|---|---|']
    for folder,mf,profiles,count in records:
        start=mf['start_frame'];end=start+mf['frames']-1
        fps='120' if mf['fps']==120 else '30000/1001'
        section.append(f"| results/{folder} | {standards[mf['codec']]} | {mf['preset']} | {mf['width']}×{mf['height']}，{fps}fps | {start}–{end}（{mf['frames']}帧） | {', '.join(profiles)} |")
    section += ['',
                '各组均使用CRF 22/26/30/34、GOP=120和固定线程配置。baseline与opt在组内共享相同编码器参数；veryfast与medium是不同实验组，不是opt单独改变preset。不同标准的同值CRF不代表同等质量，因此本报告不据此排名x264与x265的压缩效率。', '',
                '### 迁移结论具体指什么','',
                '同一个前处理可受标准、实现、preset、视频内容、GOP上下文和评测模型影响。下面对照同一Beauty片段（256–447）、同一弱候选sharp:1，各自相对本标准的identity基线；不是直接比较两种标准的绝对编码质量。', '',
                '| 固定前处理和内容 | 标准/实现 | PSNR BD-Rate | VMAF BD-Rate |',
                '|---|---|---:|---:|']
    for folder in ('holdout_x265','holdout_x264'):
        directory=ROOT/'results'/folder
        if not (directory/'summary.json').exists():continue
        mf=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        s=next(r for r in json.loads((directory/'summary.json').read_text()) if r['profile']=='sharp:1')
        section.append(f"| Beauty 192帧、sharp:1、medium | {standards[mf['codec']]} | {s['psnr_pchip']['percent']:+.4f}% | {s['vmaf_pchip']['percent']:+.4f}% |")
    section += ['',
                '该对照已经显示同一前处理的收益方向可以随后端变化；同一x265内部，弱候选在Beauty全长、留出片段和Foreman上也呈现不同结果。当前只能证明列出的实验条件，不能声称四种标准或所有内容上收益已复现。官方编码器公布后需替换后端、保持外部模块接口，并按正式配置和脚本重新测试。', '',
                '本次文档更新未新增编码实验；下文的原始点、BD-Rate和耗时仍来自既有结果。新增感知论文和数据推荐位于KNOWLEDGE.md的1.4、1.5节，不能算作已完成算法或数据验证。','']
    return section

def main():
    stages=[('screen_v3','首次筛选：前 64 帧 / x265 veryfast'),('screen_hybrid','扩展筛选：前 64 帧 / x265 veryfast'),('holdout_x265','sharp:1 验证：帧 256–447 / x265 medium'),('full_x265','全长验证：600 帧 / x265 medium'),('full_sharp1','弱候选全长复核：600 帧 / x265 medium'),('holdout_x264','编码器迁移：帧 256–447 / x264 medium'),('foreman_x265','独立内容 Foreman CIF / x265 medium'),('mobile_x265','独立内容 Mobile CIF / x265 medium')]
    report=['# 34 题赛前开发与验证报告','',
            '实验日期：2026-10-13。结果覆盖Beauty 1080p及Foreman/Mobile CIF，分别保留其原始规格；正式编码器和脚本尚未发布。压缩标准、编码器、前处理与实际测试范围如下单独列明。',
            '', '## 指标口径','',
            '所有表格均为 BD-Rate 百分比，负数表示同等质量节省码率。PSNR 约束为 ≤ +0.3%。主值使用 PCHIP，JSON 中保留传统三次插值与共同质量区间。YUV 综合和 Y-PSNR 分别列出，避免提前猜测官方口径。',
            '', '已有 CRF28 单点：baseline VMAF 69.163722，opt 68.754333；PSNR 从逐帧日志的已舍入 MSE 重算约 38.296932→38.360033 dB，仅供审计。单点结果不能计算 BD-Rate。旧 VMAF JSON 未完整记录模型/配置，因此不能与新四点实验混用。',
            '', '## 实际实验','']
    report[4:4]=experiment_scope(stages)
    fig,axs=plt.subplots(4,2,figsize=(12,16));completed=[]
    for ax,(folder,title) in zip(axs.flat,stages):
        directory=ROOT/'results'/folder
        if not (directory/'summary.json').exists():
            ax.set_visible(False);continue
        completed.append(folder)
        manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        summaries=json.loads((directory/'summary.json').read_text())
        report += ['### '+title,'', f"CRF：{manifest['crfs']}；GOP=120；线程=4；VMAF=v0.6.1，NEG=v0.6.1neg。未缩放或抽帧；输入片段逐帧连续。",'',
                   '| 配置 | PSNR YUV | PSNR Y | VMAF | VMAF-NEG | 总墙钟耗时变化 | PSNR双口径通过 |',
                   '|---|---:|---:|---:|---:|---:|---|']
        for s in summaries:
            values=[s[m+'_pchip'].get('percent') for m in ('psnr','psnr_y','vmaf','vmaf_neg')]
            text=['无有效曲线' if v is None else f'{v:+.4f}%' for v in values]
            report.append('| '+s['profile']+' | '+' | '.join(text)+f" | {s['total_wall_change_percent']:+.2f}% | "+('是' if s['passes_psnr_all'] and s['passes_psnr_y'] else '否')+' |')
        report += ['',f'逐点数据：`results/{folder}/points.csv`；汇总：`results/{folder}/summary.json`；完整配置：`manifest.json`；编码及指标日志均已保留。','']
        if manifest.get('reuse_baseline'):report += [f"本组 identity 四点复用自 `{manifest['reuse_baseline']}`，已核对源文件、编码/度量配置及原始片段哈希。耗时比较沿用旧 baseline，仅质量比较适合直接复用。",'']
        rows=list(csv.DictReader((directory/'points.csv').open()))
        for profile in sorted(set(r['profile'] for r in rows)):
            data=sorted([r for r in rows if r['profile']==profile],key=lambda r:float(r['bitrate']))
            ax.plot([float(r['bitrate'])/1000 for r in data],[float(r['vmaf']) for r in data],marker='o',label=profile)
        ax.set_xscale('log');ax.set_xlabel('Elementary video bitrate (kbps)');ax.set_ylabel('VMAF v0.6.1')
        ax.set_title(folder);ax.grid(alpha=.25);ax.legend(fontsize=8)
    report += ['## 实现与正确性','',
               '`preprocess.cpp` 保留 `processYUVFrame(const uint8_t*, uint8_t*, int, int, int)` 接口。新候选包括弱混合保边平滑、仅色度平滑、限幅细节增强；旧方案精确复现。支持输入输出原地调用，拦截 CLI 同源输出和残帧输入。OpenMP 按行处理，四线程写入独立目标行。',
               '', '`results/correctness/verified.json` 记录恒等、恒定图、±1 改变量、色度不改亮度、旧版一致性、文件保护和解析 BD-Rate 测试。`interface_test.cpp` 验证原地/分离缓冲一致与非法尺寸拒绝。编译和检查命令见 `README.md`。',
               '', '最终 GCC 版本加入运行时 AVX2 检测及整型 SIMD。`results/simd_check/verified.txt` 记录 192 组标量/SIMD 逐字节一致性检查，覆盖 1–16 强度、混合模式、极小尺寸、SIMD 尾部和 1080p；未支持 AVX2 时可回退标量。首次筛选与强候选全长验证使用优化前二进制，弱候选全长及后续验证使用最终二进制，参数所对应像素输出保持一致。',
               '', '## 结论边界','',
               '首次候选sharp:1在片段验证中未取得VMAF收益。随后在原筛选片段比较sharp:2、sharp:4与hybrid，进入全长测试；发现强候选保真失效后，又追加sharp:1全长复核。因此本次是探索性实验，不能将最后弱候选全长结果描述为预先锁定参数的独立盲测。全长包含筛选片段；两种编码器也不等于两种独立视频内容。',
               '', '耗时是单次进程墙钟测量，包含启动和文件 I/O；前处理内核时间另存于 points.csv。结果未做多次计时置信区间，也未接入主办方内存接口，因此不能作为正式速度得分。低于 0.3% 的微小 BD 收益也不等同统计显著性。',
               '', '另补充 Xiph 的 Foreman 和 Mobile 原生 352×288 / 30000:1001fps 内容。保持原尺寸，使用同一 VMAF 模型只做迁移诊断；小分辨率和模型观看域差异限制其代表性。数据来源、哈希与容器剥离过程见 datasets/manifest.json。需要更多独立 1080p 视频、全视频目视播放及官方脚本复核，才能证明正式泛化和主观正常性。知识与公开数据源详见 `KNOWLEDGE.md`。',
               '', f'![VMAF RD curves]({(ROOT/"results/rd_curves.png").as_posix()})','']
    timing=ROOT/'results/timing/summary.json'
    if timing.exists():
        t=json.loads(timing.read_text())
        report += ['## 最终程序重复计时','',f"Beauty 192 帧、x265 medium、CRF26、{t['profile']}，三次交替测量，总耗时中位数变化 {t['median_total_change_percent']:+.2f}%。baseline 范围 {t['baseline_range_seconds']} 秒；opt 范围 {t['opt_range_seconds']} 秒。详细分解和限制见 results/timing/summary.json。",'']
    weak=ROOT/'results/full_sharp1/summary.json'
    if weak.exists():
        s=json.loads(weak.read_text())[0]
        lead=[
            '## 选题判断','',
            f"当前最保守的候选 sharp:1 在 Beauty 全 600 帧 / x265 medium 的 PSNR BD-Rate 为 {s['psnr_pchip']['percent']:+.4f}%，Y-PSNR 为 {s['psnr_y_pchip']['percent']:+.4f}%，VMAF 为 {s['vmaf_pchip']['percent']:+.4f}%，VMAF-NEG 为 {s['vmaf_neg_pchip']['percent']:+.4f}%。该条件下满足保真约束并取得微小收益。",'',
            '但 sharp:1 在 Beauty 另一片段 / x265 medium 上出现 +0.3092% VMAF BD-Rate 损失；sharp:2 和 hybrid:2 在 Beauty 全长虽然有 VMAF 收益，却超过 PSNR 上限。因此当前证据支持“已搭建可运行开发与验证闭环、局部条件有收益”，不支持“稳定满足正式赛题全部要求”。', '',
            '若选择 34 题，下一阶段优先投入独立 1080p 内容验证与内容门控，先保证最差内容的保真裕量，再争取更大的 VMAF 收益；不建议继续无约束增加全画面处理强度。目标是围绕局部噪声/纹理特征决定哪些像素应该处理，避免仅靠固定强度碰运气。该建议是基于本次实验的工程判断。','',
        ]
        report[4:4]=lead
    report += ['## 抽帧目视检查','',
               '已查看原始 Beauty 第 300 帧与 weak sharp:1 / CRF26 解码帧：分辨率、主体结构、字幕水印保持；可见常规有损编码造成的噪声/纹理变化，未发现黑帧、错位、色块或明显色彩异常。检查文件位于 results/visual_check/。这仅是单帧检查，不等同于完整视频的主观质量验证。','']
    fig.tight_layout();fig.savefig(ROOT/'results/rd_curves.png',dpi=160);plt.close(fig)
    (ROOT/'REPORT.md').write_text('\n'.join(report),encoding='utf-8')
    print('Report generated for:',', '.join(completed))

if __name__=='__main__':main()
