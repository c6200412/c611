## 第 0 层：数据 —— 最根本、也最脆弱的一层

模型的能力**完全由这份标注决定**：

代码块

```
每张截图对应一个 txt，每行一个框：
0 0.512006 0.178194 0.354790 0.067713     ← 类别 cx cy w h（全部归一化到 0~1）
1 0.316412 0.073308 0.073396 0.032288     ← chat_object
2 0.146280 0.072047 0.140291 0.040235     ← distraction
```

作者用自己的微信截图标注了 3 个类别，然后训练：

|项|值|
|---|---|
|数据量|未随包提供（`labels\`、`dataset\` 都没打包）|
|类别|0 chat_bubble / 1 chat_object / 2 distraction|
|主题|**只有浅色主题**|
|来源|作者自己的微信窗口截图|

⚠️ **第 0 层就是能力上限**。你深色截图检测不出来，不是算法问题，是这一层缺数据。

---

## 第 1 层：算法 —— YOLOv8

`YOLO` = You Only Look Once，**单阶段目标检测器**。核心思路：

代码块

```
整图一次前向 → 直接输出所有框的位置+类别+置信度 → NMS 去重
```

不像两阶段检测（R-CNN 系列）那样先找候选区域再分类。所以快。

具体到 v8-nano：

|组件|作用|
|---|---|
|CSPDarknet 骨干|提特征，逐层下采样|
|PAN-FPN 颈部|融合浅层（细节）和深层（语义）特征|
|解耦检测头|分别预测"有没有东西"和"是什么类别"|
|Anchor-free + DFL|不用预设先验框，直接回归边界距离|
|损失|CIoU（框）+ BCE（类别）+ DFL（分布）|

实际训练配置（从 `args.yaml` 读到的）：

代码块

```
model    yolov8n.pt      ← COCO 预训练底座
epochs   100
batch    16
imgsz    640
optimizer auto, lr0 0.01
```

最终成绩：**P 0.979 / R 0.948 / mAP50 0.973 / mAP50-95 0.902**

> 这个成绩很高，但注意：这是**在同分布的验证集**上测的（浅色、同分辨率、同布局）。换深色主题就归零 —— 说明它学的是"这种浅色界面里的气泡"，不是"气泡"这个抽象概念。

---

## 第 2 层：框架 —— PyTorch + Ultralytics

|东西|它提供什么|
|---|---|
|**PyTorch 2.15**|张量计算、自动求导、模型序列化（`.pt` 就是它的格式）|
|**ultralytics 8.4.41**|把 YOLO 的训练/推理/验证/导出/画图全封装成 `YOLO("best.pt").predict(...)` 一行|

**关键机制：迁移学习**。`yolov8n.pt` 在 COCO 的 80 类物体上预训练过，已经有了"边缘、纹理、形状"的通用识别能力。作者只在它上面微调 3 个新类别，所以几十上百张图就能训到 mAP 0.97。

如果从零训，同样的数据量根本学不出来。

---

## 第 3 层：图像处理 —— OpenCV + 手写规则

这一层是**最容易被忽略但占比很大**的部分。OpenCV 提供算子，项目写了 4 条**规则**（不是学习出来的）：

|规则|实现|参数|
|---|---|---|
|判左右|HSV 绿像素占比|`min_green_ratio=0.08`，HSV 区间手工定的|
|去边框干扰|框内缩 12% 再采样|`shrink_ratio=0.12`|
|找聊天区边界|Sobel Y 算子 + 取能量最强行|上 1/3 / 下 1/3 分区搜索|
|半截气泡过滤|溢出高度 / 框高|`edge_overlap_threshold=0.30`|

用到的 OpenCV 算子：`imread/imdecode`、`cvtColor`、`inRange`、`bitwise_or`、`countNonZero`、`Sobel`、`GaussianBlur`、`rectangle`、`putText`、`imwrite`。

> 这 4 条规则是**脆弱点**：换气泡配色、换 DPI、换微信皮肤都会让阈值失准。它们不是"学"出来的，没法自适应。

---

## 第 4 层：OCR —— RapidOCR / PaddleOCR / ONNX

`RapidOCR` 本质是**把 PaddleOCR 的模型转成 ONNX，用 onnxruntime 跑**，从而摆脱 PaddlePaddle 框架依赖。三个子模型串起来：

代码块

```
① 方向分类器   → 判断文字有没有倒转
② DBNet 检测   → 输出"哪里是文字"的概率图 → 二值化 → 找连通域 → 文本行框
③ CRNN/SVTR 识别 → 每个文本行裁出来 → 转成字符串
```

所以 `text_process.py` 一次 `ocr(crop)` 调用，背后是三个神经网络依次跑。

而检测框内的文字是**多行**时，DBNet 会把每行当独立文本框，识别完用 `\n` 连接 —— 这就是你看到 `"我在8号楼门口，\n但是我忘了他还要交10块钱呢"` 的原因。

---

## 第 5 层：工程 —— Python 标准库 + uv

|依赖|用途|
|---|---|
|`argparse`|所有命令行参数|
|`json` / `pathlib`|读写结果|
|`http.server`|**网页标注器（`tools/fount/server.py`）只用标准库写的**，没装 Flask|
|`ctypes` + Win32 API|截图脚本枚举进程、找窗口、抓客户区|
|`uv`|装 Python、建 venv、装依赖、跑脚本|

---

# 依赖关系总图

代码块

```
                    ┌─ 训练数据（浅色微信截图 + 3类标注）★ 决定能力上限
                    │
YOLOv8-nano ◄───────┴─ 迁移学习（COCO 预训练 yolov8n.pt）
   │
   ├─ PyTorch（张量/自动求导/.pt 格式）
   ├─ Ultralytics（封装训练与推理）
   │
   ▼
OpenCV（读图/画框/HSV/Sobel）+ 4 条手写规则 ★ 最脆弱
   │
   ▼
RapidOCR = PaddleOCR 转 ONNX：DBNet 检测 + CRNN 识别 + 方向分类
   │
   ▼
onnxruntime（CPU 推理）
   │
   ▼
Python 3.13 + uv
```

---

# 一句话总结它的"基础"

**90% 是现成轮子**（YOLO + OpenCV + RapidOCR），**10% 是胶水规则**（HSV 判左右、Sobel 找边界、阈值过滤）。

作者没有自研任何算法 —— 这个项目的价值在于**把三套现成工具用 4 条经验规则缝成了一条能用的流水线**，并且训出了一个可用的微信气泡模型。

所以它的行为完全可预测：

|输入|结果|
|---|---|
|和训练数据同分布（浅色微信）|极好（mAP 0.90）|
|分布外（深色、别的软件、别的 DPI）|崩塌|

这也解释了为什么它能"读微信"却读不了账单页 —— **不是它聪明，是它只见过那一种画面**。



## 0. 一句话

把**微信聊天窗口截图**变成结构化的「谁说了什么」JSON：YOLO 找气泡框 → 按颜色判左右 → RapidOCR 认字。

不需要登录、不解密数据库，纯视觉方案。

---

## 1. 它能干什么 / 不能干什么

### 能干

|能力|说明|
|---|---|
|检测聊天气泡|输出像素坐标 + 置信度|
|判断自己/对方|靠气泡颜色（绿=自己），不靠头像|
|识别聊天对象名字|从窗口标题栏/聊天头部的名字框 OCR|
|提取气泡内文字|RapidOCR，中英文都可以|
|按阅读顺序排序|按 y 坐标从上到下|
|批量处理|指一个目录，逐张跑|
|连续截图|自带脚本，按间隔抓微信窗口|
|自己训练模型|标注 → 划分 → 训练 全链路都有|

### 不能干

|限制|原因|
|---|---|
|深色主题|训练集只有浅色图，实测 8 条气泡只认出 0~3 个|
|表情包 / 图片 / 语音条|只标了"气泡"这一类，非文字内容不检测|
|群聊里区分具体谁说的|只有 `self` / `chat_object` 两个值|
|提取时间戳|`星期三 10:23` 这种没被检测|
|别的软件（企业微信/QQ/Telegram）|布局与气泡样式不同，需重训|
|读取已删除的消息|纯视觉，只能看到屏幕上有的|
|写文件/导表格|只出 JSON，转换要自己写|

---

## 2. 当前环境状态（已装好，别再动）

|项|值|
|---|---|
|Python|3.13（uv 托管，`%APPDATA%\uv\python\cpython-3.13-windows-x86_64-none`）|
|虚拟环境|`<项目>\.venv`，约 **0.98 GB**|
|torch|**2.15.0+cpu**（`torch.version.cuda` 为 `None`）|
|ultralytics|8.4.41|
|opencv-python|4.13.0.92|
|numpy|2.4.4|
|RapidOCR|rapidocr_onnxruntime 1.4.4 + onnxruntime 1.32.0|
|CPU 线程|14|

### 装环境时发生的关键决策

原始 `pyproject.toml` 里锁了 CUDA 源：

toml

```
[[tool.uv.index]]
name = "pytorch-cu126"
url = "https://download.pytorch.org/whl/cu126"
explicit = true

[tool.uv.sources]
torch = { index = "pytorch-cu126" }
torchvision = { index = "pytorch-cu126" }
```

本机**完全没有 NVIDIA 硬件**（`nvidia-smi.exe`、`NVIDIA Corporation` 目录、`nvlddmkm.sys` 三者都不存在），所以：

- 这套 CUDA 会白下 2.5 GB+
- Windows 的 CUDA 版 torch 把 CUDA DLL 打进 wheel，`+cu126` 版本 `.venv` 达 **4.38 GB**，但 `torch.cuda.is_available()` 仍是 `False`

**已删除该 7 行配置**，改用 PyPI 的 CPU 版，`.venv` 降到 0.98 GB，省 3.4 GB。

> 如果以后要拷到有 N 卡的机器：把上面那段加回文件末尾即可。

### 日常命令

powershell

```
cd "C:\Users\王任卓\Desktop\26114\WeChatChatReader-main\WeChatChatReader-main"
uv run python predict_bubbles.py --device cpu
uv run python text_process.py --ocr-device cpu
```

**不需要**：`uv sync`（已装好）、手动 activate、重装。

---

## 3. 目录结构与数据流

代码块

```
before_img\      截图脚本的输出（监测模式输入）
img\             标注图片（split_dataset 的输入）
labels\          YOLO 标签 txt
dataset\         划分后的训练/验证集
test\            ★ 默认推理输入（手动截图丢这里）
shots\           可选的自定义输入目录
predict_out\     ★ 检测结果（每张图 .json + _vis.jpg + summary.json）
text_json\       ★ 最终结果（每张图 .json + summary.json）
text_img\<图名>\ 每个气泡的裁图 msg_0001.png...
runs\detect\...\weights\best.pt   ★ 模型权重
tools\           各种工具脚本
```

### 数据流

代码块

```
微信截图
   │  tools/wechat_window_loop_ocr.py（可选，自动连续截图）
   ▼
before_img\      或直接 manual → test\
   │  predict_bubbles.py（YOLO 检测 + 颜色判左右）
   ▼
predict_out\<图名>.json      ← 检测坐标
predict_out\<图名>_vis.jpg   ← 画框预览（人眼检查）
   │  text_process.py（裁气泡 + OCR + 配 speaker）
   ▼
text_json\<图名>.json        ← 每张图的消息
text_json\summary.json       ← 所有图的汇总
text_img\<图名>\msg_00NN.png ← 气泡裁图
```

### 训练支线（与日常使用完全独立）

代码块

```
before_img\ → label_review.py / fount/server.py → img\ + labels\
   → split_dataset.py → dataset\
   → train_bubbles.py → runs\detect\<run>\weights\best.pt
```

---

## 4. 三个入口脚本详解

### 4.1 `predict_bubbles.py` —— 检测

powershell

```
uv run python predict_bubbles.py --source test --device cpu
```

|参数|默认|说明|
|---|---|---|
|`--weights`|`runs/detect/wechat_bubbles-3/weights/best.pt`|模型路径|
|`--source`|`test\`|图片目录或单张图；**只读第一层，不递归**|
|`--conf`|0.25|置信度阈值；漏检多→降，误检多→升|
|`--output`|`predict_out\`|输出目录|
|`--bubble-class`|0|气泡类别的 id，须与 data.yaml 一致|
|`--min-green-ratio`|0.08|判 self 的绿色像素占比阈值|
|`--shrink-ratio`|0.12|判颜色时框内缩比例（避开圆角/阴影）|
|`--device`|`0`|**本机必须写 `cpu`**|
|`--edge-overlap-threshold`|0.30|半截气泡过滤阈值|
|`--name-pad-x/y`|12 / 6|写入 JSON 时框向外扩张的像素|

行为要点：

- **完全不打印成功信息**，跑完没输出是正常的
- 支持的图片格式：`.jpg .jpeg .png .webp .bmp`
- 读图用 `cv2.imread`，**没有中文路径兜底** → 中文路径读取失败会静默跳过整张图（见 §8 已知问题）
- 每张图输出 `<图名>.json` + `<图名>_vis.jpg`，最后追加 `summary.json`

### 4.2 `text_process.py` —— OCR 与归属

powershell

```
uv run python text_process.py --ocr-device cpu
```

|参数|默认|说明|
|---|---|---|
|`--predict-out`|`predict_out\`|读哪个检测结果目录|
|`--text-json`|`text_json\`|输出 JSON 目录|
|`--text-img`|`text_img\`|输出裁图目录|
|`--no-save-crop`|关|不要裁图时加（省磁盘）|
|`--ocr-device`|`gpu`|**本机必须写 `cpu`**|
|`--sleep-ms`|0|每张图之间休眠，批量太大时用|

行为要点：

- 扫 `--predict-out` 下**所有** `.json`（跳过 `summary.json`）
- 读图有兜底：`cv2.imread` 失败 → `np.fromfile` + `imdecode`
- **源图不存在时会退化去读 `_vis.jpg`（画了框的图）**，导致 OCR 结果被框线污染（见 §8）
- 依赖 `rapidocr_onnxruntime`，缺包直接 `SystemExit`
- 同样不打印成功信息

### 4.3 `tools\wechat_window_loop_ocr.py` —— 连续截图

powershell

```
uv run python tools/wechat_window_loop_ocr.py --interval-ms 5000
```

|参数|默认|说明|
|---|---|---|
|`--interval-ms`|1000|截图间隔；1 秒/张约 3.6 GB/小时，建议 3000~5000|
|`--exe`|`WeChat.exe` `Weixin.exe`|可重复指定|

要点：

- **名字里有 ocr，但完全不做 OCR**，只截图
- 通过进程名找 PID → 枚举窗口 → 抓客户区
- 微信窗口必须**可见、不最小化、不被遮挡**；全黑时用 `PrintWindow` 兜底
- 截图存 `before_img\wechat_cap_<时间戳>.png`
- `Ctrl+C` 停止（最小化终端不影响，关掉终端等于杀进程）

---

## 5. 输出格式

### 5.1 `predict_out\<图名>.json`

json

```
{
  "image": "C:\\...\\test\\bc0f9547....png",
  "detections": [
    {
      "xyxy": [824.0, 289.0, 1079.0, 356.0],
      "class_id": 0,
      "class_name": "chat_bubble",
      "conf": 0.916,
      "role": "self",
      "green_ratio": 0.917
    }
  ]
}
```

|字段|含义|
|---|---|
|`image`|源图**绝对路径**（换机器/删图会失效）|
|`xyxy`|左上右下像素坐标|
|`class_id` / `class_name`|0=chat_bubble、1=chat_object、2=distraction|
|`conf`|检测置信度|
|`role`|气泡才有：`self` / `peer`；其他类为 `null`|
|`green_ratio`|气泡才有：框内绿色像素占比|

### 5.2 `text_json\<图名>.json`

json

```
{
  "source_image": "...",
  "source_detection_json": "...",
  "chat_object": "Accept",
  "messages": [
    {"index": 1, "bbox": [404,119,632,188], "speaker": "Accept", "text": "这会就要上课吗"},
    {"index": 2, "bbox": [987,204,1081,272], "speaker": "self",   "text": "en"}
  ]
}
```

|字段|含义|
|---|---|
|`chat_object`|对方名字（OCR 自标题栏）；抓不到时为 `"对方"`|
|`messages[].index`|序号，按 y 坐标排序|
|`messages[].bbox`|裁图所用的框（已 clamp 到图像内）|
|`messages[].speaker`|`self` 或 `chat_object` 的值|
|`messages[].text`|OCR 结果，**保留气泡内换行 `\n`**|

### 5.3 `text_json\summary.json`

所有图像结果的数组（`text_process.py` 每次运行整体重写）。

---

## 6. 检测原理（用一张真实截图讲）

测试图：`test\bc0f9547749466f01d9c81a86d6713d9.png`，1169×1019，浅色主题。

### 6.1 YOLO 怎么找框

1. 整张窗口截图（含左侧会话列表、右侧聊天区、底部输入框）直接输入
2. 缩放到 640×640，切成 20×20 的网格
3. 每个格子预测：有无物体中心 + 框尺寸偏移 + 类别 + 置信度
4. **NMS** 去重，坐标映射回原图尺寸

实测输出 8 个框：

代码块

```
类名            置信度   role    绿占比   x1,y1,x2,y2
distraction     0.926   -       0.000   89,53,253,94      ← 左上搜索框
chat_object     0.904   -       0.000   327,58,413,91     ← 标题栏 "Accept"
chat_bubble     0.920   peer    0.000   406,702,607,767   ← "重回巅峰好吧"
chat_bubble     0.916   self    0.917   824,289,1079,356  ← "已经给你们办好了"
chat_bubble     0.909   self    0.956   987,204,1081,272  ← "en"
chat_bubble     0.907   peer    0.000   403,375,503,443   ← "OK"
chat_bubble     0.902   peer    0.000   404,119,632,188   ← "这会就要上课吗"
chat_bubble     0.824   self    0.942   987,786,1080,844  ← "nb"
```

### 6.2 左右（self/peer）不是模型判的

由 `bubble_role.py` 用颜色算：

python

```
① 框内缩 12%（shrink_ratio）→ 去掉边缘圆角与阴影
② 转 HSV，落在绿色区间的像素
   H ∈ [35,92] 或 [55,85]  (两组区间取并)
③ 绿色占比 ≥ min_green_ratio(0.08) → "self"，否则 "peer"
```

实测分离度极高：self 三个框 0.917/0.956/0.942，peer 三个框全部 0.000。

交叉验证：按框中心点左右分区（中线 584），3 个左全 peer、3 个右全 self，与颜色判定 6/6 一致。

> ⚠️ 可视化图上的标签 `chat_bubble peer 0.00` 里那个 `0.00` **是绿占比不是置信度**（`predict_bubbles.py` L167）。非气泡框才显示置信度。

### 6.3 半截气泡过滤

用 Sobel Y 算子找横向边缘最强的行，作为聊天区上/下边界（上边界只在上 1/3 搜索，下边界只在下 1/3），然后：

代码块

```
超出比例 = (上溢出高度 + 下溢出高度) / 框高
> edge-overlap-threshold(0.30) → 丢弃
```

### 6.4 OCR 与归属

1. 只取 `chat_bubble` 的框，按 `(y1, x1)` 排序
2. 每个框裁图 → RapidOCR（conf ≥ 0.1 的行保留，多行用 `\n` 连接）
3. `chat_object` = 取置信度最高的 `chat_object` 框做 OCR；没有则 `"对方"`
4. `speaker`：`role == self` → `"self"`；否则 → `chat_object`；`role` 缺失时现场用颜色重算一次

---

## 7. 已实测的结果

### 样例图（浅色）

代码块

```
[Accept] 这会就要上课吗
[self]   en
[self]   已经给你们办好了
[Accept] OK
[Accept] 重回巅峰好吧
[self]   nb
```

### 自己的浅色截图

代码块

```
[对方]   你在哪
[self]   我在8号楼门口，但是我忘了他还要交10块钱呢
[self]   你有吗
[对方]   无
[对方]   我先去了
[self]   OK
[self]  答案，12月16日
```

7 个气泡全中，那个 😂 表情没被检测（正确，它不是文字气泡）。因为截图是从聊天区裁的、没有标题栏，`chat_object` 退化成 `"对方"`。

### 深色主题（失败）

同样的对话内容，深色主题下检测 **0 个**。尝试 4 种图像变换后：

|变换|气泡数（实际 8 个）|
|---|---|
|只反转亮度 V|1|
|灰度反转|3（且角色全判 peer）|
|全通道反相|2|
|灰度反转 + CLAHE|2|

**结论：预处理救不了，只能补数据重训。**

### 支付账单页（正常返回空）

`test\22.png` 是"微信支付"服务号页面（深色、付款卡片），检测 0 个 —— 正确的，那里没有气泡。想读这类图应直接整图 OCR。

---

## 8. 已知问题清单（★ = 建议修）

### ★ 8.1 `predict_bubbles.py` 无中文路径兜底

python

```
im_bgr = cv2.imread(str(img_path))
if im_bgr is None:
    continue          # 静默跳过，没有任何提示
```

`cv2.imread` 在 Windows 上用 ANSI 编码打开文件，中文路径（`C:\Users\王任卓\...`）会变成乱码 `鐜嬩换鍗揬` 从而打不开。

**症状**：跑完 `predict_out\` 是空的，终端只有一行 `can't open/read file`。

**修法**（与 `text_process.py` 一致）：

python

```
def imread_any(path: Path):
    img = cv2.imread(str(path))
    if img is not None:
        return img
    try:
        data = np.fromfile(str(path), np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
    except OSError:
        return None
```

### ★ 8.2 `text_process.py` 源图缺失时去读 `_vis.jpg`

`pick_source_image()` 在 `record["image"]` 不存在时回退到 `predict_out\<stem>_vis.jpg`。而 `_vis.jpg` 是**画了彩色框和文字**的预览图，拿去 OCR 会被污染。

**症状**：删了 `test\` 的图但没删 `predict_out\` 的 json，重跑后结果异常。

**修法**：源图不存在时直接返回 `None` 跳过；或把 fallback 换成 `before_img\<stem>.png` 之类的原图候选。

### ★ 8.3 `SyntaxWarning: invalid escape sequence '\j'`

`predict_bubbles.py` 第 6 行文档字符串里写了 `D:\java_object\...`。

**修法**：文档字符串前加 `r`。

### 8.4 中文路径的全套影响

|环节|影响|
|---|---|
|`predict_bubbles.py`|静默跳过（危险）|
|`text_process.py`|有兜底，仅刷警告（无害）|
|图片文件名含中文|同上|

**根治办法**：把整个项目挪到纯英文路径，例如 `D:\wechat\`。挪完在那边跑一次 `uv sync`（缓存都在，很快）。

### 8.5 其他

- `predict_out\`、`text_json\`、`text_img\` 里的旧结果不会自动清理，会累积
- `text_img\<图名>\` 里可能残留作者打包时留下的旧裁图（例如样例图目录有 7 张而消息只有 6 条）
- `text_process.py` 每次重扫 `predict_out\` 全部 json，图多了会越来越慢
- 两个脚本都**不输出成功日志**，"没输出"≠"出错"

---

## 9. 排错手册

|现象|原因|处理|
|---|---|---|
|跑完 `predict_out\` 空|中文路径导致 `cv2.imread` 失败|见 8.1 / 把项目挪到英文路径|
|`detections: []` 但图里有气泡|深色主题 / 非聊天气布|切浅色主题重截，或重训|
|`speaker` 全是"对方"|截图没带标题栏|截图包含窗口顶部名字栏|
|大量 `can't open/read file` 警告|中文路径|无害；想彻底消除见 8.4|
|`RapidOCR 初始化失败`|缺 onnxruntime|`uv pip install onnxruntime`|
|默认参数报 CUDA 错误|默认 `--device 0`|加 `--device cpu` / `--ocr-device cpu`|
|结果和上一轮一样|图没变 / 同名覆盖|检查是不是 `test\` 里同一张图|
|结果被框线污染|源图已删，读了 `_vis.jpg`|清空 `predict_out\` 重跑|
|卡住 >2 分钟|加载模型或首次 OCR 下载|等待；必要时 `Ctrl+C` 重试|
|`SyntaxWarning: '\j'`|文档字符串|无害，可忽略|

---

## 10. 模型与训练

### 10.1 `best.pt` 是什么

|项|值|
|---|---|
|大小|5.95 MB（fp16 存储）|
|参数量|3,011,433|
|架构|YOLOv8-nano|
|输入|640×640|
|类别|0 chat_bubble / 1 chat_object / 2 distraction|
|验证集|P 0.979 / R 0.948 / mAP50 0.973 / mAP50-95 0.902|

`.pt` = PyTorch 序列化文件（zip + pickle 的 dict），包含 `model`、`ema`、`optimizer`、`train_metrics`。`YOLO("best.pt")` 可直接还原结构与权重。

⚠️ 不要加载来路不明的 `.pt` —— `torch.load` 会执行 pickle，等价于执行代码。

### 10.2 标注

**方式 A：网页标注**

powershell

```
uv run python tools/fount/server.py     # 或设 ANNOTATE_PORT
# 浏览器打开 http://127.0.0.1:8810/
```

读 `before_img\`，写 `img\` + `labels\`；快捷键 `1/2/3` 切类别、`←/→` 换图、`Del` 删框。 （`index.html` 从 jsDelivr 拉 JSZip，**离线环境打包下载按钮会失效**）

**方式 B：半自动标注**

powershell

```
uv run python tools/label_review.py --images before_img --device cpu
```

|参数|默认|
|---|---|
|`--weights`|`runs/detect/wechat_bubbles-3/weights/best.pt`|
|`--images`|`before_img\`|
|`--labels-out`|`labels\`|
|`--img-mirror`|`img\`（默认同步原图，供 split 用）|
|`--imgsz` / `--conf` / `--device` / `--max-side`|640 / 0.25 / 0 / 1280|

操作：`q`/`Esc` 退出并保存、`s` 保存、`n` 下一张、`p` 上一张、`r` 重新推理、`Delete`/`Backspace` 删选中框、`[`/`]` 切类别、`0-9` 设新框类别、左键拖拽画框、左键点击选中、右键删除。

### 10.3 划分与训练

powershell

```
uv run python tools/split_dataset.py --train-ratio 0.8 --seed 42
# 只复制 img\ 与 labels\ 中 stem 同名且都存在 的样本 → dataset\images|labels\train|val

uv run python train_bubbles.py --model runs/detect/wechat_bubbles-3/weights/best.pt --device cpu --epochs 50 --batch 8
```

`train_bubbles.py` 主要参数：`--data`(data.yaml)、`--model`(yolov8n.pt)、`--epochs`(100)、`--imgsz`(640)、`--batch`(16)、`--device`(0)、`--workers`(0)、`--half`、`--cache`(false/ram/disk)、`--no-plots`、`--save-val-vis`、`--project`、`--name`。

### 10.4 支持深色主题的路线

1. 深色截图 30~60 张放 `before_img\`
2. `label_review.py --images before_img --device cpu` 手工补框（模型在深色上图基本全漏，得手动画）
3. **浅色与深色混在一起训**，避免遗忘浅色能力
4. `--model .../best.pt` 继续训，别从零开始
5. 60 张图 × 50 epoch，CPU 上约 10~20 分钟

---

## 11. 中文路径问题的根治

推荐：整个项目挪到 `D:\wechat\`。

powershell

```
# 1. 关闭所有终端（.venv 不能被占用）
# 2. 资源管理器里剪切 C:\Users\王任卓\Desktop\26114\WeChatChatReader-main
#    到 D:\ 并改名为 wechat
# 3. 验证
cd D:\wechat
uv run python -c "import torch; print(torch.__version__)"
# 若报环境错误（venv 记了旧路径）：
uv sync
```

---

## 12. 待办 / 可选增强

|事项|价值|工作量|
|---|---|---|
|补 `predict_bubbles.py` 中文路径兜底|消除"跑完是空的"幽灵问题|5 行|
|`text_process.py` 源图缺失时跳过|防止 OCR 读到画框图|2 行|
|文档字符串加 `r` 前缀|消除 SyntaxWarning|1 行|
|`tools\export_text.py`：JSON → txt/md，合并气泡内换行、多图去重|得到可读聊天记录|60 行|
|`tools\stats.py`：条数/发言人占比/长度分布|统计|40 行|
|`tools\watch.py`：截图+检测+OCR 实时循环|边聊边出文字|80 行|
|整图 OCR 工具（账单/表单）|覆盖非聊天截图|40 行|
|导出 ONNX|CPU 推理快 2~3 倍|一条命令|

---

## 13. 隐私与安全

- 本工具纯本地运行，不上传任何图片
- 包内自带两张**作者本人**的截图（`test\bc0f9547....png`、`before_img\wechat_cap_20260509_*.png`、`img\wechat_cap_20260509_*.png`，创建时间同为打包时间），与使用者无关
- 截图里可能含真实聊天内容，`text_json\`、`text_img\`、`predict_out\` 都是明文，注意归档与分享
- 不要加载来源不明的 `.pt`

---

## 14. 三分钟速查

powershell

```
cd "C:\Users\王任卓\Desktop\26114\WeChatChatReader-main\WeChatChatReader-main"

# 日常：把截图丢进 test\ 后
uv run python predict_bubbles.py --device cpu
uv run python text_process.py --ocr-device cpu
# 结果：text_json\summary.json

# 清空中间产物重来
Remove-Item predict_out\* -Force; Remove-Item text_json\* -Force; Remove-Item text_img\* -Recurse -Force

# 连续截图
uv run python tools/wechat_window_loop_ocr.py --interval-ms 5000
uv run python predict_bubbles.py --source before_img --device cpu
uv run python text_process.py --ocr-device cpu

# 换模型
uv run python predict_bubbles.py --weights runs\detect\<run>\weights\best.pt --device cpu
```


**就这两条命令**（在 `WeChatChatReader-main\WeChatChatReader-main` 目录里跑）：

powershell

```
uv run python predict_bubbles.py --device cpu
uv run python text_process.py --ocr-device cpu
```

|命令|干什么|
|---|---|
|第一条|找气泡框 → `predict_out\`|
|第二条|认字 → **`text_json\summary.json`（结果）**|

两条都要跑，顺序不能反。

## 完整流程（复制粘贴版）

powershell

```
cd "C:\Users\王任卓\Desktop\26114\WeChatChatReader-main\WeChatChatReader-main"; uv run python predict_bubbles.py --device cpu; uv run python text_process.py --ocr-device cpu; (Get-Content text_json\summary.json -Raw -Encoding UTF8 | ConvertFrom-Json) | ForEach-Object { "--- " + (Split-Path $_.source_image -Leaf); $_.messages | ForEach-Object { "  [" + $_.speaker + "] " + ($_.text -replace "`n"," ") } }
```

这一整段会**跑完两条命令并直接把结果打印在终端里**，不用再去翻文件。

## 记不住的话

在项目文件夹里建个 `run.bat`，以后双击它：

bat

```
@echo off
cd /d "%~dp0"
uv run python predict_bubbles.py --device cpu
uv run python text_process.py --ocr-device cpu
echo.
echo === 结果 ===
type text_json\summary.json
pause
```