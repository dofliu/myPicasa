# MediaToolkit MCP Server 完整設定指南

> **一步步教您將 MCP Server 加入 Claude Desktop**

---

## 📋 目錄

1. [快速檢查](#快速檢查)
2. [安裝依賴](#安裝依賴)
3. [配置 Claude Desktop](#配置-claude-desktop)
4. [驗證設定](#驗證設定)
5. [使用範例](#使用範例)
6. [故障排除](#故障排除)

---

## 🔍 快速檢查

### ✨ 重大更新：支援直接檔案路徑
現在，不再需要繁瑣的 Base64 編碼！您可以直接將 **本地檔案路徑** 傳給 MCP 工具。
- AI 可以直接呼叫: `word_to_pdf(word_path="D:/Documents/report.docx")`
- **📂 檔案自動儲存：** 處理結果會自動儲存在**輸入檔案的同一個目錄**下（例如 `report.pdf`）。

### 確認桌面 UI 仍可使用

```bash
# 原本的桌面程式不受影響
cd /home/user/myPicasa
python picasa6.py
```

✅ **兩者完全獨立：**
- 桌面 UI (`picasa6.py`) - 圖形介面，所有功能
- MCP Server (`mcp_server/`) - AI 工具，輕量級功能

---

## 📦 安裝依賴

### 步驟 1: 檢查 Python 版本

```bash
python --version
```

**要求：** Python >= 3.10

---

### 步驟 2: 安裝套件

```bash
cd /home/user/myPicasa

# 安裝所有依賴
pip install mcp Pillow pypdf docx2pdf pdf2docx reportlab
```

---

### 步驟 3: 驗證安裝

```bash
# 測試 MCP SDK
python -c "import mcp; print('✅ MCP SDK 已安裝')"

# 測試其他套件
python -c "from PIL import Image; import pypdf; print('✅ 所有套件已安裝')"
```

---

## ⚙️ 配置 Claude Desktop

### 步驟 1: 找到配置文件

**Linux:**
```bash
~/.config/Claude/claude_desktop_config.json
```

**macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

---

### 步驟 2: 創建/編輯配置文件

```bash
# Linux
mkdir -p ~/.config/Claude
nano ~/.config/Claude/claude_desktop_config.json
```

---

### 步驟 3: 添加配置

**如果檔案是空的（新建）：**

```json
{
  "mcpServers": {
    "media-toolkit": {
      "command": "python",
      "args": [
        "-m",
        "mcp_server.server"
      ],
      "cwd": "/home/user/myPicasa"
    }
  }
}
```

**如果已有其他 MCP Server：**

```json
{
  "mcpServers": {
    "existing-server": {
      "command": "...",
      "args": ["..."]
    },
    "media-toolkit": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/home/user/myPicasa"
    }
  }
}
```

**⚠️ 重要：**
- `cwd` 必須是**絕對路徑**
- 改為您的實際專案路徑
- 確認 JSON 格式正確

---

### 步驟 4: 驗證 JSON 格式

```bash
# Linux/macOS
python -c "import json; json.load(open('~/.config/Claude/claude_desktop_config.json'.replace('~', '$HOME'))); print('✅ JSON 格式正確')"

# 或使用線上工具
cat ~/.config/Claude/claude_desktop_config.json
# 複製內容到 https://jsonlint.com/ 驗證
```

---

## ✅ 驗證設定

### 步驟 1: 測試 MCP Server（獨立）

```bash
cd /home/user/myPicasa
python -m mcp_server.server
```

**預期：**
- Server 啟動，無錯誤訊息
- 按 `Ctrl+C` 停止

**如果出錯：**
- 檢查依賴是否全部安裝
- 確認 `utils/` 目錄存在

---

### 步驟 2: 重啟 Claude Desktop

1. **完全關閉** Claude Desktop
2. **重新開啟** Claude Desktop
3. **檢查 Developer Tools**

---

### 步驟 3: 確認 Server 已載入

在 Claude Desktop 中：

**方法 1: 詢問工具**
> "你有哪些工具可以用？"

**方法 2: 直接使用**
> "幫我把這個 PDF 轉成 Word: `D:\Docs\test.pdf`"

---

## 💡 使用範例

### 範例 1: Word 轉 PDF (自動存檔)

**您：**
> "請幫我把這個檔案轉成 PDF: `D:\Documents\report.docx`"

**Claude 會：**
1. 傳送 `word_path="D:\Documents\report.docx"`
2. Server 進行轉換...
3. **自動儲存：** `D:\Documents\report.pdf` 會自動出現在該資料夾！
4. 顯示成功訊息。

---

### 範例 2: 合併 PDF（自動存檔）

**您：**
> "幫我合併這兩個 PDF: `D:\Docs\part1.pdf`, `D:\Docs\part2.pdf`"

**Claude 會：**
1. 傳送 `pdf_paths=[...]`
2. **自動儲存：** `D:\Docs\merged_output.pdf`
3. 顯示成功訊息。

---

### 範例 3: 圖片拼接

**您：**
> "把這個資料夾裡的照片拼成 2x2 網格: `D:\Photos`"

**Claude 會：**
1. **自動儲存：** `D:\Photos\merged_grid.png`
2. 顯示成功訊息。

---

## 🔧 故障排除

### 問題 1: 找不到輸出的檔案？

**舊版行為：** 在升級前，Server 轉換後會回傳內容但**刪除**臨時檔案。
**新版行為 (v2.0)：** 只要您使用 `path` (路徑) 方式呼叫，檔案就會**保留**在原始目錄。
- 如果找不到，請確認是否有更新到最新的 `server.py`。
- 檢查檔案是否有重名，系統會自動命名為 `filename_1.docx` 等。

---

### 問題 2: Server 啟動失敗

**錯誤訊息：** `AttributeError: module 'mcp.server.stdio' has no attribute 'run'`
**解決方法：** 請更新 `server.py`，我們已改用新的 `asyncio` 啟動方式。

---

## 📊 功能限制摘要

| 工具 | 單檔限制 | 數量限制 | 備註 |
|-----|---------|---------|------|
| word_to_pdf | 10MB | - | 也可使用 LibreOffice |
| pdf_to_word | 10MB | - | |
| merge_pdfs | 10MB/個 | 10 個 | |
| merge_images | 5MB/張 | 9 張 | |
| batch_rename | - | - | 直接本機操作 |
| batch_edit_images | - | - | 產生副本或覆蓋 |

---

### 範例 6: 批次重新命名
> "把這個資料夾的檔案重新命名為 'Photo_001.jpg': `D:\Photos`"

### 範例 7: 批次旋轉
> "把這些照片順時針轉 90 度: `D:\Photos\Trip`"

---
**祝您使用順利！** 🎉
