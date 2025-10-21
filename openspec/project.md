# Project Context

## Purpose
本專案是一個使用 PyQt5 開發的桌面應用程式，主要目標是提供使用者一個簡單易用的工具，用於圖片和影片的整理與處理。其核心功能包括：
1.  **圖片拼接/合併**：將多張圖片按照使用者定義的網格佈局拼接成一張圖片。
2.  **GIF 動畫生成**：從一系列選定的圖片中生成動畫 GIF。
3.  **影片合併**：將多個影片檔案合併為一個單一影片檔案。
4.  **圖片格式轉換**：將圖片轉換為不同的格式（例如：JPG, PNG, WEBP 等）。

**使用者介面**: 採用分頁式介面，將不同功能模組化，提供更清晰的操作體驗。

## Tech Stack
- **GUI 框架**: PyQt5
- **圖片處理**: Pillow (PIL - Python Imaging Library)
- **影片處理**: MoviePy
- **排序**: natsort
- **程式語言**: Python

## Project Conventions

### Code Style
- **命名慣例**: 變數和方法名稱混合使用英文和中文/拼音。
- **註解**: 使用繁體中文進行註解，解釋程式碼邏輯或功能。

### Architecture Patterns
- 採用類似 MVC 的模式，其中 `ImageTool` 類別作為視圖和控制器，處理使用者介面和互動邏輯。
- 圖片資料和處理邏輯主要由 Pillow 庫和相關輔助函數（如 `resize_with_padding`）負責。
- 應用程式是事件驅動的，利用 PyQt5 的信號與槽機制處理使用者操作。

### Testing Strategy
目前專案中沒有明確的測試策略或測試檔案。

### Git Workflow
目前專案中沒有明確定義的 Git 工作流程。

## Domain Context
本專案的領域上下文主要圍繞著圖片處理和使用者介面互動。涉及圖片的讀取、縮放、拼接、以及生成動畫 GIF 等操作。

## Important Constraints
目前專案中沒有明確列出重要限制。

## External Dependencies
- **PyQt5**: 用於建立圖形使用者介面 (GUI)。
- **Pillow (PIL)**: 用於圖片的讀取、處理和儲存。
- **MoviePy**: 用於影片的讀取、編輯和合併。
- **natsort**: 用於自然排序檔案名稱。
