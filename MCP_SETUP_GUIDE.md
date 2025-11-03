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
   ```bash
   # Linux - 強制終止
   pkill -9 claude
   ```

2. **重新開啟** Claude Desktop

3. **檢查 Developer Tools**（可選）
   - 在 Claude Desktop 中按 `Ctrl+Shift+I`（或從選單開啟）
   - 查看 Console 中是否有錯誤訊息

---

### 步驟 3: 確認 Server 已載入

在 Claude Desktop 中：

**方法 1: 詢問工具**

您：
```
你有哪些工具可以用？
```

Claude 應該列出 `media-toolkit` 相關的 6 個工具。

**方法 2: 直接使用**

您：
```
幫我列出 media-toolkit 的所有功能
```

---

## 💡 使用範例

### 範例 1: Word 轉 PDF

**您：**
```
幫我把這個 Word 轉成 PDF
```
[上傳 document.docx]

**Claude 會：**
1. 使用 `word_to_pdf` 工具
2. 回傳轉換後的 PDF

---

### 範例 2: 合併 PDF（含目錄）

**您：**
```
把這三個 PDF 合併，加上目錄和頁碼
```
[上傳 3 個 PDF]

**Claude 會：**
1. 使用 `merge_pdfs` 工具
2. 參數：`add_toc=true, add_page_numbers=true`
3. 回傳合併後的 PDF

---

### 範例 3: 圖片拼接

**您：**
```
把這 4 張圖拼成 2x2 網格
```
[上傳 4 張圖片]

**Claude 會：**
1. 使用 `merge_images` 工具
2. 參數：`rows=2, cols=2`
3. 回傳拼接結果

---

### 範例 4: 創建 GIF

**您：**
```
把這些圖片做成 GIF，每張顯示 1 秒
```
[上傳多張圖片]

**Claude 會：**
1. 使用 `create_gif` 工具
2. 參數：`duration=1000` (毫秒)
3. 回傳 GIF

---

### 範例 5: 壓縮圖片

**您：**
```
幫我壓縮這些照片，品質設 80
```
[上傳多張照片]

**Claude 會：**
1. 使用 `compress_images` 工具
2. 參數：`quality=80`
3. 顯示壓縮統計（節省多少空間）

---

## 🔧 故障排除

### 問題 1: Claude Desktop 中看不到 media-toolkit

**可能原因：**
1. 配置文件路徑錯誤
2. JSON 格式錯誤
3. `cwd` 路徑不正確
4. 未重啟 Claude Desktop

**解決方法：**

```bash
# 1. 驗證配置文件存在
ls ~/.config/Claude/claude_desktop_config.json

# 2. 檢查 JSON 格式
python -c "import json; json.load(open('/home/user/.config/Claude/claude_desktop_config.json'))"

# 3. 確認專案路徑
ls /home/user/myPicasa/mcp_server/server.py

# 4. 完全重啟 Claude Desktop
pkill -9 claude
# 然後重新開啟
```

---

### 問題 2: Server 啟動失敗

**錯誤訊息：** `ModuleNotFoundError: No module named 'mcp'`

**解決方法：**
```bash
pip install mcp
```

---

**錯誤訊息：** `ModuleNotFoundError: No module named 'utils'`

**解決方法：**
```bash
# 確認在正確的目錄
cd /home/user/myPicasa
python -m mcp_server.server
```

---

### 問題 3: 工具執行失敗

**錯誤訊息：** `檔案過大`

**原因：** 超過大小限制

**限制：**
- Word/PDF: 10MB
- 圖片: 5MB
- PDF 數量: 最多 10 個
- 圖片數量: 視功能而定（9-50 張）

---

### 問題 4: Word 轉 PDF 失敗（Windows）

**可能原因：** 缺少 Microsoft Word

**解決方法：**
1. 安裝 Microsoft Word
2. 或使用線上轉換（如 LibreOffice）

**Linux 替代方案：**
```bash
# 安裝 LibreOffice
sudo apt-get install libreoffice
```

---

### 問題 5: 檢查 Server 日誌

**在 Claude Desktop 中查看日誌：**
1. 按 `Ctrl+Shift+I` 開啟 Developer Tools
2. 切換到 "Console" 標籤
3. 查找 `media-toolkit` 相關訊息
4. 檢查錯誤訊息

---

## 📊 功能限制摘要

| 工具 | 單檔限制 | 數量限制 | 原因 |
|-----|---------|---------|------|
| word_to_pdf | 10MB | - | 轉換效能 |
| pdf_to_word | 10MB | - | 轉換效能 |
| merge_pdfs | 10MB/個 | 10 個 | 輸出控制 |
| merge_images | 5MB/張 | 9 張 | 網格顯示 |
| create_gif | 5MB/張 | 20 張 | GIF 大小 |
| compress_images | 5MB/張 | 50 張 | 批次平衡 |

**不支援：**
- ❌ 影片合併（檔案太大）
- ❌ 影片轉 GIF（檔案太大）

---

## 🎯 快速測試腳本

創建測試腳本快速驗證：

```bash
# 創建測試腳本
cat > /home/user/myPicasa/test_mcp.sh << 'EOF'
#!/bin/bash
echo "🔍 測試 MCP Server 設定..."

# 1. 檢查 Python 版本
echo "1️⃣ Python 版本:"
python --version

# 2. 檢查依賴
echo -e "\n2️⃣ 檢查依賴:"
python -c "import mcp; print('✅ MCP')" 2>/dev/null || echo "❌ MCP 未安裝"
python -c "from PIL import Image; print('✅ Pillow')" 2>/dev/null || echo "❌ Pillow 未安裝"
python -c "import pypdf; print('✅ pypdf')" 2>/dev/null || echo "❌ pypdf 未安裝"

# 3. 檢查配置文件
echo -e "\n3️⃣ 配置文件:"
if [ -f ~/.config/Claude/claude_desktop_config.json ]; then
    echo "✅ 配置文件存在"
    python -c "import json; json.load(open('$HOME/.config/Claude/claude_desktop_config.json'))" 2>/dev/null && echo "✅ JSON 格式正確" || echo "❌ JSON 格式錯誤"
else
    echo "❌ 配置文件不存在"
fi

# 4. 檢查專案結構
echo -e "\n4️⃣ 專案結構:"
[ -f mcp_server/server.py ] && echo "✅ server.py 存在" || echo "❌ server.py 不存在"
[ -d utils ] && echo "✅ utils/ 目錄存在" || echo "❌ utils/ 目錄不存在"

echo -e "\n✅ 測試完成！"
EOF

chmod +x /home/user/myPicasa/test_mcp.sh

# 執行測試
cd /home/user/myPicasa
./test_mcp.sh
```

---

## 📞 需要幫助？

1. **檢查日誌** - Claude Desktop Developer Tools
2. **驗證配置** - 使用上面的測試腳本
3. **重新安裝依賴** - `pip install --force-reinstall mcp`
4. **查看文檔** - `mcp_server/README.md`

---

## ✅ 設定成功標誌

當您成功設定後，應該能：

1. ✅ 在 Claude Desktop 中看到 media-toolkit 工具
2. ✅ 上傳檔案並讓 Claude 處理
3. ✅ 獲得處理結果（PDF、圖片等）
4. ✅ 桌面 UI (`picasa6.py`) 仍正常運作

---

**祝您使用順利！** 🎉
