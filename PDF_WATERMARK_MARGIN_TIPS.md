# PDF 浮水印邊距調整技巧

## 邊距功能說明

邊距參數控制浮水印與頁面邊緣的距離，範圍為 **0-100 像素**。

## 建議設定

### 🎯 母片底稿效果（完全貼邊）
**邊距：0-5 像素**

適用場景：
- 公文底稿標記
- 草稿版本標示
- 模板母片標記
- 需要明確且緊貼邊緣的標示

```python
add_text_watermark_to_pdf(
    "template.pdf",
    "template_draft.pdf",
    "草稿 DRAFT",
    position='bottom-right',
    opacity=0.3,
    font_size=14,
    rotation=0,
    margin=3  # 幾乎完全貼邊
)
```

視覺效果：
```
┌────────────────────────┐
│                        │
│                        │
│                        │
│                  DRAFT─┤  ← 緊貼邊緣
└────────────────────────┘
```

### 📄 一般浮水印（預設）
**邊距：10-20 像素**

適用場景：
- 一般文件標記
- 版權聲明
- 機密標示
- 日常使用

```python
add_text_watermark_to_pdf(
    "document.pdf",
    "document_watermarked.pdf",
    "© 2025 Company",
    position='bottom-right',
    opacity=0.4,
    font_size=12,
    rotation=0,
    margin=10  # 預設邊距
)
```

視覺效果：
```
┌────────────────────────┐
│                        │
│                        │
│                        │
│              © 2025    │  ← 適當距離
└────────────────────────┘
```

### 🖼️ 圖片浮水印（舒適距離）
**邊距：20-30 像素**

適用場景：
- 公司 Logo
- 品牌標識
- 圖形浮水印
- 需要留白的設計

```python
add_image_watermark_to_pdf(
    "report.pdf",
    "report_branded.pdf",
    "logo.png",
    position='bottom-right',
    opacity=0.7,
    scale=0.15,
    margin=25  # 較大邊距
)
```

視覺效果：
```
┌────────────────────────┐
│                        │
│                        │
│                        │
│            [LOGO]      │  ← 舒適留白
└────────────────────────┘
```

### 🎨 藝術效果（大邊距）
**邊距：40-100 像素**

適用場景：
- 設計文件
- 展示用途
- 強調留白美學
- 避免裁切

```python
add_text_watermark_to_pdf(
    "design.pdf",
    "design_marked.pdf",
    "Preview",
    position='bottom-right',
    opacity=0.5,
    font_size=24,
    rotation=0,
    margin=50  # 大邊距
)
```

## 不同位置的邊距建議

### 角落位置（top-left, top-right, bottom-left, bottom-right）
- **貼邊效果**：0-5px
- **一般效果**：10-15px
- **舒適效果**：20-30px

### 中央位置（center）
- 邊距參數不影響中央位置
- 浮水印始終置中

## GUI 操作

在 picasa6.py 的 PDF 浮水印分頁中：

1. 找到「通用設定」區域
2. 調整「邊距 (px)」數值
   - **向左拖動**：減少邊距（更貼邊）
   - **向右拖動**：增加邊距（更多留白）
3. 即時顯示當前設定值
4. 工具提示說明功能用途

## 實際案例

### 案例 1：公文底稿
```python
# 需求：右下角草稿標記，完全貼邊
add_text_watermark_to_pdf(
    "official_doc.pdf",
    "official_doc_draft.pdf",
    "草稿",
    position='bottom-right',
    opacity=0.3,
    font_size=16,
    rotation=0,
    margin=2  # 幾乎無邊距
)
```

### 案例 2：合約版權
```python
# 需求：底部版權聲明，保持閱讀舒適
add_text_watermark_to_pdf(
    "contract.pdf",
    "contract_copyrighted.pdf",
    "© 2025 Company. Confidential.",
    position='bottom-right',
    opacity=0.4,
    font_size=10,
    rotation=0,
    margin=15  # 適中邊距
)
```

### 案例 3：品牌報告
```python
# 需求：公司 Logo，美觀呈現
add_image_watermark_to_pdf(
    "annual_report.pdf",
    "annual_report_branded.pdf",
    "company_logo.png",
    position='bottom-right',
    opacity=0.8,
    scale=0.12,
    margin=30  # 較大邊距，更精緻
)
```

## 注意事項

### ⚠️ 裁切風險
邊距 **0-5px** 時：
- 某些印刷設備可能會裁切浮水印
- 建議在正式印刷前進行測試
- 電子版不受影響

### ✅ 建議作法
1. **先測試**：使用單頁 PDF 測試效果
2. **查看預覽**：確認浮水印位置
3. **考慮用途**：
   - 電子文件：可以更貼邊（0-5px）
   - 列印文件：建議留邊距（10-20px）
4. **批次處理**：確定參數後再批次處理

### 💡 專業提示
- **母片效果**：使用 0-5px + 小字體 + 低透明度
- **品牌標識**：使用 20-30px + 適當縮放 + 中等透明度
- **版權聲明**：使用 10-15px + 小字體 + 中低透明度
- **設計作品**：使用 40-60px + 大字體 + 高透明度

## 快速參考表

| 用途 | 建議邊距 | 透明度 | 字體/縮放 |
|------|---------|--------|----------|
| 母片底稿 | 0-5px | 20-30% | 小-中 |
| 草稿標記 | 5-10px | 30-40% | 中 |
| 一般標記 | 10-20px | 30-50% | 中 |
| Logo 浮水印 | 20-30px | 60-80% | 15-20% |
| 版權聲明 | 10-15px | 40-50% | 小 |
| 藝術設計 | 40-100px | 50-70% | 大 |

## 更多資訊

詳細功能說明請參閱：
- [PDF_WATERMARK_GUIDE.md](PDF_WATERMARK_GUIDE.md) - 完整使用指南
- [README.md](README.md) - 專案總覽

---

**提示**：使用 GUI 介面時，可以即時調整邊距並重新處理，直到找到最適合的設定！
