# MCP Server 疑難排解指南

## 📋 目錄
- [常見問題](#常見問題)
- [診斷工具](#診斷工具)
- [錯誤訊息解讀](#錯誤訊息解讀)
- [依賴項安裝](#依賴項安裝)

---

## 🔍 診斷工具

### check_system 工具

MCP Server 現在提供 `check_system` 工具，可以檢查系統環境和依賴項狀態。

**使用方式：**
在 Claude Desktop 中，可以直接要求 AI 檢查系統狀態：

```
請幫我檢查 MediaToolkit 的系統狀態
```

**輸出範例：**
```
依賴項狀態:
  - pypdf: ✓ 已安裝
  - docx2pdf: ✗ 未安裝
  - pdf2docx: ✓ 已安裝
  - reportlab: ✓ 已安裝

LibreOffice:
  ✓ 已安裝於: /usr/bin/soffice

作業系統: Linux 4.4.0
Python 版本: 3.8.10

==================================================
⚠️  問題和建議
==================================================
⚠️ Word 轉 PDF 功能可能受限
   建議：
   1. pip install docx2pdf
   2. 或確保 LibreOffice 已安裝
```

---

## ❌ 常見問題

### 1. Word 轉 PDF 失敗

**症狀：**
```
❌ Word 轉 PDF 失敗
錯誤類型: Exception
錯誤訊息: 轉換函數返回 False，可能是依賴項缺失或系統配置問題
```

**原因：**
- `docx2pdf` 套件未安裝
- LibreOffice 未安裝或路徑不正確

**解決方案：**

#### 方案 1：安裝 docx2pdf（推薦 Windows 用戶）
```bash
pip install docx2pdf
```

**注意：** Windows 上的 `docx2pdf` 需要 Microsoft Word。

#### 方案 2：使用 LibreOffice（推薦 Linux/Mac 用戶）

**Linux:**
```bash
sudo apt-get install libreoffice
# 或
sudo yum install libreoffice
```

**macOS:**
```bash
brew install libreoffice
```

**Windows:**
下載安裝：https://www.libreoffice.org/download/download/

---

### 2. PDF 轉 Word 失敗

**症狀：**
```
❌ PDF 轉 Word 失敗
錯誤訊息: 轉換函數返回 False，可能是依賴項缺失或 PDF 格式問題
```

**原因：**
- `pdf2docx` 套件未安裝
- PDF 文件有密碼保護
- PDF 格式不支援（如掃描版 PDF）

**解決方案：**

#### 安裝 pdf2docx
```bash
pip install pdf2docx
```

#### PDF 格式限制
- ✅ 支援：文字型 PDF（含文字圖層）
- ❌ 不支援：純圖片 PDF（掃描版）
- ❌ 不支援：密碼保護的 PDF

---

### 3. PDF 合併功能缺少目錄或頁碼

**症狀：**
合併 PDF 成功，但沒有生成目錄或頁碼。

**原因：**
`reportlab` 套件未安裝。

**解決方案：**
```bash
pip install reportlab
```

---

## 🔧 依賴項安裝

### 完整安裝指令

**基本功能（必需）：**
```bash
pip install mcp Pillow pypdf
```

**Word/PDF 轉換（選用）：**
```bash
# Windows 用戶（需要 Microsoft Word）
pip install docx2pdf

# Linux/Mac 用戶（需要 LibreOffice）
sudo apt-get install libreoffice  # Linux
brew install libreoffice           # macOS

# PDF 轉 Word
pip install pdf2docx

# PDF 目錄和頁碼功能
pip install reportlab
```

**一次安裝所有套件：**
```bash
pip install mcp Pillow pypdf docx2pdf pdf2docx reportlab
```

---

## 📊 錯誤訊息解讀

### 詳細錯誤訊息格式

從版本更新後，所有轉換失敗都會提供詳細診斷資訊：

```
❌ [操作名稱] 失敗
錯誤類型: [異常類型]
錯誤訊息: [具體錯誤]

==================================================
診斷資訊:
==================================================
依賴項狀態:
  - pypdf: ✓/✗
  - docx2pdf: ✓/✗
  - pdf2docx: ✓/✗
  - reportlab: ✓/✗

LibreOffice:
  ✓ 已安裝於: [路徑]
  或
  ✗ 未找到

作業系統: [系統資訊]
Python 版本: [版本號]

建議:
  • [具體建議 1]
  • [具體建議 2]
```

### 常見錯誤類型

| 錯誤類型 | 可能原因 | 解決方案 |
|---------|---------|---------|
| `ModuleNotFoundError` | 缺少必要套件 | 安裝對應套件 |
| `FileNotFoundError` | LibreOffice 未安裝 | 安裝 LibreOffice |
| `ValueError` | 檔案大小超過限制 | 縮小檔案或調整限制 |
| `Exception: 轉換函數返回 False` | 多種可能 | 查看診斷資訊 |

---

## 🎯 最佳實踐

### 1. 轉換前檢查系統

建議在首次使用轉換功能前，先執行系統檢查：

```
請檢查系統狀態，確認所有功能可用
```

### 2. 分析錯誤訊息

遇到錯誤時，完整錯誤訊息會包含：
- 具體錯誤類型和訊息
- 依賴項狀態
- 系統環境資訊
- 針對性建議

請將完整錯誤訊息提供給 Claude，以獲得更準確的協助。

### 3. 環境準備建議

**文檔轉換環境（完整版）：**
```bash
# Python 套件
pip install mcp Pillow pypdf docx2pdf pdf2docx reportlab

# 系統工具（選擇一個）
# Windows: 安裝 Microsoft Word 或 LibreOffice
# Linux: sudo apt-get install libreoffice
# macOS: brew install libreoffice
```

**輕量級環境（僅圖片處理）：**
```bash
pip install mcp Pillow pypdf reportlab
```

---

## 📞 進階診斷

### 手動檢查依賴項

在終端機執行：

```bash
python3 -c "
import sys
sys.path.insert(0, '/home/user/myPicasa')
from utils.doc_converter import check_dependencies
deps = check_dependencies()
for k, v in deps.items():
    print(f'{k}: {\"✓\" if v else \"✗\"}')
"
```

### 檢查 LibreOffice

**Linux/Mac:**
```bash
which soffice
soffice --version
```

**Windows:**
檢查是否存在：
- `C:\Program Files\LibreOffice\program\soffice.exe`
- `C:\Program Files (x86)\LibreOffice\program\soffice.exe`

---

## 🔄 版本更新記錄

### v1.1 (本次更新)

**新功能：**
- ✅ 添加 `check_system` 診斷工具
- ✅ 改進錯誤訊息，提供詳細診斷資訊
- ✅ 自動檢測依賴項狀態
- ✅ 提供針對性的安裝建議

**改進：**
- 錯誤訊息從簡單的「轉換失敗」改為詳細的診斷報告
- 自動識別系統環境（Windows/Linux/macOS）
- 清楚標示每個依賴項的狀態

---

## 💡 提示

1. **環境隔離：** 建議使用虛擬環境（venv）管理依賴項
2. **權限問題：** Linux/Mac 安裝系統套件需要 sudo 權限
3. **路徑問題：** Windows 用戶注意 LibreOffice 安裝路徑
4. **大檔案處理：** 檔案大小限制可在 `mcp_server/server.py` 中調整

---

如有其他問題，請在 GitHub Issues 回報：
https://github.com/anthropics/claude-code/issues
