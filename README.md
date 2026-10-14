# 34 题赛前开发目录

GitHub 仓库仅包含代码、文档、指标与图表。大视频和工具留在本地，获取方式及完整本地清单说明见 [GITHUB_CONTENTS.md](GITHUB_CONTENTS.md)。


## 开始使用

在本目录 PowerShell 中运行：

```powershell
.\build.ps1
python benchmark.py --out results/my_screen
```

依赖：本机现有 MinGW g++、Python、NumPy、SciPy；生成曲线另需 Matplotlib。FFmpeg 默认使用本目录的 full_build。`build.ps1` 编译四线程候选程序并执行正确性检查。

固定参数验证：

```powershell
python benchmark.py --out results/my_holdout --start-frame 256 --frames 192 --preset medium --profiles identity:0 sharp:1
python benchmark.py --out results/my_full --frames 600 --preset medium --profiles identity:0 sharp:1
python benchmark.py --out results/my_x264 --start-frame 256 --frames 192 --preset medium --codec libx264 --profiles identity:0 sharp:1
```

独立视频：传入 `--input`、`--width`、`--height`、`--fps`、`--frames`。原始输入必须是完整的 8-bit YUV420P。默认 CRF 22、26、30、34，可用 `--crfs` 指定至少四个不同点。

可加 `--reuse-baseline results/full_x265` 复用同源、同编码和度量配置的 identity 点；脚本还核对原始片段 SHA256。新实验目录仍保存独立 manifest。复用适合码率—质量比较；速度结论应重新交替测量 baseline/opt，不能把不同时间运行的时长当成严格速度收益。`python timing_check.py` 对最终 weak sharp:1 做三轮交替计时。`points.csv` 中码率来自视频包大小总和，不含 MP4 封装。PSNR 使用 FFmpeg 累计 MSE 的 summary，VMAF 使用全帧算术平均，不设置指标抽帧。`summary.json` 同时给出 PCHIP 与三次多项式 BD-Rate 和共同积分区间。

## 前处理接口
```cpp
#include "preprocess.h"
// 初始化时配置一次，处理期间不要并发修改配置。
configurePreprocess("guarded", 2); // HEVC回归候选；先按REPORT.md核对适用条件
processYUVFrame(src, dst, width, height, crf);
```

集成时编译 `preprocess.cpp`，定义 `PREPROCESS_LIBRARY` 以排除命令行 main；Windows g++ 还需 `-std=c++17 -O3 -DNOMINMAX -fopenmp`。MSVC 可使用 C++17、优化和 `/openmp`。帧缓冲为紧密排列 Y、U、V，偶数宽高，无 stride；官方如果使用 stride 或其他格式，需要独立适配，不能直接把不同布局的地址传入。支持 src==dst 的原地调用，原地调用会额外分配备份，性能评测建议使用分离缓冲。部分重叠缓冲不支持。

未配置时默认恒等处理。`guarded:2`是HEVC回归候选，不是未知视频/标准已达标的默认提交；content的独立高清失败与后续风险门控见REPORT.md。官方若只提供逐帧入口，可在选定已验证配置后修改默认mode/amount。不要逐帧重复初始化，不要按视频名称选择参数。线程局部缓冲只复用内存，不保存历史帧状态。

命令行示例：

```powershell
.\preprocess.exe input.yuv processed.yuv 1920 1080 28 guarded 2 600
```

最后一个参数为帧数；省略则处理全输入。`amount` 取 0–16，`smooth/chroma` 为原平滑修正的十六分比例，`sharp` 为十字高通修正的十六分比例；新候选限制每像素 ±1，旧版 `legacy:16` 保持原方案。各模式并不是同等处理强度。

扩展 `hybrid` 对亮度使用指定细节增强强度，对色度使用 16/16 混合且仍限制 ±1。它用于检验亮度收益与色度保真的组合；较强参数不自动满足 PSNR 约束。GCC x86 构建会运行时检测 AVX2，对细节增强使用整数 SIMD；不支持时走标量路径，无需全程序设置 `-mavx2`。`verify_simd.py` 比较构建前保留的标量程序与 SIMD 程序；测试证据见 `results/simd_check/`。

## 2026-10-14新增评测与复现

当前统一源码为`preprocess.cpp`，`build.ps1`构建并检查接口。`preprocess_adaptive/context/content.cpp`和相应二进制保留用于历史复现；编译集成时只选择一个实现文件，避免重复符号。旧标量版本保存在`results/code_snapshots/`。

```powershell
.\build.ps1
python benchmark_v5.py --preprocessor preprocess.exe --preprocessor-source preprocess.cpp --out results/my_content --frames 600 --preset medium
python benchmark_v6.py --out results/my_guarded --frames 600 --preset medium
python benchmark_v5.py --preprocessor preprocess.exe --preprocessor-source preprocess.cpp --out results/my_av1 --codec libsvtav1 --preset 8 --points 24 30 36 42 --preprocess-crf 28 --start-frame 256 --frames 192 --profiles identity:0 hybrid:2
python benchmark_v5.py --preprocessor preprocess.exe --preprocessor-source preprocess.cpp --out results/my_vvc --codec libvvenc --preset faster --points 22 27 32 37 --preprocess-crf 28 --start-frame 256 --frames 192 --profiles identity:0 perceptual:2
```

VVC使用QP，不是CRF；评测统一回8-bit，转换协议与完整命令另存。AV1/VVC的前处理提示独立固定为28。不能把不同标准质量参数相等当成质量相等，也不能给opt单独改变编码配置。

`perceptual/balanced/adaptive/context/content/guarded`都属于感知启发式，规则与失败见报告。`guarded_validation.ps1`验证最终HEVC回归候选，`chroma_validation.ps1`补充仅色度处理，`timing_check_final.py`做guarded三轮交替计时。其他脚本保留历史版本；改变脚本/二进制后用新目录，不覆盖旧manifest或强行复用质量。

`equivalent_validation.py`先验证每个质量点全部处理字节相等、旧二进制与视频哈希一致，再复用原编码质量；`equivalence.json`保存证明。它不产生新编码测量，借用的编码耗时也不能用于同时段速度排名。

```powershell
g++ -O3 -std=c++17 -fopenmp -DPREPROCESS_SCALAR preprocess.cpp -o preprocess_scalar.exe
python verify_final_simd.py
python verify_adaptive.py --mode content --exe preprocess.exe --out results/my_correctness
python make_report.py
```

最终SIMD还加速了弱平滑与色度平滑：把“舍入后±1限幅”转为整型阈值比较，保持像素结果不变。旧`legacy`仍使用原始舍入路径。GCC运行时检测AVX2，不支持时用标量；MSVC无需GNU target扩展，使用标量路径及C++17/OpenMP。

详细知识见`KNOWLEDGE.md`，结论见`REPORT.md`。生成器扫描已完成的历史及v2–v7结果，排除后端通路检查；区分实编码、baseline复用与像素等价复用。guarded是在五段已知素材上设计的回归门控，不是独立泛化证明。高清前缀仅剥离Y4M标记，JSON记录帧数/FPS/SHA256，不缩放或抽帧。
