# 34 题赛前开发与验证报告

实验日期：2026-10-13。结果覆盖Beauty 1080p及Foreman/Mobile CIF，分别保留其原始规格；正式编码器和脚本尚未发布。压缩标准、编码器、前处理与实际测试范围如下单独列明。

## 选题判断

当前最保守的候选 sharp:1 在 Beauty 全 600 帧 / x265 medium 的 PSNR BD-Rate 为 -0.1274%，Y-PSNR 为 -0.1680%，VMAF 为 -0.1641%，VMAF-NEG 为 -0.1273%。该条件下满足保真约束并取得微小收益。

但 sharp:1 在 Beauty 另一片段 / x265 medium 上出现 +0.3092% VMAF BD-Rate 损失；sharp:2 和 hybrid:2 在 Beauty 全长虽然有 VMAF 收益，却超过 PSNR 上限。因此当前证据支持“已搭建可运行开发与验证闭环、局部条件有收益”，不支持“稳定满足正式赛题全部要求”。

若选择 34 题，下一阶段优先投入独立 1080p 内容验证与内容门控，先保证最差内容的保真裕量，再争取更大的 VMAF 收益；不建议继续无约束增加全画面处理强度。目标是围绕局部噪声/纹理特征决定哪些像素应该处理，避免仅靠固定强度碰运气。该建议是基于本次实验的工程判断。

## 实验范围：压缩标准、编码器与前处理思路

**已实际采用 HEVC/H.265（x265）与 AVC/H.264（x264）两种压缩标准，并比较多种独立前处理思路。VVC/H.266 与 AV1 只确认本地可用，尚未开展编码和质量评测。**

处理位于编码器外部：baseline 为原始帧→编码→解码，opt 为原始帧→本项目前处理→同配置编码→解码；两者都与未处理原始帧比较。

| 压缩标准 | 实现 | 实际用途与范围 | 状态 |
|---|---|---|---|
| HEVC / H.265 | FFmpeg libx265 | 主筛选、Beauty片段/600帧全长、Foreman/Mobile；veryfast和medium分别建立baseline | 已评测 |
| AVC / H.264 | FFmpeg libx264 | Beauty帧256–447、medium；仅检验identity、sharp:1、sharp:2 | 已评测 |
| VVC / H.266 | FFmpeg libvvenc / VVenC | 查询可用性和输入支持，尚未建立独立QP/位深转换评测路径 | 未评测 |
| AV1 | libaom / SVT-AV1 / rav1e | 查询编码器可用性，尚未适配和运行评测 | 未评测 |

### 前处理方案与标准覆盖

`mode:amount` 是本项目前处理配置，不是编码器参数。下表中的数值是实际测试强度；“未测试”不能理解为无效。实现支持更宽的强度范围，但这里仅报告已有记录。

| 配置模式 | 思路与作用 | HEVC/x265已测amount | AVC/x264已测amount |
|---|---|---|---|
| identity（恒等参考） | Y/U/V 原样复制，用于各组 baseline | 0 | 0 |
| legacy（原版范围门控平滑） | Y/U/V 邻域均值，跳过强梯度；保持旧版修正，不设新方案的±1上限 | 16 | 未测试 |
| smooth（弱混合保边平滑） | Y/U/V 使用原平滑修正的 amount/16，舍入后每样本限幅±1 | 2、4 | 未测试 |
| chroma（仅色度平滑） | Y 原样复制；只处理 U/V，修正混合比例 amount/16，每样本限幅±1 | 4、16 | 未测试 |
| sharp（限幅亮度细节增强） | 仅处理 Y；十字邻域高通修正 amount×残差/64，梯度门控并限幅±1；U/V复制 | 1、2、4 | 1、2 |
| hybrid（亮度增强+色度平滑） | Y 用指定强度增强；U/V 用16/16平滑修正，均限幅±1 | 2、4 | 未测试 |

空间平滑属于范围门控邻域均值，没有复现完整双边滤波或NLM。当前门控仅使用CRF相关阈值和局部梯度，不是完整JND、人脸/文字检测或时域运动模型。时域去噪、JND/显著性模型、自适应DCT、亮度映射及学习型前处理均未实现或测试。OpenMP/AVX2是计算加速，未改变候选像素输出，不作为新的前处理思路计数。

### 实际实验组合

| 结果目录 | 标准/实现 | preset | 输入尺寸、FPS | 连续帧区间（0起始） | 已测前处理 |
|---|---|---|---|---|---|
| results/screen_v3 | HEVC / H.265（x265） | veryfast | 1920×1080，120fps | 0–63（64帧） | chroma:4, identity:0, legacy:16, sharp:1, smooth:2, smooth:4 |
| results/screen_hybrid | HEVC / H.265（x265） | veryfast | 1920×1080，120fps | 0–63（64帧） | chroma:16, hybrid:2, hybrid:4, identity:0, sharp:2, sharp:4 |
| results/holdout_x265 | HEVC / H.265（x265） | medium | 1920×1080，120fps | 256–447（192帧） | identity:0, sharp:1 |
| results/full_x265 | HEVC / H.265（x265） | medium | 1920×1080，120fps | 0–599（600帧） | hybrid:2, identity:0, sharp:2 |
| results/full_sharp1 | HEVC / H.265（x265） | medium | 1920×1080，120fps | 0–599（600帧） | identity:0, sharp:1 |
| results/holdout_x264 | AVC / H.264（x264） | medium | 1920×1080，120fps | 256–447（192帧） | identity:0, sharp:1, sharp:2 |
| results/foreman_x265 | HEVC / H.265（x265） | medium | 352×288，30000/1001fps | 0–299（300帧） | identity:0, sharp:1, sharp:2 |
| results/mobile_x265 | HEVC / H.265（x265） | medium | 352×288，30000/1001fps | 0–299（300帧） | identity:0, sharp:1, sharp:2 |

各组均使用CRF 22/26/30/34、GOP=120和固定线程配置。baseline与opt在组内共享相同编码器参数；veryfast与medium是不同实验组，不是opt单独改变preset。不同标准的同值CRF不代表同等质量，因此本报告不据此排名x264与x265的压缩效率。

### 迁移结论具体指什么

同一个前处理可受标准、实现、preset、视频内容、GOP上下文和评测模型影响。下面对照同一Beauty片段（256–447）、同一弱候选sharp:1，各自相对本标准的identity基线；不是直接比较两种标准的绝对编码质量。

| 固定前处理和内容 | 标准/实现 | PSNR BD-Rate | VMAF BD-Rate |
|---|---|---:|---:|
| Beauty 192帧、sharp:1、medium | HEVC / H.265（x265） | -0.0138% | +0.3092% |
| Beauty 192帧、sharp:1、medium | AVC / H.264（x264） | +0.1566% | -0.2481% |

该对照已经显示同一前处理的收益方向可以随后端变化；同一x265内部，弱候选在Beauty全长、留出片段和Foreman上也呈现不同结果。当前只能证明列出的实验条件，不能声称四种标准或所有内容上收益已复现。官方编码器公布后需替换后端、保持外部模块接口，并按正式配置和脚本重新测试。

本次文档更新未新增编码实验；下文的原始点、BD-Rate和耗时仍来自既有结果。新增感知论文和数据推荐位于KNOWLEDGE.md的1.4、1.5节，不能算作已完成算法或数据验证。

## 指标口径

所有表格均为 BD-Rate 百分比，负数表示同等质量节省码率。PSNR 约束为 ≤ +0.3%。主值使用 PCHIP，JSON 中保留传统三次插值与共同质量区间。YUV 综合和 Y-PSNR 分别列出，避免提前猜测官方口径。

已有 CRF28 单点：baseline VMAF 69.163722，opt 68.754333；PSNR 从逐帧日志的已舍入 MSE 重算约 38.296932→38.360033 dB，仅供审计。单点结果不能计算 BD-Rate。旧 VMAF JSON 未完整记录模型/配置，因此不能与新四点实验混用。

## 实际实验

### 首次筛选：前 64 帧 / x265 veryfast

CRF：[22, 26, 30, 34]；GOP=120；线程=4；VMAF=v0.6.1，NEG=v0.6.1neg。未缩放或抽帧；输入片段逐帧连续。

| 配置 | PSNR YUV | PSNR Y | VMAF | VMAF-NEG | 总墙钟耗时变化 | PSNR双口径通过 |
|---|---:|---:|---:|---:|---:|---|
| chroma:4 | -0.3127% | -0.2393% | +0.1653% | -0.0225% | +114.83% | 是 |
| legacy:16 | -3.5147% | -3.1373% | +0.6020% | -0.2025% | +381.75% | 是 |
| sharp:1 | -0.2950% | -0.1665% | -0.2684% | -0.3265% | +94.30% | 是 |
| smooth:2 | +0.1265% | +0.1938% | +0.3620% | +0.2634% | +357.21% | 是 |
| smooth:4 | -0.7646% | -0.6855% | +0.0995% | -0.0114% | +329.21% | 是 |

逐点数据：`results/screen_v3/points.csv`；汇总：`results/screen_v3/summary.json`；完整配置：`manifest.json`；编码及指标日志均已保留。

### 扩展筛选：前 64 帧 / x265 veryfast

CRF：[22, 26, 30, 34]；GOP=120；线程=4；VMAF=v0.6.1，NEG=v0.6.1neg。未缩放或抽帧；输入片段逐帧连续。

| 配置 | PSNR YUV | PSNR Y | VMAF | VMAF-NEG | 总墙钟耗时变化 | PSNR双口径通过 |
|---|---:|---:|---:|---:|---:|---|
| chroma:16 | -0.1407% | +0.1194% | +0.0415% | -0.0571% | +54.04% | 是 |
| hybrid:2 | +0.2648% | +0.4923% | -0.0717% | +0.0073% | +70.38% | 否 |
| hybrid:4 | +0.9662% | +1.2099% | -2.2401% | -1.7420% | +72.56% | 否 |
| sharp:2 | -0.0245% | +0.0499% | -0.5662% | -0.4738% | +28.82% | 是 |
| sharp:4 | +1.3218% | +1.2000% | -0.5904% | -0.2015% | +33.83% | 否 |

逐点数据：`results/screen_hybrid/points.csv`；汇总：`results/screen_hybrid/summary.json`；完整配置：`manifest.json`；编码及指标日志均已保留。

### sharp:1 验证：帧 256–447 / x265 medium

CRF：[22, 26, 30, 34]；GOP=120；线程=4；VMAF=v0.6.1，NEG=v0.6.1neg。未缩放或抽帧；输入片段逐帧连续。

| 配置 | PSNR YUV | PSNR Y | VMAF | VMAF-NEG | 总墙钟耗时变化 | PSNR双口径通过 |
|---|---:|---:|---:|---:|---:|---|
| sharp:1 | -0.0138% | +0.0198% | +0.3092% | +0.2154% | +34.02% | 是 |

逐点数据：`results/holdout_x265/points.csv`；汇总：`results/holdout_x265/summary.json`；完整配置：`manifest.json`；编码及指标日志均已保留。

### 全长验证：600 帧 / x265 medium

CRF：[22, 26, 30, 34]；GOP=120；线程=4；VMAF=v0.6.1，NEG=v0.6.1neg。未缩放或抽帧；输入片段逐帧连续。

| 配置 | PSNR YUV | PSNR Y | VMAF | VMAF-NEG | 总墙钟耗时变化 | PSNR双口径通过 |
|---|---:|---:|---:|---:|---:|---|
| hybrid:2 | +0.7079% | +0.5507% | -0.3381% | -0.1829% | +35.50% | 否 |
| sharp:2 | +0.5991% | +0.4554% | -0.4841% | -0.3256% | +21.03% | 否 |

逐点数据：`results/full_x265/points.csv`；汇总：`results/full_x265/summary.json`；完整配置：`manifest.json`；编码及指标日志均已保留。

### 弱候选全长复核：600 帧 / x265 medium

CRF：[22, 26, 30, 34]；GOP=120；线程=4；VMAF=v0.6.1，NEG=v0.6.1neg。未缩放或抽帧；输入片段逐帧连续。

| 配置 | PSNR YUV | PSNR Y | VMAF | VMAF-NEG | 总墙钟耗时变化 | PSNR双口径通过 |
|---|---:|---:|---:|---:|---:|---|
| sharp:1 | -0.1274% | -0.1680% | -0.1641% | -0.1273% | +13.62% | 是 |

逐点数据：`results/full_sharp1/points.csv`；汇总：`results/full_sharp1/summary.json`；完整配置：`manifest.json`；编码及指标日志均已保留。

本组 identity 四点复用自 `results/full_x265`，已核对源文件、编码/度量配置及原始片段哈希。耗时比较沿用旧 baseline，仅质量比较适合直接复用。

### 编码器迁移：帧 256–447 / x264 medium

CRF：[22, 26, 30, 34]；GOP=120；线程=4；VMAF=v0.6.1，NEG=v0.6.1neg。未缩放或抽帧；输入片段逐帧连续。

| 配置 | PSNR YUV | PSNR Y | VMAF | VMAF-NEG | 总墙钟耗时变化 | PSNR双口径通过 |
|---|---:|---:|---:|---:|---:|---|
| sharp:1 | +0.1566% | +0.1861% | -0.2481% | -0.2449% | +16.92% | 是 |
| sharp:2 | +0.3822% | +0.3784% | -0.3777% | -0.2708% | +16.56% | 否 |

逐点数据：`results/holdout_x264/points.csv`；汇总：`results/holdout_x264/summary.json`；完整配置：`manifest.json`；编码及指标日志均已保留。

### 独立内容 Foreman CIF / x265 medium

CRF：[22, 26, 30, 34]；GOP=120；线程=4；VMAF=v0.6.1，NEG=v0.6.1neg。未缩放或抽帧；输入片段逐帧连续。

| 配置 | PSNR YUV | PSNR Y | VMAF | VMAF-NEG | 总墙钟耗时变化 | PSNR双口径通过 |
|---|---:|---:|---:|---:|---:|---|
| sharp:1 | +0.0885% | +0.0124% | +0.7053% | +0.6510% | +9.00% | 是 |
| sharp:2 | -0.0105% | -0.2059% | -0.1182% | +0.1255% | +9.10% | 是 |

逐点数据：`results/foreman_x265/points.csv`；汇总：`results/foreman_x265/summary.json`；完整配置：`manifest.json`；编码及指标日志均已保留。

### 独立内容 Mobile CIF / x265 medium

CRF：[22, 26, 30, 34]；GOP=120；线程=4；VMAF=v0.6.1，NEG=v0.6.1neg。未缩放或抽帧；输入片段逐帧连续。

| 配置 | PSNR YUV | PSNR Y | VMAF | VMAF-NEG | 总墙钟耗时变化 | PSNR双口径通过 |
|---|---:|---:|---:|---:|---:|---|
| sharp:1 | +0.0469% | -0.0047% | -0.4690% | -0.1174% | +34.25% | 是 |
| sharp:2 | +0.0746% | +0.0203% | +0.1807% | +0.2378% | -2.31% | 是 |

逐点数据：`results/mobile_x265/points.csv`；汇总：`results/mobile_x265/summary.json`；完整配置：`manifest.json`；编码及指标日志均已保留。

## 实现与正确性

`preprocess.cpp` 保留 `processYUVFrame(const uint8_t*, uint8_t*, int, int, int)` 接口。新候选包括弱混合保边平滑、仅色度平滑、限幅细节增强；旧方案精确复现。支持输入输出原地调用，拦截 CLI 同源输出和残帧输入。OpenMP 按行处理，四线程写入独立目标行。

`results/correctness/verified.json` 记录恒等、恒定图、±1 改变量、色度不改亮度、旧版一致性、文件保护和解析 BD-Rate 测试。`interface_test.cpp` 验证原地/分离缓冲一致与非法尺寸拒绝。编译和检查命令见 `README.md`。

最终 GCC 版本加入运行时 AVX2 检测及整型 SIMD。`results/simd_check/verified.txt` 记录 192 组标量/SIMD 逐字节一致性检查，覆盖 1–16 强度、混合模式、极小尺寸、SIMD 尾部和 1080p；未支持 AVX2 时可回退标量。首次筛选与强候选全长验证使用优化前二进制，弱候选全长及后续验证使用最终二进制，参数所对应像素输出保持一致。

## 结论边界

首次候选sharp:1在片段验证中未取得VMAF收益。随后在原筛选片段比较sharp:2、sharp:4与hybrid，进入全长测试；发现强候选保真失效后，又追加sharp:1全长复核。因此本次是探索性实验，不能将最后弱候选全长结果描述为预先锁定参数的独立盲测。全长包含筛选片段；两种编码器也不等于两种独立视频内容。

耗时是单次进程墙钟测量，包含启动和文件 I/O；前处理内核时间另存于 points.csv。结果未做多次计时置信区间，也未接入主办方内存接口，因此不能作为正式速度得分。低于 0.3% 的微小 BD 收益也不等同统计显著性。

另补充 Xiph 的 Foreman 和 Mobile 原生 352×288 / 30000:1001fps 内容。保持原尺寸，使用同一 VMAF 模型只做迁移诊断；小分辨率和模型观看域差异限制其代表性。数据来源、哈希与容器剥离过程见 datasets/manifest.json。需要更多独立 1080p 视频、全视频目视播放及官方脚本复核，才能证明正式泛化和主观正常性。知识与公开数据源详见 `KNOWLEDGE.md`。

![VMAF RD curves](D:/shenni/交大/Hackthon/34-demo/results/rd_curves.png)

## 最终程序重复计时

Beauty 192 帧、x265 medium、CRF26、sharp:1，三次交替测量，总耗时中位数变化 +8.63%。baseline 范围 [7.872434500022791, 8.395751999982167] 秒；opt 范围 [7.801908399997046, 8.977515300008235] 秒。详细分解和限制见 results/timing/summary.json。

## 抽帧目视检查

已查看原始 Beauty 第 300 帧与 weak sharp:1 / CRF26 解码帧：分辨率、主体结构、字幕水印保持；可见常规有损编码造成的噪声/纹理变化，未发现黑帧、错位、色块或明显色彩异常。检查文件位于 results/visual_check/。这仅是单帧检查，不等同于完整视频的主观质量验证。
