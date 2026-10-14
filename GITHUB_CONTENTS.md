# GitHub 上传范围与复现说明

本仓库保存代码、文档、实验指标（JSON/CSV/日志）、图表、测试脚本和历史源码。按项目所有者选择，原始视频、生成的视频/YUV、下载工具与编译二进制保留本地，不上传 GitHub。

`LOCAL_FILE_INVENTORY.csv` 是上传准备时的本地文件快照，记录相对路径和字节数；列出的文件不一定存在于 GitHub。原目录约 72.8 GB。该清单不包含 Git 元数据，也不代表所有文件均可再分发。

## 素材与工具获取

- Beauty：在 [UVG 测试集](https://ultravideo.fi/dataset.html) 获取 Beauty 的 1920×1080、120fps、8-bit YUV420 序列；核对 `Beauty_Copyright.txt`，遵守 Digiturk 的 CC BY-NC 3.0 限制。实验使用完整 600 帧。
- Foreman / Mobile：从 [Xiph 测试集](https://media.xiph.org/video/derf/y4m/) 获取 `foreman_cif.y4m` 和 `mobile_cif.y4m`；具体来源、SHA256、帧数见 `datasets/manifest.json`。用 FFmpeg 去除 Y4M 容器头与帧标记，保持原始 YUV420P，不缩放或重编码。
- CrowdRun / DucksTakeOff：`fetch_hd_prefix.py` 获取前 128 个完整帧；来源、格式、SHA256 见 `datasets/*_prefix128.json`。使用和再分发限制见 [SVT 原始说明](https://media.xiph.org/video/derf/vqeg.its.bldrdoc.gov/HDTV/SVT_MultiFormat/SVT_MultiFormat_v10.pdf)。
- FFmpeg：[官方网站](https://ffmpeg.org/download.html)；历史评测使用 `ffmpeg-2026-10-12-git-615b07170e-full_build`。需要包含 libx264、libx265、libsvtav1、libvvenc、libvmaf 的构建。更换版本须重新评测，不能假定指标逐位一致。
- 编译和运行依赖、评测命令见 `README.md`。二进制由源码重新编译；历史 manifest 的二进制哈希对应本地原构建，重编译后的文件可能不同，原缓存不可直接冒充新测量。全字节等价性验证如果依赖旧二进制，需要原本地文件。

## 已保存与待生成的实验文件

`results/` 中保留指标、参数、来源与图表。原始/处理后 YUV、编码 MP4 以及 exe 不在仓库，运行相应脚本可重新生成。部分 manifest 和命令含实验机器的绝对路径，运行时应调整到本机路径。`REPORT.md` 说明复用指标、失败实验、PSNR 硬约束以及泛化限制；上传不代表官方达标。

未为本项目代码新增开源许可证；公开访问不等于自动取得第三方素材或代码的再分发许可。
