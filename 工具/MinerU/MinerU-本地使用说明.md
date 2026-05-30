# MinerU 本地使用说明

## 1. 当前安装位置

```text
Python: D:\Python\Python312
MinerU 根目录: D:\Python\MinerU
MinerU 主程序: D:\Python\MinerU\venv\Scripts\mineru.exe
启动脚本目录: D:\桌面\云端法考知识问答项目\工具\MinerU
```

## 2. 最常用运行方式

### 方式 A：直接运行脚本

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\桌面\云端法考知识问答项目\工具\MinerU\运行扫描件转Markdown.ps1" "D:\桌面\法考word资料\26商经郄鹏恩真金题.pdf" "D:\桌面\法考word资料\MinerU输出-商经知" "ch"
```

### 方式 B：直接调用 MinerU 主程序

```powershell
$env:HF_HOME="D:\Python\MinerU\models\hf-cache"
$env:MODELSCOPE_CACHE="D:\Python\MinerU\models\ms-cache"
$env:MINERU_TOOLS_CONFIG_JSON="D:\Python\MinerU\mineru.json"
$env:MINERU_MODEL_SOURCE="local"
& "D:\Python\MinerU\venv\Scripts\mineru.exe" -p "D:\桌面\法考word资料\26商经郄鹏恩真金题.pdf" -o "D:\桌面\法考word资料\MinerU输出-商经知" -b pipeline -m ocr -l ch
```

## 3. 参数含义

```text
-p  输入文件或文件夹
-o  输出目录
-b  后端。当前用 pipeline
-m  模式。扫描件一般用 ocr
-l  语言。中文用 ch
```

常用语言参数：

```text
ch      中文
en      英文
japan   日文
korean  韩文
auto    自动识别
```

## 4. 怎么判断它有没有真的在跑

如果窗口里只显示开头几行：

```text
[MinerU] input: ...
[MinerU] output: ...
[MinerU] lang: ch
[MinerU] mode: pipeline + ocr
```

这只能说明脚本已经启动，不代表整本一定已经顺利跑完。

更可靠的判断方法：

```powershell
Get-Process mineru,python -ErrorAction SilentlyContinue
```

如果能看到 `mineru.exe` 和相关 `python.exe`，说明程序还在运行。

## 5. 如果卡住，怎么结束

```powershell
Get-Process mineru,python -ErrorAction SilentlyContinue | Stop-Process -Force
```

## 6. 你截图里这些“加载/预测/进度”是什么意思

下面是窗口里常见进度项的含义。

### `Pipeline processing window batch 1/4`

意思是：

- 整个 PDF 被拆成了几个大批次处理
- 比如 `1/4` 就是第 1 批，共 4 批
- 你的 PDF 是 231 页，所以 MinerU 会按窗口分批跑，不是一次性全塞进去

### `GPU Memory: 8 GB, Batch Ratio: 4`

意思是：

- 程序检测到了可用于当前分析的 GPU 显存规模
- `Batch Ratio` 是它内部根据显存决定的一种批处理比例
- 这是程序自己根据显存做的调节，不是报错

### `DocAnalysis init, this may take some times......`

意思是：

- 文档分析模型开始初始化
- 这一步通常会加载模型到内存/GPU
- 第一次跑时会更慢

### `DocAnalysis init done!`

意思是：

- 文档分析主模型已经初始化完成
- 后面开始真正进入页面解析

### `Layout Predict`

意思是：

- 做版面分析
- 识别这一页里哪里是正文、标题、图片、表格、公式、印章等区域
- 可以理解为“先看页面结构”

### `MFR Predict`

意思是：

- 做公式识别
- MFR 通常就是公式相关识别
- 如果文档里公式不多，这一段通常很快

### `Table-ocr det`

意思是：

- 表格里的文字检测
- 先找到表格内部哪里有文字块

### `Table-ocr rec ch`

意思是：

- 表格里的文字识别
- `ch` 表示按中文 OCR 模型来识别

### `Table-wireless Predict`

意思是：

- 识别无线表格结构
- 也就是没有明显完整边框线的表格

### `Table-wired Predict`

意思是：

- 识别有线表格结构
- 也就是边框比较明确的表格

### `OCR-det ch`

意思是：

- 普通正文 OCR 的文字检测
- 先找出页面上哪些位置有文字

### `OCR-rec Predict`

意思是：

- 普通正文 OCR 的文字识别
- 把前面检测到的文字区域真正识别成文本

### `Seal Predict`

意思是：

- 印章/盖章区域识别
- 这在合同、公文、扫描材料里有时会出现

### `Processing pages: 28%`

意思是：

- 当前整批页面总进度
- 这是最接近“整本跑到哪了”的一个进度条

## 7. 这些进度条说明了什么

如果你看到这些条在动，通常说明：

- MinerU 的内部模型确实已经开始工作
- 不只是脚本启动成功，而是 OCR / 版面 / 表格等流程在跑

如果窗口只停在最开始几行，后面这些条完全不出现，通常表示：

- 程序还卡在初始化
- 或者本轮处理没有顺利往下推进

## 8. 对你当前用途最重要的结论

你现在主要是拿它做扫描 PDF 转 Markdown。

所以最关键的是：

- `mode: pipeline + ocr` 是对的
- `lang: ch` 是对的
- 真正有意义的运行信号，不是窗口有没有打开，而是后面这些分析进度条有没有开始动

## 9. 输出目录里常见文件作用

```text
xxx.md                     最终 Markdown
images/                    Markdown 用到的图片
xxx_middle.json            中间结构化数据
xxx_model.json             模型原始输出
xxx_content_list.json      内容列表
xxx_content_list_v2.json   新版内容列表
xxx_layout.pdf             版面调试图
xxx_span.pdf               文本块调试图
xxx_origin.pdf             原始 PDF 副本
```

如果只是日常使用，最常看的是：

```text
md + images
```

如果以后做切块或 RAG，更值得保留的是：

```text
md
images
middle.json
content_list_v2.json
origin.pdf
```
