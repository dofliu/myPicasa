# MediaToolkit MCP Server

> **文檔和圖片處理 MCP 工具集（輕量級版本）**
> © 2025 Dof Liu AI工作室

讓 Claude AI 可以幫您處理文檔和圖片！

---

## 🎯 功能概覽

### 📄 文檔轉換
- **Word → PDF** - 將 .docx 轉換為 PDF
- **PDF → Word** - 將 PDF 轉換為 .docx
- **PDF 合併** - 合併多個 PDF（可選：添加目錄、頁碼）

### 🖼️ 圖片處理
- **圖片拼接** - 將多張圖片拼接為網格
- **創建 GIF** - 從多張圖片創建動畫 GIF
- **圖片壓縮** - 批次壓縮圖片，節省空間

### 🔧 系統工具
- **系統檢查** - 診斷環境和依賴項狀態（⭐ 新增）

---

## 📊 檔案大小限制（避免大量 token 消耗）

| 功能 | 單檔限制 | 數量限制 | 原因 |
|-----|---------|---------|------|
| Word/PDF 轉換 | 10MB | - | 避免轉換超時 |
| PDF 合併 | 10MB/個 | 最多 10 個 | 控制輸出大小 |
| 圖片拼接 | 5MB/張 | 最多 9 張 | 網格顯示限制 |
| 創建 GIF | 5MB/張 | 最多 20 張 | GIF 大小控制 |
| 圖片壓縮 | 5MB/張 | 最多 50 張 | 批次處理平衡 |

**❌ 不包含影片處理** - 影片檔案太大，會消耗過多 token

---

## 🚀 安裝步驟

### 1. 安裝依賴

```bash
# 進入專案目錄
cd /home/user/myPicasa

# 安裝 MCP SDK 和相關套件
pip install mcp Pillow pypdf docx2pdf pdf2docx reportlab
```

### 2. 設定 Claude Desktop

編輯 Claude Desktop 配置文件：

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Linux:** `~/.config/Claude/claude_desktop_config.json`

添加以下配置：

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

**注意：** 請將 `cwd` 路徑改為您的實際專案路徑。

### 3. 重啟 Claude Desktop

關閉並重新開啟 Claude Desktop，MCP Server 即可使用。

---

## 💡 使用範例

### 範例 1: Word 轉 PDF

**您:**
「幫我把這個 Word 文件轉成 PDF」
[上傳 report.docx]

**Claude:**
✅ 使用 `word_to_pdf` 工具
✅ 回傳轉換後的 PDF 文件

---

### 範例 2: 合併 PDF + 添加目錄

**您:**
「把這三個 PDF 合併，並且加上目錄頁和頁碼」
[上傳 chapter1.pdf, chapter2.pdf, chapter3.pdf]

**Claude:**
✅ 使用 `merge_pdfs` 工具
✅ 參數: `add_toc=true, add_page_numbers=true`
✅ 回傳合併後的 PDF（含目錄和頁碼）

---

### 範例 3: 圖片拼接

**您:**
「把這 4 張截圖拼成 2x2 的網格」
[上傳 4 張圖片]

**Claude:**
✅ 使用 `merge_images` 工具
✅ 參數: `rows=2, cols=2`
✅ 回傳拼接後的圖片

---

### 範例 4: 創建 GIF

**您:**
「把這些圖片做成 GIF，每張停留 0.8 秒」
[上傳多張圖片]

**Claude:**
✅ 使用 `create_gif` 工具
✅ 參數: `duration=800`（毫秒）
✅ 回傳 GIF 動畫

---

### 範例 5: 壓縮圖片

**您:**
「把這些照片壓縮成 JPG，品質 85」
[上傳多張圖片]

**Claude:**
✅ 使用 `compress_images` 工具
✅ 參數: `quality=85, output_format="jpg"`
✅ 顯示壓縮統計（節省空間）
✅ 回傳壓縮後的圖片（base64 格式）

---

## 🛠️ 可用工具清單

### 1. `word_to_pdf`
將 Word 文件轉換為 PDF

**參數:**
- `word_data` (string): Word 文件的 base64 編碼

**限制:**
- 檔案大小 ≤ 10MB

---

### 2. `pdf_to_word`
將 PDF 轉換為 Word 文件

**參數:**
- `pdf_data` (string): PDF 文件的 base64 編碼

**限制:**
- 檔案大小 ≤ 10MB

---

### 3. `merge_pdfs`
合併多個 PDF 文件

**參數:**
- `pdf_files` (array): PDF 文件的 base64 編碼陣列
- `add_toc` (boolean, 可選): 是否添加目錄頁面
- `add_page_numbers` (boolean, 可選): 是否添加頁碼

**限制:**
- 最多 10 個 PDF
- 每個 ≤ 10MB

---

### 4. `merge_images`
拼接多張圖片為網格

**參數:**
- `image_files` (array): 圖片的 base64 編碼陣列
- `rows` (integer, 預設 3): 網格行數
- `cols` (integer, 預設 3): 網格列數
- `strategy` (string, 預設 "直接縮放"): 縮放策略

**限制:**
- 最多 9 張圖片
- 每張 ≤ 5MB

---

### 5. `create_gif`
從多張圖片創建 GIF 動畫

**參數:**
- `image_files` (array): 圖片的 base64 編碼陣列
- `duration` (integer, 預設 500): 每幀持續時間（毫秒）

**限制:**
- 最多 20 張圖片
- 每張 ≤ 5MB

---

### 6. `compress_images`
壓縮圖片

**參數:**
- `image_files` (array): 圖片的 base64 編碼陣列
- `quality` (integer, 預設 75): 壓縮品質 (1-100)
- `output_format` (string, 預設 "jpg"): 輸出格式 (jpg/png/webp)

**限制:**
- 最多 50 張圖片
- 每張 ≤ 5MB

---

### 7. `check_system` ⭐ 新增
檢查系統環境和依賴項狀態

**參數:**
- 無需參數

**功能:**
- 檢測所有依賴項安裝狀態
- 檢查 LibreOffice 安裝情況
- 顯示作業系統和 Python 版本
- 提供針對性的安裝建議

**使用時機:**
- ✅ 首次使用前，確認環境配置
- ✅ 轉換功能失敗時，診斷問題
- ✅ 安裝新依賴後，驗證安裝

**範例輸出:**
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

⚠️ Word 轉 PDF 功能可能受限
   建議：
   1. pip install docx2pdf
   2. 或確保 LibreOffice 已安裝
```

---

## 🔍 故障排除

### 🆕 自動診斷工具（推薦）

**首先使用 `check_system` 工具診斷問題：**

在 Claude Desktop 中輸入：
```
請檢查 MediaToolkit 系統狀態
```

系統會自動：
- ✅ 檢測所有依賴項
- ✅ 檢查 LibreOffice 安裝
- ✅ 提供針對性建議

### 📖 完整疑難排解指南

遇到問題時，請參考：

**[MCP_TROUBLESHOOTING.md](../MCP_TROUBLESHOOTING.md)** - 完整疑難排解指南

內容包含：
- 詳細錯誤訊息解讀
- 常見問題解決方案
- 依賴項安裝指引
- 進階診斷方法

### 快速參考

### 問題 1: MCP Server 未出現在 Claude Desktop

**解決方法:**
1. 確認配置文件路徑正確
2. 確認 JSON 格式正確（無語法錯誤）
3. 確認 `cwd` 路徑是絕對路徑
4. 重啟 Claude Desktop

### 問題 2: 轉換功能失敗

**立即執行：**
```
使用 check_system 工具檢查系統狀態
```

**常見原因：**
1. 缺少依賴套件（docx2pdf、pdf2docx、reportlab）
2. LibreOffice 未安裝（Linux/Mac）
3. 檔案格式不支援（如掃描版 PDF）

### 問題 3: PDF 轉換失敗（Windows）

**解決方法:**
- Word → PDF: 需要安裝 Microsoft Word
- PDF → Word: 使用 pdf2docx（已包含）

---

## 📋 技術細節

### 檔案傳輸方式
- **輸入**: Base64 編碼（Claude 自動處理）
- **輸出**: Base64 編碼 + MIME type

### 臨時檔案管理
- 自動創建臨時檔案
- 處理完成後自動清理
- 異常情況也會清理（try-finally）

### 錯誤處理
- 檔案大小驗證
- 數量限制檢查
- 詳細錯誤訊息

---

## 🎓 延伸閱讀

- [MCP 官方文檔](https://modelcontextprotocol.io/)
- [Claude Desktop 設定](https://claude.ai/docs)
- [MediaToolkit 桌面版](../README.md)

---

## 📝 版本資訊

**v1.0.0** (2025)
- ✅ Word/PDF 互轉
- ✅ PDF 合併（含目錄、頁碼）
- ✅ 圖片拼接
- ✅ GIF 創建
- ✅ 圖片壓縮
- ❌ 影片處理（已排除）

---

## 🤝 支援

**問題回報:** GitHub Issues
**作者:** Dof Liu AI工作室
**授權:** © 2025 All Rights Reserved
