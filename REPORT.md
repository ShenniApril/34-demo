# 34题赛前开发与验证报告

更新日期：2026-10-14

## 当前候选与硬约束检查

接受条件：YUV综合与Y-PSNR的PCHIP、三次插值四个结果全部≤+0.3%，同时普通VMAF BD-Rate<0。表中的“PSNR最坏值”为这四项的最大值，判定使用未舍入数值；NEG另列诊断，不替代主指标。

| 内容/范围 | 标准 | 前处理 | PSNR最坏值 | VMAF BD-Rate | NEG BD-Rate | 本条件下接受 |
|---|---|---|---:|---:|---:|---|
| Beauty HD，帧0–599 | HEVC / x265 | guarded:2 | -0.1914% | -0.2834% | -0.2494% | 是 |
| Beauty HD，帧256–447 | HEVC / x265 | guarded:2 | -0.0511% | -0.1570% | -0.1638% | 是 |
| Foreman CIF，帧0–299 | HEVC / x265 | guarded:2 | -0.4567% | -0.4092% | -0.4498% | 是 |
| Mobile CIF，帧0–299 | HEVC / x265 | guarded:2 | +0.0973% | -0.3183% | -0.1642% | 是 |
| CrowdRun HD，帧0–127 | HEVC / x265 | guarded:2 | +0.0000% | -0.1562% | -0.1849% | 是 |
| DucksTakeOff HD，帧0–127 | HEVC / x265 | guarded:2 | +0.0666% | -0.4697% | -0.4803% | 是 |
| Beauty HD，帧256–447 | AVC / x264 | guarded:2 | -0.1314% | +0.1323% | +0.1275% | 否 |
| Beauty HD，帧256–447 | AV1 / SVT-AV1 | guarded:2 | -0.0637% | -1.8547% | -1.3772% | 是 |
| Beauty HD，帧256–447 | VVC / VVenC | guarded:2 | +0.0525% | -0.3737% | -0.3287% | 是 |
| Beauty HD，帧256–447 | AV1 / SVT-AV1 | hybrid:2 | -9.8182% | -11.8006% | -10.9363% | 是 |
| Beauty HD，帧256–447 | AV1 / SVT-AV1 | perceptual:2 | +0.2164% | -2.4714% | -2.0043% | 是 |
| Beauty HD，帧256–447 | VVC / VVenC | perceptual:2 | -0.0182% | -0.8884% | -0.6062% | 是 |

上述最新验证条目中，11项同时过保真约束并取得VMAF收益，1项未满足联合条件。这里只统计列出的条件，不作为不同标准、帧数或分辨率的混合平均分。

最终HEVC候选guarded:2在当前五段素材的六组条件中均过本地保真筛选并取得VMAF收益。前四组经过每个质量点全部处理字节相等后复用原编码质量，两组高清重新编码；这是回归结果，不是六次新独立编码验证。content原先在DucksTakeOff未过PSNR、CrowdRun未取得VMAF收益，失败记录仍保留。

风险门控是在观察新增高清失败、补测chroma:4后设计，因此CrowdRun/DucksTakeOff已经参与最终方案设计，不能再称最终guarded的独立盲测集。它只使用分辨率与输入梯度，不查询视频名称/标签，但仍可能对这五段素材过拟合。需要新的独立全长高清集及官方配置复核。

更稳妥的局部条件候选：Beauty/x264 medium 192帧的sharp:1（最坏PSNR +0.1861%、VMAF −0.2481%）；Beauty/SVT-AV1 preset8 192帧的hybrid:2（最坏PSNR −9.8182%、VMAF −11.8006%）；Beauty/VVenC faster 192帧的perceptual:2（最坏PSNR −0.0182%、VMAF −0.8884%）。这些是不同标准各自相对基线的收益，不能把AV1大收益当作正式HEVC赛题收益。

![HEVC回归结果](D:/shenni/交大/Hackthon/34-demo/results/guarded_regression.png)

## 方案如何结合人眼感知理论

本模块部署在编码器外部，不修改编码器源码；每组baseline/opt使用相同编码配置，都相对未处理原始帧评测。优化目标是在PSNR BD-Rate硬约束内降低VMAF BD-Rate。像素限幅是输入扰动控制，不是编码后BD-Rate保证。

### 新增的可执行策略

| 方案 | 理论启发与实际规则 | 当前实现边界 |
|---|---|---|
| perceptual | 用亮度、邻域活动度和方向一致性保护结构；深暗/高亮保持原值，只增强有邻域支持的低至中等对比细节 | 不是完整JND/CSF模型，不检测人脸或文字 |
| balanced | 在perceptual外，抑制弱梯度邻域中四方向一致的小孤立峰/谷，尝试减少随机扰动 | 单帧处理；不能把真实颗粒都看作噪声 |
| adaptive | 16×16块纹理密度较高时回退到更弱增强，其余使用balanced；保护真实纹理 | 局部块决策可能改变收益，已保留失败结果 |
| context | 整帧均值<12用balanced，≥40用弱增强，中间用局部adaptive；保护暗部/高亮，U/V复制 | 探索性阈值，非JND标定 |
| content | 整帧均值<9用balanced，否则用局部adaptive，取消整帧弱增强分支 | 固定后独立高清验证失效，未调整该阈值 |
| guarded | 宽≥1280、高≥720且整帧平均梯度≥10时保留输入Y，只执行chroma:4；其他情况采用content:2 | 后续回归风险门控，不保证未知内容/分辨率必然过BD-Rate |

令中心为c，四邻点为L/R/U/D：g=|L−R|+|U−D|，A=Σ|c−邻点|，h=4c−L−R−U−D。增强要求24≤c≤231、6≤g<32、2g≥A，A≤36（中间亮度）或48（较暗/亮区域）；|h|达到强度阈值才修改±1。balanced小峰抑制要求g≤4、8≤A≤20、|h|≥12且四方向同为峰或谷。

amount=2时，前处理CRF提示<26会把增强降到强度1；其他提示使用强度2。局部adaptive按输入块梯度均值≥12或强梯度比例≥25%选择弱增强。context/content的整帧均值每4像素采样，局部每2像素采样；仅保存复用工作缓冲，不保存过去帧状态。

这些规则借鉴亮度掩蔽、纹理掩蔽与结构保护，但真实纹理也可能重要，因此高活动区域采用保护优先的弱处理。当前没有复现完整NLM、双边滤波、时域运动补偿、自适应DCT或神经网络；这些仍属于文献/后续方向。论文依据和数据选取见[KNOWLEDGE.md](D:/shenni/交大/Hackthon/34-demo/KNOWLEDGE.md)。

### 迭代过程与选择偏差

初版弱增强在Beauty全长有小收益，但在另一片段和Foreman失效。结构门控与小峰抑制改善Beauty/Foreman，却在Mobile失效；局部纹理回退改善Mobile，但损失了Beauty片段收益。context据此引入整帧上下文，但Foreman有12/300帧跨过阈值12，混合策略效果变差；该观察提示切换与编码参考的耦合，尚未做专门因果消融。

content将阈值改为9并取消整帧弱增强分支；全帧梯度记录保存在results/context_features_all_frames.json。Beauty/Foreman/Mobile参与设计，不是盲测集。CrowdRun/DucksTakeOff最初在固定参数后验证content并暴露失效；之后色度补测通过它们，但在Beauty/Foreman失效，故新增guarded风险门控。它们各128连续帧，最终已成为回归素材，并非未参与设计的独立集或完整500帧。

## 压缩标准与前处理覆盖

已完成的评测分别使用x265、x264、SVT-AV1与VVenC。这里补齐的是已实现方法在四标准上的代表性强度；并非每个强度、每个视频、每种preset的全组合。AV1其他实现libaom/rav1e未评测，算法文献方向也不能算作已测试方法。

| 模式/思路 | HEVC/x265 amount | AVC/x264 amount | AV1/SVT-AV1 amount | VVC/VVenC amount |
|---|---|---|---|---|
| identity：原样复制；各组基线 | 0 | 0 | 0 | 0 |
| legacy：Y/U/V范围门控均值；复现旧版，无新方案的±1限制 | 16 | 16 | 16 | 16 |
| smooth：Y/U/V弱混合保边平滑，±1限幅 | 2、4 | 4 | 4 | 4 |
| chroma：仅U/V平滑，Y复制，±1限幅 | 4、16 | 4 | 4 | 4 |
| sharp：仅Y十字高通增强，梯度门控，±1限幅 | 1、2、4 | 1、2 | 1 | 1 |
| hybrid：Y增强＋U/V平滑，±1限幅 | 2、4 | 2 | 2 | 2 |
| perceptual：亮度保护＋活动度/结构一致性门控增强，仅Y | 1、2 | 2 | 2 | 2 |
| balanced：perceptual＋弱梯度孤立小峰抑制，仅Y | 1、2 | 2 | 2 | 2 |
| adaptive：16×16纹理块在balanced与弱sharp间选择，仅Y | 2 | 2 | 2 | 2 |
| context：整帧纹理上下文＋局部块选择，暗部/高亮保护，仅Y | 2 | 2 | 2 | 2 |
| content：低活动帧balanced、其余局部adaptive，固定阈值9，仅Y | 2 | 2 | 2 | 2 |
| guarded：高活动高清仅色度轻平滑；其余content，回归风险门控 | 2 | 2 | 2 | 2 |

### 不同标准的固定评测协议

| 标准 | 质量控制/测试点 | preset与线程 | 输入/评价像素域 | 其他固定设置 |
|---|---|---|---|---|
| HEVC/x265 | CRF 22/26/30/34 | veryfast或medium；pools=4、frame-threads=1 | 8-bit YUV420P | keyint=min-keyint=120、scenecut=0 |
| AVC/x264 | CRF 22/26/30/34 | veryfast或medium；threads=4 | 8-bit YUV420P | keyint=min-keyint=120、scenecut=0 |
| AV1/SVT-AV1 | CRF 24/30/36/42 | preset=8、lp=4 | 8-bit YUV420P | GOP=120、film-grain=0；日志确认默认PSNR tune，内部过滤保持库默认 |
| VVC/VVenC | QP 22/27/32/37 | faster、Threads=4 | 两路8→10编码；解码统一10→8后与原始8-bit比较 | QPA=1、IntraPeriod=128、GOPSize=32；固定无抖动位深转换 |

AV1/VVC的前处理CRF提示显式固定为28，不把它与AV1 CRF或VVC QP宣称等价。VVC转换已对0–255全部代码验证8→10→8原样返回，但有损VVC输出仍可能产生正常的舍入误差。VVC结果仅适用于本轮10-bit编码包装和8-bit评价口径，不能当成官方原生8-bit评测已复现。

VMAF固定为v0.6.1，NEG固定为v0.6.1neg，所有帧均评价。码率由视频包字节和真实帧数/FPS计算，不含MP4封装。模型、共同质量区间、插值、解码位深和baseline复用均记录在manifest/summary中。不同标准的同值数值不能直接比较质量，本报告不排名其绝对压缩效率。

旧脚本沿用crf字段/部分文件名；VVC的真实质量参数以manifest/quality_mode=qp及编码命令中的-qp为准。新context脚本已将VVC结果文件命名为qp。

![四标准代表性筛选](D:/shenni/交大/Hackthon/34-demo/results/four_standard_screening.png)

## 全部已完成实验结果

以下保留历史、筛选、验证及失败方案。PSNR/YUV、Y、VMAF、NEG列为PCHIP BD-Rate百分比；最坏PSNR同时考虑两个平面口径与两种插值。质量无有效曲线时不判定达标。

### screen_v3：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–63，共64帧；CRF点[22, 26, 30, 34]；preset=veryfast；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| chroma:4 | -0.3127% | -0.2393% | +0.1653% | -0.0225% | -0.2393% | 是 | 否 | +114.83% |
| legacy:16 | -3.5147% | -3.1373% | +0.6020% | -0.2025% | -3.1373% | 是 | 否 | +381.75% |
| sharp:1 | -0.2950% | -0.1665% | -0.2684% | -0.3265% | -0.1665% | 是 | 是 | +94.30% |
| smooth:2 | +0.1265% | +0.1938% | +0.3620% | +0.2634% | +0.1938% | 是 | 否 | +357.21% |
| smooth:4 | -0.7646% | -0.6855% | +0.0995% | -0.0114% | -0.6855% | 是 | 否 | +329.21% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/screen_v3/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/screen_v3/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/screen_v3/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### screen_hybrid：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–63，共64帧；CRF点[22, 26, 30, 34]；preset=veryfast；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| chroma:16 | -0.1407% | +0.1194% | +0.0415% | -0.0571% | +0.1307% | 是 | 否 | +54.04% |
| hybrid:2 | +0.2648% | +0.4923% | -0.0717% | +0.0073% | +0.4923% | 否 | 否 | +70.38% |
| hybrid:4 | +0.9662% | +1.2099% | -2.2401% | -1.7420% | +1.2800% | 否 | 否 | +72.56% |
| sharp:2 | -0.0245% | +0.0499% | -0.5662% | -0.4738% | +0.0595% | 是 | 是 | +28.82% |
| sharp:4 | +1.3218% | +1.2000% | -0.5904% | -0.2015% | +1.4015% | 否 | 否 | +33.83% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/screen_hybrid/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/screen_hybrid/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/screen_hybrid/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### holdout_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| sharp:1 | -0.0138% | +0.0198% | +0.3092% | +0.2154% | +0.0359% | 是 | 否 | +34.02% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/holdout_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/holdout_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/holdout_x265/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### full_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–599，共600帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| hybrid:2 | +0.7079% | +0.5507% | -0.3381% | -0.1829% | +0.7181% | 否 | 否 | +35.50% |
| sharp:2 | +0.5991% | +0.4554% | -0.4841% | -0.3256% | +0.6542% | 否 | 否 | +21.03% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/full_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/full_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/full_x265/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### full_sharp1：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–599，共600帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| sharp:1 | -0.1274% | -0.1680% | -0.1641% | -0.1273% | -0.1274% | 是 | 是 | +13.62% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/full_sharp1/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/full_sharp1/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/full_sharp1/manifest.json)。
baseline复用自`results/full_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### holdout_x264：Beauty HD / AVC / x264

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| sharp:1 | +0.1566% | +0.1861% | -0.2481% | -0.2449% | +0.1861% | 是 | 是 | +16.92% |
| sharp:2 | +0.3822% | +0.3784% | -0.3777% | -0.2708% | +0.5001% | 否 | 否 | +16.56% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/holdout_x264/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/holdout_x264/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/holdout_x264/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### foreman_x265：Foreman CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| sharp:1 | +0.0885% | +0.0124% | +0.7053% | +0.6510% | +0.0885% | 是 | 否 | +9.00% |
| sharp:2 | -0.0105% | -0.2059% | -0.1182% | +0.1255% | -0.0105% | 是 | 是 | +9.10% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/foreman_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/foreman_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/foreman_x265/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### mobile_x265：Mobile CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| sharp:1 | +0.0469% | -0.0047% | -0.4690% | -0.1174% | +0.0493% | 是 | 是 | +34.25% |
| sharp:2 | +0.0746% | +0.0203% | +0.1807% | +0.2378% | +0.0768% | 是 | 否 | -2.31% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/mobile_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/mobile_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/mobile_x265/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v2_foreman_x265：Foreman CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | -0.3046% | -0.3908% | -0.4339% | -0.2765% | -0.3045% | 是 | 是 | +13.06% |
| perceptual:2 | -0.4800% | -0.5717% | -0.7518% | -0.8210% | -0.4800% | 是 | 是 | +5.76% |
| sharp:1 | +0.0885% | +0.0124% | +0.7053% | +0.6510% | +0.0885% | 是 | 否 | +3.61% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v2_foreman_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v2_foreman_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v2_foreman_x265/manifest.json)。
baseline复用自`results/foreman_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v2_full_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–599，共600帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | -0.1914% | -0.2225% | -0.2834% | -0.2494% | -0.1914% | 是 | 是 | +30.53% |
| sharp:1 | -0.1274% | -0.1680% | -0.1641% | -0.1273% | -0.1274% | 是 | 是 | +10.84% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v2_full_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v2_full_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v2_full_x265/manifest.json)。
baseline复用自`results/full_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v2_holdout_x264：Beauty HD / AVC / x264

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | -0.1697% | -0.1605% | +0.1323% | +0.1275% | -0.1314% | 是 | 否 | +41.49% |
| sharp:1 | +0.1566% | +0.1861% | -0.2481% | -0.2449% | +0.1861% | 是 | 是 | +16.12% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v2_holdout_x264/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v2_holdout_x264/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v2_holdout_x264/manifest.json)。
baseline复用自`results/holdout_x264`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v2_holdout_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | -0.1473% | -0.0594% | -0.1570% | -0.1638% | -0.0511% | 是 | 是 | +84.61% |
| perceptual:2 | +0.2100% | +0.2341% | +0.0954% | +0.1495% | +0.2563% | 是 | 否 | +89.31% |
| sharp:1 | -0.0138% | +0.0198% | +0.3092% | +0.2154% | +0.0359% | 是 | 否 | +64.39% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v2_holdout_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v2_holdout_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v2_holdout_x265/manifest.json)。
baseline复用自`results/holdout_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v2_mobile_x265：Mobile CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | +0.2406% | +0.2435% | +0.4002% | +0.2985% | +0.2456% | 是 | 否 | +0.52% |
| perceptual:2 | +0.0209% | -0.0132% | +0.3456% | +0.2609% | +0.0233% | 是 | 否 | -0.42% |
| sharp:1 | +0.0469% | -0.0047% | -0.4690% | -0.1174% | +0.0493% | 是 | 是 | -4.75% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v2_mobile_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v2_mobile_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v2_mobile_x265/manifest.json)。
baseline复用自`results/mobile_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v2_screen_av1：Beauty HD / AV1 / SVT-AV1

输入1920×1080、120fps；帧0–63，共64帧；CRF点[24, 30, 36, 42]；preset=8；GOP=120；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | -0.2598% | -0.2287% | -1.8204% | -1.5864% | -0.2185% | 是 | 是 | +50.63% |
| chroma:4 | -9.3900% | -3.6354% | -2.9906% | -3.0903% | -3.6354% | 是 | 是 | +46.79% |
| hybrid:2 | -18.3560% | -9.0284% | -11.0408% | -10.3634% | -9.0284% | 是 | 是 | +44.78% |
| legacy:16 | -13.4781% | -1.1424% | +5.4263% | +1.4685% | -1.0911% | 是 | 否 | +132.85% |
| perceptual:2 | -0.5036% | -0.5943% | -2.3711% | -1.9731% | -0.4642% | 是 | 是 | +46.75% |
| sharp:1 | -0.0217% | -0.0374% | -0.5060% | -0.6455% | +0.0074% | 是 | 是 | +19.70% |
| smooth:4 | -8.8319% | -2.0748% | -0.1815% | -1.1846% | -2.0682% | 是 | 是 | +115.02% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_av1/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_av1/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_av1/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v2_screen_vvc：Beauty HD / VVC / VVenC

输入1920×1080、120fps；帧0–63，共64帧；QP点[22, 27, 32, 37]；preset=faster；GOP=128；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | +0.3006% | +0.2614% | -1.6237% | -1.1752% | +0.3006% | 否 | 否 | +13.11% |
| chroma:4 | -0.2702% | -0.4580% | -1.1491% | -0.8598% | -0.2702% | 是 | 是 | +4.16% |
| hybrid:2 | +0.2550% | +0.1111% | -2.3129% | -1.5759% | +0.2550% | 是 | 是 | +18.98% |
| legacy:16 | +6.7884% | +7.3859% | +13.1717% | +10.5092% | +7.3859% | 否 | 否 | +31.61% |
| perceptual:2 | -0.1409% | -0.1769% | -2.1128% | -1.6461% | -0.1409% | 是 | 是 | +21.05% |
| sharp:1 | -0.0054% | -0.0319% | -1.2991% | -0.8865% | -0.0054% | 是 | 是 | +12.20% |
| smooth:4 | +0.1419% | +0.3242% | +1.6008% | +1.4091% | +0.3242% | 否 | 否 | +17.40% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_vvc/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_vvc/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_vvc/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v2_screen_x264：Beauty HD / AVC / x264

输入1920×1080、120fps；帧0–63，共64帧；CRF点[22, 26, 30, 34]；preset=veryfast；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | +0.0881% | +0.1244% | +0.1517% | +0.2906% | +0.1244% | 是 | 否 | +59.18% |
| chroma:4 | +0.0610% | +0.1901% | -0.1009% | -0.0374% | +0.1901% | 是 | 是 | +61.59% |
| hybrid:2 | -0.2609% | -0.1874% | -0.3282% | -0.2378% | -0.1874% | 是 | 是 | +63.34% |
| legacy:16 | -1.8347% | -1.3475% | +2.9685% | +2.7645% | -1.3475% | 是 | 否 | +164.79% |
| perceptual:2 | -0.2041% | -0.2497% | -0.0167% | +0.0938% | -0.1126% | 是 | 是 | +57.99% |
| sharp:1 | -0.1976% | -0.2749% | +0.5407% | +0.5590% | -0.1465% | 是 | 否 | +23.71% |
| smooth:4 | -1.0760% | -0.9297% | +0.6809% | +0.7648% | -0.9297% | 是 | 否 | +153.58% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_x264/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_x264/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_x264/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v2_screen_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–63，共64帧；CRF点[22, 26, 30, 34]；preset=veryfast；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:1 | -0.3443% | -0.2602% | +0.5434% | +0.5277% | -0.2537% | 是 | 否 | +38.67% |
| balanced:2 | +0.0269% | -0.1257% | -0.5954% | -0.4932% | +0.0269% | 是 | 是 | +48.96% |
| perceptual:1 | +0.4136% | +0.3418% | +0.1899% | +0.2303% | +0.4328% | 否 | 否 | +58.08% |
| perceptual:2 | -0.3037% | -0.1126% | -0.8399% | -0.7805% | -0.1126% | 是 | 是 | +51.17% |
| sharp:1 | -0.2950% | -0.1665% | -0.2684% | -0.3265% | -0.1665% | 是 | 是 | +14.66% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v2_screen_x265/manifest.json)。
baseline复用自`results/screen_v3`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v3_foreman_x265：Foreman CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| adaptive:2 | -0.4567% | -0.5266% | -0.4092% | -0.4498% | -0.4567% | 是 | 是 | +5.28% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v3_foreman_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v3_foreman_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v3_foreman_x265/manifest.json)。
baseline复用自`results/foreman_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v3_full_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–599，共600帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| adaptive:2 | -0.1664% | -0.2779% | -0.1413% | -0.1620% | -0.1642% | 是 | 是 | +50.73% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v3_full_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v3_full_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v3_full_x265/manifest.json)。
baseline复用自`results/full_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v3_holdout_x264：Beauty HD / AVC / x264

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| adaptive:2 | -0.1382% | -0.1236% | +0.3672% | +0.3097% | -0.1230% | 是 | 否 | +30.62% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v3_holdout_x264/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v3_holdout_x264/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v3_holdout_x264/manifest.json)。
baseline复用自`results/holdout_x264`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v3_holdout_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| adaptive:2 | -0.1201% | -0.1294% | +0.1809% | +0.1145% | -0.1201% | 是 | 否 | +57.62% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v3_holdout_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v3_holdout_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v3_holdout_x265/manifest.json)。
baseline复用自`results/holdout_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v3_mobile_x265：Mobile CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| adaptive:2 | +0.0950% | +0.0428% | -0.3183% | -0.1642% | +0.0973% | 是 | 是 | +2.02% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v3_mobile_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v3_mobile_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v3_mobile_x265/manifest.json)。
baseline复用自`results/mobile_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v3_screen_av1：Beauty HD / AV1 / SVT-AV1

输入1920×1080、120fps；帧0–63，共64帧；CRF点[24, 30, 36, 42]；preset=8；GOP=120；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| adaptive:2 | +0.1617% | +0.1878% | -0.3898% | -0.5412% | +0.1878% | 是 | 是 | +37.66% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v3_screen_av1/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v3_screen_av1/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v3_screen_av1/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v3_screen_vvc：Beauty HD / VVC / VVenC

输入1920×1080、120fps；帧0–63，共64帧；QP点[22, 27, 32, 37]；preset=faster；GOP=128；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| adaptive:2 | +0.1072% | +0.0965% | -0.7151% | -0.5928% | +0.1072% | 是 | 是 | +6.69% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v3_screen_vvc/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v3_screen_vvc/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v3_screen_vvc/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v4_crowd_run_1080p50_x265：CrowdRun HD / HEVC / x265

输入1920×1080、50.0fps；帧0–127，共128帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | +0.0653% | +0.0175% | -0.0881% | +0.0407% | +0.0681% | 是 | 是 | +3.76% |
| context:2 | +0.1664% | +0.0936% | +0.0455% | +0.1596% | +0.1679% | 是 | 否 | +6.88% |
| sharp:1 | +0.0688% | -0.0064% | -0.0846% | +0.0493% | +0.0702% | 是 | 是 | +7.80% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v4_crowd_run_1080p50_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v4_crowd_run_1080p50_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v4_crowd_run_1080p50_x265/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v4_ducks_take_off_1080p50_x265：DucksTakeOff HD / HEVC / x265

输入1920×1080、50.0fps；帧0–127，共128帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| balanced:2 | +0.3524% | +0.2910% | -0.3017% | -0.0843% | +0.3524% | 否 | 否 | +1.71% |
| context:2 | +0.5875% | +0.4753% | +0.1977% | +0.3653% | +0.5875% | 否 | 否 | +14.06% |
| sharp:1 | +0.5705% | +0.4742% | +0.0034% | +0.2229% | +0.5705% | 否 | 否 | +0.95% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v4_ducks_take_off_1080p50_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v4_ducks_take_off_1080p50_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v4_ducks_take_off_1080p50_x265/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v4_foreman_x265：Foreman CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| context:2 | -0.2794% | -0.3463% | +0.1872% | +0.0589% | -0.2794% | 是 | 否 | +5.44% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v4_foreman_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v4_foreman_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v4_foreman_x265/manifest.json)。
baseline复用自`results/foreman_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v4_full_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–599，共600帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| context:2 | -0.1914% | -0.2225% | -0.2834% | -0.2494% | -0.1914% | 是 | 是 | +9.50% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v4_full_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v4_full_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v4_full_x265/manifest.json)。
baseline复用自`results/full_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v4_holdout_av1：Beauty HD / AV1 / SVT-AV1

输入1920×1080、120fps；帧256–447，共192帧；CRF点[24, 30, 36, 42]；preset=8；GOP=120；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| context:2 | -0.0637% | -0.2391% | -1.8547% | -1.3772% | -0.0637% | 是 | 是 | +26.33% |
| hybrid:2 | -23.4350% | -9.8182% | -11.8006% | -10.9363% | -9.8182% | 是 | 是 | +56.79% |
| perceptual:2 | -0.1631% | -0.7683% | -2.4714% | -2.0043% | +0.2164% | 是 | 是 | +25.43% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_av1/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_av1/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_av1/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v4_holdout_vvc：Beauty HD / VVC / VVenC

输入1920×1080、120fps；帧256–447，共192帧；QP点[22, 27, 32, 37]；preset=faster；GOP=128；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| context:2 | -0.0256% | +0.0189% | -0.3737% | -0.3287% | +0.0525% | 是 | 是 | +1.01% |
| perceptual:2 | -0.0512% | -0.0640% | -0.8884% | -0.6062% | -0.0182% | 是 | 是 | +0.08% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_vvc/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_vvc/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_vvc/manifest.json)。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v4_holdout_x264：Beauty HD / AVC / x264

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| context:2 | -0.1697% | -0.1605% | +0.1323% | +0.1275% | -0.1314% | 是 | 否 | +15.96% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_x264/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_x264/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_x264/manifest.json)。
baseline复用自`results/holdout_x264`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v4_holdout_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| context:2 | -0.1473% | -0.0594% | -0.1570% | -0.1638% | -0.0511% | 是 | 是 | +9.56% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v4_holdout_x265/manifest.json)。
baseline复用自`results/holdout_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v4_mobile_x265：Mobile CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| context:2 | +0.1118% | +0.0660% | +0.1083% | +0.1674% | +0.1118% | 是 | 否 | -1.19% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v4_mobile_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v4_mobile_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v4_mobile_x265/manifest.json)。
baseline复用自`results/mobile_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v5_crowd_run_1080p50_x265：CrowdRun HD / HEVC / x265

输入1920×1080、50.0fps；帧0–127，共128帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| content:2 | +0.1664% | +0.0936% | +0.0455% | +0.1596% | +0.1679% | 是 | 否 | -3.44% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v5_crowd_run_1080p50_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v5_crowd_run_1080p50_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v5_crowd_run_1080p50_x265/manifest.json)。
baseline复用自`results/v4_crowd_run_1080p50_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v5_ducks_take_off_1080p50_x265：DucksTakeOff HD / HEVC / x265

输入1920×1080、50.0fps；帧0–127，共128帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| content:2 | +0.5875% | +0.4753% | +0.1977% | +0.3653% | +0.5875% | 否 | 否 | +3.31% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v5_ducks_take_off_1080p50_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v5_ducks_take_off_1080p50_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v5_ducks_take_off_1080p50_x265/manifest.json)。
baseline复用自`results/v4_ducks_take_off_1080p50_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v5_foreman_x265：Foreman CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| content:2 | -0.4567% | -0.5266% | -0.4092% | -0.4498% | -0.4567% | 是 | 是 | +15.42% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v5_foreman_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v5_foreman_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v5_foreman_x265/manifest.json)。
baseline复用自`v3_foreman_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v3_foreman_x265`中的`adaptive:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v5_foreman_x265/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v5_full_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–599，共600帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| content:2 | -0.1914% | -0.2225% | -0.2834% | -0.2494% | -0.1914% | 是 | 是 | +25.97% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v5_full_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v5_full_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v5_full_x265/manifest.json)。
baseline复用自`v2_full_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v2_full_x265`中的`balanced:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v5_full_x265/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v5_holdout_av1：Beauty HD / AV1 / SVT-AV1

输入1920×1080、120fps；帧256–447，共192帧；CRF点[24, 30, 36, 42]；preset=8；GOP=120；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| content:2 | -0.0637% | -0.2391% | -1.8547% | -1.3772% | -0.0637% | 是 | 是 | +244.61% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_av1/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_av1/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_av1/manifest.json)。
baseline复用自`v4_holdout_av1`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v4_holdout_av1`中的`context:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_av1/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v5_holdout_vvc：Beauty HD / VVC / VVenC

输入1920×1080、120fps；帧256–447，共192帧；QP点[22, 27, 32, 37]；preset=faster；GOP=128；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| content:2 | -0.0256% | +0.0189% | -0.3737% | -0.3287% | +0.0525% | 是 | 是 | +0.98% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_vvc/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_vvc/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_vvc/manifest.json)。
baseline复用自`v4_holdout_vvc`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v4_holdout_vvc`中的`context:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_vvc/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v5_holdout_x264：Beauty HD / AVC / x264

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| content:2 | -0.1697% | -0.1605% | +0.1323% | +0.1275% | -0.1314% | 是 | 否 | +17.41% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_x264/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_x264/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_x264/manifest.json)。
baseline复用自`v4_holdout_x264`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v4_holdout_x264`中的`context:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_x264/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v5_holdout_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| content:2 | -0.1473% | -0.0594% | -0.1570% | -0.1638% | -0.0511% | 是 | 是 | +71.05% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_x265/manifest.json)。
baseline复用自`v2_holdout_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v2_holdout_x265`中的`balanced:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v5_holdout_x265/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v5_mobile_x265：Mobile CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| content:2 | +0.0950% | +0.0428% | -0.3183% | -0.1642% | +0.0973% | 是 | 是 | +13.05% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v5_mobile_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v5_mobile_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v5_mobile_x265/manifest.json)。
baseline复用自`v3_mobile_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v3_mobile_x265`中的`adaptive:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v5_mobile_x265/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v6_crowd_run_1080p50_x265：CrowdRun HD / HEVC / x265

输入1920×1080、50.0fps；帧0–127，共128帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| chroma:4 | -0.0018% | -0.3171% | -0.1562% | -0.1849% | +0.0000% | 是 | 是 | +1.57% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v6_crowd_run_1080p50_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v6_crowd_run_1080p50_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v6_crowd_run_1080p50_x265/manifest.json)。
baseline复用自`results/v4_crowd_run_1080p50_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v6_ducks_take_off_1080p50_x265：DucksTakeOff HD / HEVC / x265

输入1920×1080、50.0fps；帧0–127，共128帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| chroma:4 | +0.0666% | -0.4449% | -0.4697% | -0.4803% | +0.0666% | 是 | 是 | +0.42% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v6_ducks_take_off_1080p50_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v6_ducks_take_off_1080p50_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v6_ducks_take_off_1080p50_x265/manifest.json)。
baseline复用自`results/v4_ducks_take_off_1080p50_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v6_foreman_x265：Foreman CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| chroma:4 | +0.1350% | -0.1828% | +0.6057% | +0.1114% | +0.1350% | 是 | 否 | +1.35% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v6_foreman_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v6_foreman_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v6_foreman_x265/manifest.json)。
baseline复用自`results/foreman_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v6_full_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–599，共600帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| chroma:4 | +0.4733% | +0.4253% | +0.5242% | +0.5236% | +0.4733% | 否 | 否 | +8.76% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v6_full_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v6_full_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v6_full_x265/manifest.json)。
baseline复用自`results/full_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v6_holdout_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| chroma:4 | +0.4317% | +0.4049% | +0.9152% | +0.8889% | +0.4317% | 否 | 否 | +20.77% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v6_holdout_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v6_holdout_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v6_holdout_x265/manifest.json)。
baseline复用自`results/holdout_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v6_mobile_x265：Mobile CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| chroma:4 | +0.1220% | -0.2189% | -0.3432% | -0.2962% | +0.1247% | 是 | 是 | -3.81% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v6_mobile_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v6_mobile_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v6_mobile_x265/manifest.json)。
baseline复用自`results/mobile_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v7_crowd_run_1080p50_x265：CrowdRun HD / HEVC / x265

输入1920×1080、50.0fps；帧0–127，共128帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| guarded:2 | -0.0018% | -0.3171% | -0.1562% | -0.1849% | +0.0000% | 是 | 是 | -2.98% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v7_crowd_run_1080p50_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_crowd_run_1080p50_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v7_crowd_run_1080p50_x265/manifest.json)。
baseline复用自`results/v4_crowd_run_1080p50_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v7_ducks_take_off_1080p50_x265：DucksTakeOff HD / HEVC / x265

输入1920×1080、50.0fps；帧0–127，共128帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| guarded:2 | +0.0666% | -0.4449% | -0.4697% | -0.4803% | +0.0666% | 是 | 是 | +3.24% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v7_ducks_take_off_1080p50_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_ducks_take_off_1080p50_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v7_ducks_take_off_1080p50_x265/manifest.json)。
baseline复用自`results/v4_ducks_take_off_1080p50_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v7_foreman_x265：Foreman CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| guarded:2 | -0.4567% | -0.5266% | -0.4092% | -0.4498% | -0.4567% | 是 | 是 | +4.69% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v7_foreman_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_foreman_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v7_foreman_x265/manifest.json)。
baseline复用自`v3_foreman_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v3_foreman_x265`中的`adaptive:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v7_foreman_x265/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v7_full_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧0–599，共600帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| guarded:2 | -0.1914% | -0.2225% | -0.2834% | -0.2494% | -0.1914% | 是 | 是 | +20.68% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v7_full_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_full_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v7_full_x265/manifest.json)。
baseline复用自`v2_full_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v2_full_x265`中的`balanced:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v7_full_x265/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v7_holdout_av1：Beauty HD / AV1 / SVT-AV1

输入1920×1080、120fps；帧256–447，共192帧；CRF点[24, 30, 36, 42]；preset=8；GOP=120；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| guarded:2 | -0.0637% | -0.2391% | -1.8547% | -1.3772% | -0.0637% | 是 | 是 | +26.02% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_av1/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_av1/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_av1/manifest.json)。
baseline复用自`v4_holdout_av1`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v4_holdout_av1`中的`context:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_av1/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v7_holdout_vvc：Beauty HD / VVC / VVenC

输入1920×1080、120fps；帧256–447，共192帧；QP点[22, 27, 32, 37]；preset=faster；GOP=128；前处理提示=28。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| guarded:2 | -0.0256% | +0.0189% | -0.3737% | -0.3287% | +0.0525% | 是 | 是 | +6.51% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_vvc/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_vvc/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_vvc/manifest.json)。
baseline复用自`v4_holdout_vvc`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v4_holdout_vvc`中的`context:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_vvc/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v7_holdout_x264：Beauty HD / AVC / x264

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| guarded:2 | -0.1697% | -0.1605% | +0.1323% | +0.1275% | -0.1314% | 是 | 否 | +17.81% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_x264/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_x264/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_x264/manifest.json)。
baseline复用自`v2_holdout_x264`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v2_holdout_x264`中的`balanced:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_x264/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v7_holdout_x265：Beauty HD / HEVC / x265

输入1920×1080、120fps；帧256–447，共192帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| guarded:2 | -0.1473% | -0.0594% | -0.1570% | -0.1638% | -0.0511% | 是 | 是 | +68.43% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_x265/manifest.json)。
baseline复用自`v2_holdout_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v2_holdout_x265`中的`balanced:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v7_holdout_x265/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

### v7_mobile_x265：Mobile CIF / HEVC / x265

输入352×288、29.97002997003fps；帧0–299，共300帧；CRF点[22, 26, 30, 34]；preset=medium；GOP=120；前处理提示=随x26x CRF。

| 配置 | PSNR YUV | PSNR Y | VMAF | NEG | 最坏PSNR | 保真通过 | 联合接受 | 总墙钟变化* |
|---|---:|---:|---:|---:|---:|---|---|---:|
| guarded:2 | +0.0950% | +0.0428% | -0.3183% | -0.1642% | +0.0973% | 是 | 是 | +0.96% |

[points.csv](D:/shenni/交大/Hackthon/34-demo/results/v7_mobile_x265/points.csv)；[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_mobile_x265/summary.json)；[manifest.json](D:/shenni/交大/Hackthon/34-demo/results/v7_mobile_x265/manifest.json)。
baseline复用自`v3_mobile_x265`，已核对源文件和编码配置、原始片段哈希；复用适用于质量对比，不能直接作为同时段速度对比。
**该组优化质量为像素等价复用，未新编码：**每个质量点全部处理帧与`v3_mobile_x265`中的`adaptive:2`逐字节哈希相等，旧预处理器及原编码视频哈希也核对。证明见[equivalence.json](D:/shenni/交大/Hackthon/34-demo/results/v7_mobile_x265/equivalence.json)。新的前处理时间实测，但编码时间借用旧记录，不作为独立速度证据。
*墙钟变化为一次运行的前处理进程＋编码时间；启动、文件读写、不同运行时段及部分同时进行的下载/编译会影响它。v2为标量门控，v3/v4为经一致性检查的SIMD版本。不能据此给不同标准排名或作为正式内存接口速度得分。

## 正确性、加速与重复计时

逐帧接口保持processYUVFrame(const uint8_t*, uint8_t*, int, int, int)，输入为紧密排列的8-bit YUV420P，支持src==dst。当前实现使用局部输入和工作缓冲，不使用视频文件名、未来帧或原始参考评分。未改变分辨率、FPS或帧数。

旧检查覆盖恒等、常数帧、像素上限、色度不改亮度、旧版一致性、文件保护与解析BD-Rate；初版SIMD通过192组、门控SIMD通过160组。最终平滑/色度阈值与guarded共通过144组标量/SIMD等价检查，含奇数色度尺寸、舍入、限幅和1080p。adaptive/context/content各20组不变量检查；guarded另验证高清分支原地/分离缓冲一致、Y原样及整体限幅。证据位于results/correctness、simd_check、v2_simd_check、final_simd_check、v3/v4/v5_correctness。

重复计时 `timing`：sharp:1、libx265、preset=medium、CRF=26，三轮交替；总墙钟中位数变化+8.63%。详见[summary.json](D:/shenni/交大/Hackthon/34-demo/results/timing/summary.json)。

重复计时 `v7_timing`：guarded:2、libx265、preset=medium、CRF=26，三轮交替；总墙钟中位数变化+10.99%。详见[summary.json](D:/shenni/交大/Hackthon/34-demo/results/v7_timing/summary.json)。
192帧前处理内核中位数0.208655秒，约1.087毫秒/帧；包含文件I/O的端到端约增加11%，仍需在官方内存接口中评估并优化。

### 抽帧目视检查

已对齐查看Beauty原始片段第64帧（原序列320）与AV1 hybrid/VVC perceptual解码帧，以及DucksTakeOff原始第64帧与HEVC guarded解码帧。主体位置、轮廓、分辨率和整体颜色正常，存在正常有损编码的纹理变化，未发现黑帧、错位或明显异常色块。文件位于results/visual_check_final/。这不是全视频主观评分，也不能仅据此宣称人眼质量提升。

## 数据来源与结论边界

历史Beauty为1080p120、600帧；Foreman/Mobile为CIF、300帧，仅作低分辨率迁移诊断。新增CrowdRun、DucksTakeOff来自Xiph托管的SVT测试集，按Y4M头保持1080p50，只取前128个连续完整帧，剥离容器，不缩放、不抽帧、不重编码。源URL、头、HTTP范围状态、帧数与SHA256保存于datasets对应JSON。

UVG Jockey/HoneyBee服务器连接超时，未取得可用文件，故未写成已评测数据；改用上述独立高清内容。SVT原始技术/使用限制文档链接保存在数据清单；Beauty、Xiph等来源信息见KNOWLEDGE.md及datasets/README.md。

参考已有CRF28单点：baseline VMAF69.163722，opt68.754333；按旧日志已舍入MSE重算PSNR约38.296932→38.360033dB。单点不能算BD-Rate，旧模型/配置记录不完整，不与新四点结果混用。

接受仅指当前内容、帧区间、编码配置、质量点和度量口径。0.3%门槛很窄，四点插值结果未建立统计置信区间；短片段、CIF、不同GOP上下文和官方未知配置都限制泛化。后续须覆盖独立视频全长、更多内容/质量点，并按官方PSNR平面、模型、码率与汇总算法复核。

恒等/低强度回退可以保护正确性，但不自动构成正向收益。不得按已知视频标签切换参数，不得因某个条件失败就删除其结果；未过保真约束的候选不推荐，即使VMAF收益较大。
