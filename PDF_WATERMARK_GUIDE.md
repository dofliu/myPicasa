# PDF 浮水印功能使用指南

## 功能概述

PDF 浮水印功能允許您為 PDF 文件添加文字或圖片浮水印，支援自訂位置、透明度、大小等參數。

## 功能特色

### 文字浮水印
- ✅ 自訂浮水印文字內容
- ✅ 可調整字體大小（10-200）
- ✅ 支援旋轉角度（-180° 到 180°）
- ✅ 自動使用系統中文字體
- ✅ 支援透明度調整

### 圖片浮水印
- ✅ 支援 PNG、JPG、JPEG、BMP 格式
- ✅ PNG 格式支援透明背景
- ✅ 可調整縮放比例（5%-50%）
- ✅ 支援透明度調整

### 通用設定
- ✅ 5 種位置選擇：正中央、左上角、右上角、左下角、右下角
- ✅ 透明度調整（10%-100%）
- ✅ 邊距調整（0-100 像素）- 控制浮水印與頁面邊緣的距離
- ✅ 自動套用到所有頁面

## 使用方式

### 在 GUI 介面中使用

1. **啟動應用程式**
   ```bash
   python picasa6.py
   ```

2. **切換到文件轉換工具分頁**
   - 點擊頂部的「📄 文件轉換工具」分頁
   - 選擇「🏷️ PDF 浮水印」子分頁

3. **選擇 PDF 文件**
   - 點擊「📂 瀏覽」按鈕
   - 選擇要添加浮水印的 PDF 文件

4. **選擇浮水印類型**
   - **文字浮水印**：輸入文字內容，調整字體大小和旋轉角度
   - **圖片浮水印**：選擇浮水印圖片，調整縮放比例

5. **設定通用參數**
   - **浮水印位置**：選擇浮水印在頁面上的位置
   - **透明度**：調整浮水印的透明程度
   - **邊距**：設定浮水印與頁面邊緣的距離（預設 10px，設為 0 可完全貼邊）

6. **執行**
   - 點擊「✨ 添加浮水印」按鈕
   - 選擇輸出檔案的儲存位置
   - 等待處理完成

### 在程式碼中使用

#### 添加文字浮水印

```python
from utils.doc_converter import add_text_watermark_to_pdf

# 基本用法
add_text_watermark_to_pdf(
    input_path="input.pdf",
    output_path="output_with_text.pdf",
    watermark_text="© 2025 機密文件",
    position='center',
    opacity=0.3,
    font_size=40,
    rotation=45
)
```

**參數說明：**
- `input_path`: 輸入 PDF 路徑
- `output_path`: 輸出 PDF 路徑
- `watermark_text`: 浮水印文字
- `position`: 位置（'center', 'top-left', 'top-right', 'bottom-left', 'bottom-right'）
- `opacity`: 透明度（0.0-1.0）
- `font_size`: 字體大小
- `rotation`: 旋轉角度（度）
- `margin`: 邊距（像素，預設 10）

#### 添加圖片浮水印

```python
from utils.doc_converter import add_image_watermark_to_pdf

# 基本用法
add_image_watermark_to_pdf(
    input_path="input.pdf",
    output_path="output_with_image.pdf",
    watermark_image_path="logo.png",
    position='bottom-right',
    opacity=0.5,
    scale=0.2
)
```

**參數說明：**
- `input_path`: 輸入 PDF 路徑
- `output_path`: 輸出 PDF 路徑
- `watermark_image_path`: 浮水印圖片路徑
- `position`: 位置（'center', 'top-left', 'top-right', 'bottom-left', 'bottom-right'）
- `opacity`: 透明度（0.0-1.0）
- `scale`: 縮放比例（相對於頁面寬度，例如 0.2 表示 20%）
- `margin`: 邊距（像素，預設 10）

## 位置說明

```
┌─────────────────────────────┐
│ top-left      top-right     │
│                             │
│         center              │
│                             │
│ bottom-left  bottom-right  │
└─────────────────────────────┘
```

## 使用範例

### 範例 1：為合約添加機密標記

```python
from utils.doc_converter import add_text_watermark_to_pdf

add_text_watermark_to_pdf(
    "contract.pdf",
    "contract_confidential.pdf",
    "機密文件 CONFIDENTIAL",
    position='center',
    opacity=0.2,
    font_size=60,
    rotation=45,
    color=(255, 0, 0)  # 紅色
)
```

### 範例 2：添加公司 Logo

```python
from utils.doc_converter import add_image_watermark_to_pdf

add_image_watermark_to_pdf(
    "report.pdf",
    "report_branded.pdf",
    "company_logo.png",
    position='top-right',
    opacity=0.7,
    scale=0.15
)
```

### 範例 3：頁腳版權聲明

```python
from utils.doc_converter import add_text_watermark_to_pdf

add_text_watermark_to_pdf(
    "document.pdf",
    "document_copyrighted.pdf",
    "© 2025 Your Company. All Rights Reserved.",
    position='bottom-right',
    opacity=0.5,
    font_size=12,
    rotation=0
)
```

### 範例 4：母片底稿效果（完全貼邊）

```python
from utils.doc_converter import add_text_watermark_to_pdf

# 右下角完全貼邊的浮水印，適合母片底稿
add_text_watermark_to_pdf(
    "template.pdf",
    "template_marked.pdf",
    "DRAFT - 草稿",
    position='bottom-right',
    opacity=0.3,
    font_size=14,
    rotation=0,
    margin=5  # 設定較小的邊距，更貼近邊緣
)
```

### 範例 5：圖片浮水印貼邊

```python
from utils.doc_converter import add_image_watermark_to_pdf

# 公司 Logo 緊貼右下角
add_image_watermark_to_pdf(
    "report.pdf",
    "report_branded.pdf",
    "company_logo.png",
    position='bottom-right',
    opacity=0.8,
    scale=0.15,
    margin=5  # 更貼近邊緣
)
```

## 測試

專案提供了測試腳本 `test_pdf_watermark.py` 用於測試 PDF 浮水印功能：

```bash
python test_pdf_watermark.py
```

**測試前準備：**
1. 準備測試 PDF 文件（命名為 `test_input.pdf`）
2. 準備浮水印圖片（命名為 `watermark.png`，用於測試圖片浮水印）

## 系統需求

### 必要套件
- `pypdf` - PDF 文件處理
- `reportlab` - PDF 生成和繪圖
- `Pillow` - 圖片處理（用於圖片浮水印）

### 安裝依賴

```bash
pip install pypdf reportlab Pillow
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

## 支援的字型

系統會根據作業系統自動選擇合適的中文字型：

- **Windows**: 微軟正黑體 (msjh.ttc) 或新細明體 (simsun.ttc)
- **Linux**: Noto Sans CJK 或文泉驛正黑
- **macOS**: PingFang 或黑體

## 常見問題

### Q: 為什麼浮水印的中文字顯示不正確？

A: 確保系統已安裝中文字體。程式會自動嘗試載入系統中文字體，如果載入失敗會使用預設字體。

### Q: 可以為 PDF 的特定頁面添加浮水印嗎？

A: 目前功能會自動為所有頁面添加浮水印。如需為特定頁面添加，可以修改 `doc_converter.py` 中的相關函數。

### Q: 浮水印會影響 PDF 的文字選取或複製嗎？

A: 不會。浮水印是作為圖層覆蓋在原始內容上，不會影響原始文字。

### Q: 支援批次處理多個 PDF 嗎？

A: 目前 GUI 介面一次處理一個 PDF。如需批次處理，可以編寫 Python 腳本循環調用浮水印函數。

### Q: 浮水印圖片的最佳格式是什麼？

A: 建議使用 PNG 格式，支援透明背景，效果最佳。

## 進階用法

### 批次添加浮水印

```python
import os
from utils.doc_converter import add_text_watermark_to_pdf

# 批次處理資料夾中的所有 PDF
input_folder = "pdfs"
output_folder = "watermarked_pdfs"

os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if filename.endswith('.pdf'):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)

        add_text_watermark_to_pdf(
            input_path,
            output_path,
            "© 2025 Your Company",
            position='bottom-right',
            opacity=0.3
        )
        print(f"已處理: {filename}")
```

### 根據條件動態設定浮水印

```python
from utils.doc_converter import add_text_watermark_to_pdf
import datetime

# 根據日期生成浮水印
today = datetime.date.today()
watermark_text = f"列印日期: {today.strftime('%Y-%m-%d')}"

add_text_watermark_to_pdf(
    "document.pdf",
    "document_dated.pdf",
    watermark_text,
    position='bottom-left',
    opacity=0.5,
    font_size=10,
    rotation=0
)
```

## 技術細節

### 實作原理

1. **文字浮水印**：
   - 使用 ReportLab 創建包含文字的臨時 PDF
   - 設定字體、顏色、透明度
   - 使用 PyPDF 將浮水印 PDF 合併到原始頁面

2. **圖片浮水印**：
   - 使用 Pillow 載入並處理圖片
   - 調整圖片大小和透明度
   - 使用 ReportLab 將圖片繪製到臨時 PDF
   - 使用 PyPDF 合併到原始頁面

### 效能考量

- 處理大型 PDF（100+ 頁）可能需要較長時間
- 建議浮水印圖片不要太大（推薦 500x500 像素以內）
- 透明度設定越低，處理速度越快

## 更新日誌

### v6.0 (2025-01)
- ✨ 新增 PDF 浮水印功能
- ✨ 支援文字和圖片浮水印
- ✨ 支援 5 種位置選擇
- ✨ 支援透明度和旋轉角度調整
- ✨ GUI 整合完成

## 授權

本功能屬於 MediaToolkit v6.0 的一部分，遵循 MIT 授權條款。

## 作者

**Dof Liu AI工作室**
© 2025 All Rights Reserved.

## 技術支援

如有問題或建議，請聯繫開發團隊或在 GitHub 提交 Issue。
