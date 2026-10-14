# 独立公开测试视频

来源：[Xiph Derf's Test Media Collection](https://media.xiph.org/video/derf/)。Foreman CIF 与 Mobile CIF 各 300 帧，Y4M 头声明 352×288、30000/1001fps、8-bit 4:2:0。

下载文件保持原样，同时用 FFmpeg `-c:v copy -f rawvideo` 去除 Y4M 帧标记和容器头，得到 `.yuv`，不进行缩放、重编码或帧率转换。来源、原始文件和 YUV 的 SHA256、实际帧数见 [manifest.json](manifest.json)。

Xiph 说明素材来自公开服务器或经授权托管，并提醒遵守原始限制；部分历史素材帧率可能是推断值。本次按 Y4M 头开展技术验证，不能据此推定所有商业和再分发用途都获得许可。素材保持在本地，不向外发布。

这两段低分辨率素材用于检查独立运动与纹理内容的迁移；它们不能替代赛题主要的独立 1080p 测试集，也不应与 Beauty 的指标简单平均后宣称正式收益。

## 新增高清前缀

CrowdRun和DucksTakeOff从Xiph托管的SVT测试集获取，Y4M头为1920×1080、50fps、默认8-bit 4:2:0。通过HTTP范围请求取前128个完整连续帧，只去除容器头/帧标记，不缩放、不抽帧。对应`*_prefix128.json`保存URL、原头、HTTP206、帧数与SHA256；不是全部500帧。

来源及使用限制：[SVT Multi Format Test Set说明](https://media.xiph.org/video/derf/vqeg.its.bldrdoc.gov/HDTV/SVT_MultiFormat/SVT_MultiFormat_v10.pdf)。如再分发，应遵守该说明并附原文。素材初用于固定content策略的独立验证；在观察失败并设计guarded后，最终属于回归素材，不能继续当作未参与设计的盲测集。

UVG的Jockey/HoneyBee尝试因连接超时未取得可用文件，未记为已评测。后续仍需新的独立高清全长、文字与低光样本。
