# 1. 34 题知识：质量指标、编码技术、感知前处理与数据选取

工作流：原始视频 → 独立 C/C++ 前处理 → 固定配置编码器 → 解码 → 与原始视频比较。
正式编码器公布后，应替换后端并重新验证。

## 1.1 PSNR、VMAF 的公式、定义与含义；BD-Rate 的定义与含义

### 1.1.1 PSNR：像素保真度

设原始参考图像为 \(x\)，解码后的待评价图像为 \(\hat x\)，共有 \(N\) 个样本，位深为 \(b\)：

\[
\mathrm{MSE}=\frac{1}{N}\sum_{i=1}^{N}(x_i-\hat x_i)^2
\]

\[
\mathrm{PSNR}=10\log_{10}\frac{(2^b-1)^2}{\mathrm{MSE}}
\]

8-bit 的峰值为 255，PSNR 单位为 dB。MSE 越小，PSNR 越高；MSE 为零时为正无穷。它反映相对原始像素的保真度，对误差位置和视觉重要性没有直接建模。

对相同尺寸的连续 \(T\) 帧，先平均各帧 MSE，再计算序列 PSNR：

\[
\mathrm{MSE}_{seq}=\frac{1}{T}\sum_{t=1}^{T}\mathrm{MSE}_t,
\qquad
\mathrm{PSNR}_{seq}=10\log_{10}\frac{255^2}{\mathrm{MSE}_{seq}}
\]

逐帧 PSNR 的 dB 算术平均不等于上述序列 PSNR。 
本项目 8-bit YUV420P 按全部样本累计的综合误差为：

\[
\mathrm{MSE}_{YUV}=\frac{4\mathrm{MSE}_Y+\mathrm{MSE}_U+\mathrm{MSE}_V}{6}
\]

4:1:1 来自样本数量，不是感知权重。Y-PSNR 仅评价亮度，综合 PSNR 还包含色度。[FFmpeg PSNR 文档](https://ffmpeg.org/ffmpeg-filters.html#psnr)。

### 1.1.2 VMAF：模型预测的感知质量

VMAF（Video Multi-Method Assessment Fusion）是全参考视频质量评价方法：提取原始/失真视频的特征，再用训练好的模型预测质量。它没有适用于所有版本的固定闭式公式。以下是计算框架的参考：

\[
\boldsymbol z_t=\Phi(x,\hat x,t),\quad
s_t=f_\theta(\boldsymbol z_t),\quad
Q_{VMAF}=\mathrm{Pool}(s_1,\ldots,s_T)
\]

\(\Phi\) 表示特征提取，\(f_\theta\) 是以主观评分训练的回归模型，\(\mathrm{Pool}\) 为时域汇总。本项目取算术平均：\(Q=T^{-1}\sum_t s_t\)。
本地固定使用 `vmaf_v0.6.1` 与 `vmaf_v0.6.1neg`。v0.6.1 的典型特征包括多尺度 VIF、ADM2 和 Motion2，分别关联视觉信息、细节/结构与运动，采用训练好的支持向量回归器。常见默认输出为 0–100，越高通常表示预测质量越好，但范围、裁剪和观看条件取决于模型/选项。普通 VMAF 可计入增强收益，NEG 抑制增强奖励，用作辅助诊断；NEG 也不是不可被误导的主观真值。模型版本和观看条件不可忽略。[Netflix 模型说明](https://github.com/Netflix/vmaf/blob/master/resource/doc/models_v0.md)、[libvmaf 官方文档](https://ffmpeg.org/ffmpeg-filters.html#libvmaf)。

### 1.1.3 BD-Rate：同等质量下的平均码率差

BD-Rate 比较 baseline 与 opt 的码率—质量曲线，采样多个 CRF 点计算得到。本地每组使用 CRF 22、26、30、34。
以质量 \(Q\) 为横轴，对码率取自然对数后插值，得到 \(L_{base}(Q)\) 与 \(L_{opt}(Q)\)。在两曲线共同覆盖区间 \([Q_{min},Q_{max}]\) 上计算：

\[
\Delta=\frac{1}{Q_{max}-Q_{min}}\int_{Q_{min}}^{Q_{max}}
\left[L_{opt}(Q)-L_{base}(Q)\right]\,dQ
\]

\[
\mathrm{BD\mbox{-}Rate}=(e^{\Delta}-1)\times100\%
\]

| 结果 | 含义 |
|---|---|
| −5% | 在共同质量区间内，平均码率比 baseline 低约5% |
| 0% | 平均码率相同 |
| +5% | 同等质量需要更多码率，是损失 |

使用 PSNR 或 VMAF 作为质量轴，即得到对应 BD-Rate，两种分数不是相互相除。赛题约束为 **PSNR BD-Rate ≤ +0.3%**，目标是 VMAF BD-Rate 尽量负；不是 PSNR 的 dB 相对降幅不超过0.3%。相同 CRF 下文件变小也不自动意味着同等质量节省码率。

主结果用 PCHIP，辅以传统三次多项式，记录共同质量区间，不外推，不静默删除异常点。官方的积分方法、测试点和视频汇总规则仍需复核。[Herglotz 等：The Bjøntegaard Bible，2023](https://arxiv.org/abs/2304.12852)。

## 1.2 赛题中编码器技术的定义和在编码过程中的功用

### 1.2.1 基础编码流程

编码器利用当前帧已重建邻域做帧内预测，或利用参考帧做运动补偿预测，再编码原图与预测之间的残差。残差经过变换、量化、熵编码形成码流；内部重建与环路滤波会影响后续参考帧。

| 环节 | 功用 | 与前处理的关系 |
|---|---|---|
| 帧内预测 | 利用空间结构预测当前区域 | 保护轮廓和方向结构，可能有利于预测 |
| 帧间预测/运动补偿 | 利用跨帧相似性 | 随机噪声难预测；不稳定处理也会增加帧间变化 |
| 变换 | 将残差变成系数，集中能量 | 削弱可省略的小残差可能减少非零系数 |
| 量化 | 降低系数精度，是有损压缩的重要来源 | 前处理误差与量化误差会相互作用 |
| 熵编码 | 紧凑表示系数、模式与运动信息 | 更易预测的内容可能减少比特 |
| 环路滤波 | 改善重建与参考图像 | 前处理像素还会受到内部滤波影响 |

这些机制不构成收益保证。少量像素变化也可能触发块划分、预测或量化的离散切换。[HEVC 官方技术入口](https://hevc.hhi.fraunhofer.de/)、[AV1 官方工具说明](https://aomedia.org/docs/AV1_ToolDescription_v11-clean.pdf)。

### 1.2.2 目前视频编码器为了实现1.2.1中的流程会用到的关键技术（题干已给）

| 技术 | 定义 | 编码功用 |
|---|---|---|
| RDO：Rate-Distortion Optimization，率失真优化 | 比较候选方案的码率与失真代价 | 选择块划分、预测等方案，权衡画质和比特 |
| SAO：Sample Adaptive Offset，样本自适应偏移 | 按亮度/边缘类别施加重建像素偏移 | 补偿部分压缩偏差，属于环路滤波 |
| Deblocking：去块滤波 | 对符合条件的编码块边界滤波 | 减轻块接缝，改善重建与参考图像 |
| AQ：Adaptive Quantization，自适应量化 | 根据局部复杂度、亮度等调整块级 QP | 分配不同区域的量化精度，复杂区域不一定得到更多比特 |
| PSY-RD：心理视觉率失真优化 | 模式决策偏好保留源图像视觉能量 | 减少模糊，但可能增大码率或降低像素指标；不是直接优化 VMAF |

RDO、AQ、PSY-RD 主要是编码器决策策略；SAO、Deblocking 是相应标准的重建工具，需要解码端一致执行。不同标准/实现的工具并不完全相同。[x265 决策、AQ 与心理视觉说明](https://x265.readthedocs.io/en/master/cli.html)、[VVC/HEVC 滤波教程](https://signalprocessingsociety.org/sites/default/files/uploads/community_involvement/docs/ICME2020_MMSPTC_VideoSlides_Versatile_Video_Coding.pdf)。

RDO 的典型代价为：

\[
J=D+\lambda R
\]

\(D\) 为重建失真，\(R\) 为比特开销，\(\lambda\) 为权衡参数。例如 A 的 \(D=10,R=100\)，B 的 \(D=6,R=130\)：当 \(\lambda=0.1\)，代价为20与19，B更优；当 \(\lambda=0.2\)，代价为30与32，A更优。实际失真度量与参数尺度由实现决定，此例只说明取舍。

### 1.2.3 独立开发的前处理在迁移到不同编码器上使用时会遇到的问题

去噪会改变残差、局部复杂度与 AQ 分配；增强会改变高频和 PSY-RD 决策；它们又会影响重建参考帧。因此风险来自**标准、实现、配置、内容、编码上下文和度量口径**，并非只有更换编码器才会发生。

## 1.3 不同的视频压缩标准（不同编码器的具体软件实现）

**标准**规定码流与解码，**编码器实现**决定搜索和码率控制，**前处理**修改输入帧，MP4等**容器**装载码流。

| 标准 | 名称与关系 | 特点和实验意义 | 本地实现 | 当前验证状态 |
|---|---|---|---|---|
| AVC / H.264 | Advanced Video Coding | 成熟的混合编码标准，适合基础对照 | x264 | 已测Beauty 64帧的多种方案与192帧迁移 |
| HEVC / H.265 | High Efficiency Video Coding，AVC后续标准 | 更灵活的编码块、预测和变换，目前主验证对象 | x265 | 已测两种preset、多种方案、五种视频内容 |
| VVC / H.266 | Versatile Video Coding，HEVC后续标准 | 进一步增强划分和预测等工具 | VVenC | 已测Beauty 64/192帧；10-bit编码包装、8-bit评价 |
| AV1 | AOMedia Video 1，独立于H.26x的路线 | 丰富的预测/变换/滤波；部分实现内部有时域过滤 | libaom、SVT-AV1、rav1e | 已测SVT-AV1的Beauty 64/192帧；其他实现未测 |

标准演进不能替代具体的速度—码率—质量比较，不能根据同值 CRF 给四者排名，也不能把“可调用”写成“已验证”。[AVC 标准](https://www.itu.int/ITU-T/recommendations/rec.aspx?rec=H.264)、[HEVC 标准](https://www.itu.int/ITU-T/recommendations/rec.aspx?rec=16661)、[VVC 官方介绍](https://www.hhi.fraunhofer.de/en/departments/vca/technologies-and-solutions/h266-vvc.html)、[AV1 官方规范](https://aomedia.org/specifications/av1/)。

本地 FFmpeg 的 `libvvenc` 仅接受 `yuv420p10le`，使用QP。原脚本只支持x264/x265；新增评测入口已加入SVT-AV1与VVenC，显式固定AV1/VVC的前处理CRF提示为28，不能将其与编码CRF/QP数值视为等价。VVC两路统一8→10编码、解码10→8评价，使用无抖动转换并验证0–255代码往返原样；这只验证本地包装，未复现官方原生位深接口。[VVenC项目](https://github.com/fraunhoferhhi/vvenc)。AV1内部过滤沿用库默认，两路一致，当前SVT日志确认默认PSNR tune。[libaom开发指南](https://aomedia.googlesource.com/aom/+/refs/heads/main/doc/dev_guide/av1_encoder.dox)。

## 1.4 人眼感知论文与不同前处理思路比较

### 1.4.1 感知概念

| 概念 | 含义 | 对前处理的启发 |
|---|---|---|
| 对比敏感度 CSF | 对不同空间/时间频率的对比变化敏感度不同 | 按结构和频率选择位置，不能将所有高频当作噪声 |
| 亮度掩蔽 | 失真可见性与背景亮度有关 | 估计亮度相关阈值，同时保护暗部细节 |
| 纹理/对比掩蔽 | 周围纹理可能降低部分误差可见性 | 区分纹理与真实边缘，选择低重要性扰动 |
| 时间掩蔽与运动 | 可见性受运动与时间上下文影响 | 保持强度连续，避免拖影和闪烁 |
| 显著性 | 注意力在画面中分布不均 | 保护文字、人脸和主体是需要验证的工程方向 |
| JND：Just Noticeable Difference | 给定条件下刚能被察觉的失真阈值 | 估计局部可修改量，不假设统一阈值适用所有视频 |

观看距离、显示器、内容和人群影响这些阈值。[Zhang 等，A Survey on Perceptually Optimized Video Coding，2021预印本/2022修订](https://arxiv.org/html/2112.12284v2)系统讨论感知建模、度量、比特分配、RDO、量化与滤波。将概念转为处理规则属于本项目工程推论，目前未实现完整人眼模型。

### 1.4.2 查阅论文及适用边界

| 论文 | 主要内容 | 对34题的借鉴与限制 |
|---|---|---|
| [A JND-Based Pixel-Domain Algorithm and Hardware Architecture for Perceptual Image Coding，2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC8320967/) | 像素域JND、感知冗余处理与硬件实现 | 借鉴局部阈值与结构保护；图像域不可见性不保证编码后BD-Rate约束 |
| [Buades、Coll、Morel，Non-Local Means Denoising，2011](https://www.ipol.im/pub/art/2011/bcm_nlm/) | 在较大区域按相似性选择样本并平均，附实现 | 去噪参考方法；搜索有开销，压缩收益需另外测量 |
| [Ma 等，Rate-Perception Optimized Preprocessing for Video Coding，2023](https://arxiv.org/html/2301.10455v1) | 用自适应DCT、重建/感知损失训练轻量网络，部署于编码器前 | 独立前处理位置与本题一致，保护重要高频；不证明本题0.3%或本机CPU约束达标 |
| [Zhang 等，A Survey on Perceptually Optimized Video Coding](https://arxiv.org/html/2112.12284v2) | 从人眼模型到编码优化的综述 | 建立知识地图；其中内部编码优化不能直接作为本题改动 |
| [Siniukov 等，Hacking VMAF and VMAF NEG，2021](https://arxiv.org/abs/2107.04510) | 前处理对VMAF/NEG的影响与指标脆弱性 | 同时检查保真、NEG和画面，不能把指标增长等同人眼收益 |

以上为文献调研，RPP的“压缩友好且保护重要高频”可作为设计参考，网络路线还需独立评估训练数据、Windows/C++部署和CPU推理。

### 1.4.3 前处理路线比较

| 方向 | 可能作用 | 风险 | 本项目状态 |
|---|---|---|---|
| 空域保边平滑 | 减少邻域小扰动，保护强梯度 | 真实细纹理被当作噪声，VMAF下降 | 已测`legacy`、`smooth`；范围门控均值，非完整双边滤波 |
| 仅色度平滑 | 减少U/V残差，保持输入Y | 色彩边缘受损；联合码率控制仍会影响解码Y | 已测`chroma` |
| 限幅细节增强 | 增强部分结构，减轻模糊 | 噪声/光晕、码率与保真损失、指标奖励 | 已测`sharp`，只处理Y，U/V复制 |
| 增强+色度平滑 | 尝试用色度简化抵消亮度增强开销 | 效果不一定相加，可能改变码率分配 | 已测`hybrid`，未稳定通过约束 |
| 运动补偿时域去噪 | 减少跨帧非相关噪声 | 估计错误、拖影、切镜污染和状态开销 | 未实现，需确认接口状态生命周期 |
| JND/纹理/显著性门控 | 选择可容忍或非关键位置处理 | 模型误判与观看条件依赖 | 已增加亮度/结构/块纹理/整帧上下文启发式门控；没有完整JND或显著性模型 |
| 频域选择性处理 | 区分可省略系数与重要高频 | 变换开销、块边界和纹理损失 | 文献方向，未实现自适应DCT前处理 |
| 学习型前处理 | 学习码率、保真与感知的联合权衡 | 泛化、训练目标偏差与CPU成本 | 未训练或部署网络 |
| 亮度/对比度映射 | 改变局部可见性和像素分布 | 系统性偏差、闪烁、创作意图变化 | 未实现，严格保真约束下暂缓 |

历史`sharp:1`在Beauty全600帧/x265 medium取得PSNR BD-Rate −0.1274%、VMAF BD-Rate −0.1641%，但在另一Beauty片段和Foreman上出现VMAF损失。2026-10-14新增结构门控、组合、局部纹理与整帧上下文：组合方案在Beauty全长改善到−0.1914%/−0.2834%，但独立高清素材仍暴露保真失效。完整成功、失败和后端差异见`REPORT.md`，不能只展示某个有利条件。

可研究局部候选修改量\(\delta_i\)与自适应幅度\(\tau_i\)：

\[
x'_i=\operatorname{clip}_{[0,255]}\left[x_i+
\operatorname{clip}(\delta_i,-\tau_i,\tau_i)\right]
\]

\(\tau_i\)可由噪声、亮度、纹理和结构保护规则决定。当前新候选的每样本±1上限只能控制输入扰动，不能保证编码后的PSNR BD-Rate≤0.3%。最终仍须多点编码测量、保真/感知检查和总耗时验证。

### 1.4.4 已实现的感知启发式与验证边界

新增`perceptual`用亮度保护、局部活动度与方向一致性选择增强位置；`balanced`额外抑制弱梯度区域四方向一致的小峰/谷；`adaptive`在16×16块中保护密集真实纹理；`context`尝试整帧三个活动区间，其失败结果也保留。最终探索候选`content`简化为整帧平均梯度<9采用balanced，否则采用局部adaptive，没有视频名称、场景标签或参考评分分支。

梯度、活动度和高通残差为\(g=|L-R|+|U-D|\)、\(A=\sum|c-n|\)、\(h=4c-\sum n\)。它们只是低成本结构/频率代理，不是完整CSF。亮度范围24–231外保持原值，活动度阈值在中间亮度与较暗/亮区域不同，输出每样本仍限幅±1，纯亮度候选的U/V保持原值。阈值来自已知素材上的探索设计，不能称为心理物理标定的JND。

整帧策略的切换也会改变编码参考与离散决策，不能假定两个各自有效的方法混合后仍有效。已知Beauty/Foreman/Mobile参与了调试；CrowdRun/DucksTakeOff固定参数后验证，发现失败后没有调整当前content阈值。补充色度实验属于已有固定方法的诊断扩展，不据此宣称形成独立盲测的通用最优方法。

后续新增`guarded`风险门控：宽≥1280、高≥720且输入整帧平均梯度≥10时，保留输入Y、只执行固定chroma:4；其他情况采用content:2。这利用亮度保护与较小色度扰动预算，针对已观察到的高活动高清失效。在当前五段素材的六组HEVC条件过了本地约束，但两段新高清已参与它的设计，最终只能视为回归验证，仍需新留出集。输入Y不变也不保证解码Y不变，门槛仍靠编码测量。

部分新策略在已编码条件下输出完全等价，已在每个质量点比较全部帧的处理字节与SHA256后复用对应编码质量。报告明确区分“新编码测量”与“像素等价复用”，后者不能提供新的独立速度证据。官方脚本/编码器未知，严格过本地门槛仍只证明当前条件。

## 1.5 数据选取推荐

### 1.5.1 当前数据与缺口

| 数据 | 规格与用途 | 局限 |
|---|---|---|
| Beauty | 1920×1080、120fps、600帧、8-bit YUV420P；主筛选与全长验证 | 单一人像不能代表快运动、文字或低光噪声 |
| Foreman CIF | 352×288、30000/1001fps、300帧；独立人像/镜头运动诊断 | 不能替代独立高清内容 |
| Mobile CIF | 同上；复杂纹理/运动诊断 | 低分辨率收益不能直接推定高清收益 |
| CrowdRun HD | Xiph/SVT的1920×1080、50fps、8-bit YUV420P；前128个连续完整帧 | 独立运动/复杂纹理验证，未覆盖全部500帧 |
| DucksTakeOff HD | 同上；水面、羽毛与运动细节，前128帧 | 独立高清硬约束诊断；不能将失败略去或扩大为全长结论 |

Foreman/Mobile来源、帧数、SHA256和容器剥离方式见`datasets/manifest.json`。Xiph提示部分历史帧率是推断值，本地遵循Y4M头，不将其当作已证实的拍摄帧率。[Xiph 序列库](https://media.xiph.org/video/derf/)。

### 1.5.2 优先补充的公开内容

| 内容类型 | 推荐来源/候选 | 检验问题 | 优先级 |
|---|---|---|---|
| 快运动与相机跟随 | UVG：Jockey、ReadySetGo | 运动细节、预测与滤波稳定性 | 高 |
| 自然纹理与复杂背景 | UVG：HoneyBee、Bosphorus | 纹理/噪声区分、重要高频保护 | 高 |
| 高清人像 | 保留Beauty并加入独立高清人像 | 发丝、皮肤和轮廓迁移 | 高 |
| 屏幕文字/UI | 有来源与授权说明的原生高清录屏 | 小字、锐利轮廓、色度边缘 | 高 |
| 低光与噪声 | 有来源与授权说明的低光视频 | 去噪收益与真实细节损失 | 高 |
| 动画/平坦渐变 | Xiph动画内容或授权原生素材 | 条带、轮廓和闪烁 | 中 |

尝试下载Jockey/HoneyBee时UVG服务器连接超时，未获得可用文件；本轮已改用CrowdRun/DucksTakeOff的连续高清前缀。后续优先增加文字、低光，并扩大独立视频全长覆盖。仍可选择[UVG官方数据集](https://ultravideo.fi/dataset.html)的1080p、8-bit版本，逐文件核对帧数/FPS/采样/许可，不能把原始摄影规格当成每个下载文件的规格。

[Xiph Test Media](https://media.xiph.org/)可补充其他内容。若下载参考已是有损编码，需记录其既有压缩，不能与无压缩采集参考混用并隐去来源差异。

### 1.5.3 选取与验证原则

1. 按**独立视频内容**划分筛选和验证集。同视频不同片段只是内容内验证；留出集不继续用于调参。本次属于探索性实验，弱候选全长复核是在强候选失效后追加，不是预注册的最终验证。
2. 保留原尺寸、FPS和内容，禁止以超分、插帧、降分辨率、改变FPS取得比赛收益。连续短片段用于初筛，最终覆盖全长/足够GOP；合成图只用于正确性检查。
3. 优先8-bit YUV420P。Y4M可仅剥离容器；其他转换需记录位深、色彩范围与采样。正式接口若带stride，应单独适配。
4. 每个“视频×编码器×配置”分别计算至少四点BD-Rate，不跨视频拼曲线，不按跨标准同值CRF宣称同等质量。
5. 保存失败、最差内容和时间结果。检查Y/YUV PSNR、VMAF、NEG、像素改变量、画面及前处理+编码耗时；平均收益不能掩盖超限。
6. 保留来源与许可。本地Beauty版权文件声明Digiturk所有、CC BY-NC 3.0；其他候选分别核对，公开可下载不等于任意再分发/商用。

官方脚本发布后，先用identity确认帧对齐和零BD-Rate，再接入候选，核对PSNR平面、模型、码率定义、积分算法、测试点和汇总权重。开源后端结果是赛前证据，不能提前替代正式结论。
