#!/usr/bin/env python3
"""
MediaToolkit MCP Server
提供文檔和圖片處理工具
"""

import os
import sys
import tempfile
import base64
import subprocess
import platform
import traceback
from pathlib import Path
from typing import Optional

# 添加父目錄到 Python 路徑，以便導入 utils
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import mcp.server.stdio

from utils import (
    convert_word_to_pdf,
    convert_pdf_to_word,
    merge_pdfs,
    resize_image
)
from utils.doc_converter import check_dependencies
from PIL import Image

# 檔案大小限制（位元組）
MAX_PDF_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_PDFS_COUNT = 10  # 最多合併 10 個 PDF
MAX_IMAGES_COUNT = 20  # 最多處理 20 張圖片

# 創建 MCP Server
server = Server("media-toolkit")


def validate_file_size(file_path: str, max_size: int, file_type: str) -> None:
    """驗證檔案大小"""
    if not os.path.exists(file_path):
        raise ValueError(f"{file_type} 檔案不存在: {file_path}")

    size = os.path.getsize(file_path)
    if size > max_size:
        raise ValueError(
            f"{file_type} 檔案過大: {size / (1024*1024):.2f}MB "
            f"(限制: {max_size / (1024*1024):.0f}MB)"
        )


def save_base64_file(base64_data: str, suffix: str) -> str:
    """保存 base64 編碼的檔案到臨時位置"""
    # 移除可能的 data URL 前綴
    if ',' in base64_data:
        base64_data = base64_data.split(',', 1)[1]

    file_data = base64.b64decode(base64_data)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(file_data)
    temp_file.close()

    return temp_file.name


def file_to_base64(file_path: str) -> str:
    """將檔案轉換為 base64"""
    with open(file_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_diagnostic_info() -> str:
    """獲取診斷資訊"""
    info = []

    # 檢查依賴項
    deps = check_dependencies()
    info.append("依賴項狀態:")
    for dep, installed in deps.items():
        status = "✓ 已安裝" if installed else "✗ 未安裝"
        info.append(f"  - {dep}: {status}")

    # 檢查 LibreOffice
    soffice_path = None
    system = platform.system()
    if system == 'Windows':
        soffice_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
        ]
        for path in soffice_paths:
            if os.path.exists(path):
                soffice_path = path
                break
    else:
        try:
            result = subprocess.run(['which', 'soffice'],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                soffice_path = result.stdout.strip()
        except:
            pass

    info.append(f"\nLibreOffice:")
    if soffice_path:
        info.append(f"  ✓ 已安裝於: {soffice_path}")
    else:
        info.append(f"  ✗ 未找到")

    info.append(f"\n作業系統: {platform.system()} {platform.release()}")
    info.append(f"Python 版本: {sys.version.split()[0]}")

    return "\n".join(info)


def format_error_message(operation: str, error: Exception, include_diagnostic: bool = True) -> str:
    """格式化錯誤訊息"""
    lines = [f"❌ {operation} 失敗"]
    lines.append(f"錯誤類型: {type(error).__name__}")
    lines.append(f"錯誤訊息: {str(error)}")

    if include_diagnostic:
        lines.append("\n" + "="*50)
        lines.append("診斷資訊:")
        lines.append("="*50)
        lines.append(get_diagnostic_info())
        lines.append("\n建議:")

        deps = check_dependencies()
        if not deps.get('docx2pdf'):
            lines.append("  • 安裝 docx2pdf: pip install docx2pdf")
            lines.append("  • 或安裝 LibreOffice 作為替代方案")
        if not deps.get('pdf2docx'):
            lines.append("  • 安裝 pdf2docx: pip install pdf2docx")

    return "\n".join(lines)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用工具"""
    return [
        Tool(
            name="word_to_pdf",
            description="將 Word 文件（.docx）轉換為 PDF。檔案大小限制 10MB。",
            inputSchema={
                "type": "object",
                "properties": {
                    "word_data": {
                        "type": "string",
                        "description": "Word 文件的 base64 編碼內容"
                    }
                },
                "required": ["word_data"]
            }
        ),
        Tool(
            name="pdf_to_word",
            description="將 PDF 文件轉換為 Word（.docx）。檔案大小限制 10MB。",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_data": {
                        "type": "string",
                        "description": "PDF 文件的 base64 編碼內容"
                    }
                },
                "required": ["pdf_data"]
            }
        ),
        Tool(
            name="merge_pdfs",
            description="合併多個 PDF 文件。最多 10 個，每個限制 10MB。可選：添加目錄頁、添加頁碼。",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_files": {
                        "type": "array",
                        "description": "PDF 文件的 base64 編碼內容陣列",
                        "items": {"type": "string"}
                    },
                    "add_toc": {
                        "type": "boolean",
                        "description": "是否添加目錄頁面",
                        "default": False
                    },
                    "add_page_numbers": {
                        "type": "boolean",
                        "description": "是否添加頁碼",
                        "default": False
                    }
                },
                "required": ["pdf_files"]
            }
        ),
        Tool(
            name="merge_images",
            description="拼接多張圖片為網格。最多 9 張圖片，每張限制 5MB。",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_files": {
                        "type": "array",
                        "description": "圖片文件的 base64 編碼內容陣列",
                        "items": {"type": "string"}
                    },
                    "rows": {
                        "type": "integer",
                        "description": "網格行數",
                        "default": 3
                    },
                    "cols": {
                        "type": "integer",
                        "description": "網格列數",
                        "default": 3
                    },
                    "strategy": {
                        "type": "string",
                        "description": "縮放策略：'直接縮放'、'填滿裁切'、'等比例（含邊）'",
                        "default": "直接縮放"
                    }
                },
                "required": ["image_files"]
            }
        ),
        Tool(
            name="create_gif",
            description="從多張圖片創建 GIF 動畫。最多 20 張圖片。",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_files": {
                        "type": "array",
                        "description": "圖片文件的 base64 編碼內容陣列",
                        "items": {"type": "string"}
                    },
                    "duration": {
                        "type": "integer",
                        "description": "每幀持續時間（毫秒）",
                        "default": 500
                    }
                },
                "required": ["image_files"]
            }
        ),
        Tool(
            name="compress_images",
            description="壓縮圖片。最多 50 張。",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_files": {
                        "type": "array",
                        "description": "圖片文件的 base64 編碼內容陣列",
                        "items": {"type": "string"}
                    },
                    "quality": {
                        "type": "integer",
                        "description": "壓縮品質 (1-100)",
                        "default": 75
                    },
                    "output_format": {
                        "type": "string",
                        "description": "輸出格式：jpg, png, webp",
                        "default": "jpg"
                    }
                },
                "required": ["image_files"]
            }
        ),
        Tool(
            name="check_system",
            description="檢查系統環境和依賴項狀態，診斷轉換功能是否可用。建議在轉換失敗時呼叫此工具。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
    """處理工具呼叫"""

    try:
        if name == "word_to_pdf":
            return await handle_word_to_pdf(arguments)

        elif name == "pdf_to_word":
            return await handle_pdf_to_word(arguments)

        elif name == "merge_pdfs":
            return await handle_merge_pdfs(arguments)

        elif name == "merge_images":
            return await handle_merge_images(arguments)

        elif name == "create_gif":
            return await handle_create_gif(arguments)

        elif name == "check_system":
            return await handle_check_system(arguments)

        elif name == "compress_images":
            return await handle_compress_images(arguments)

        else:
            raise ValueError(f"未知工具: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"錯誤: {str(e)}")]


async def handle_word_to_pdf(arguments: dict) -> list[TextContent | EmbeddedResource]:
    """處理 Word 轉 PDF"""
    word_data = arguments["word_data"]
    word_path = None
    pdf_path = None

    try:
        # 保存 Word 文件
        word_path = save_base64_file(word_data, ".docx")

        # 驗證檔案大小
        validate_file_size(word_path, MAX_PDF_SIZE, "Word")

        # 轉換
        pdf_path = word_path.replace(".docx", ".pdf")
        success = convert_word_to_pdf(word_path, pdf_path)

        if not success:
            # 轉換失敗，提供診斷資訊
            error_msg = format_error_message(
                "Word 轉 PDF",
                Exception("轉換函數返回 False，可能是依賴項缺失或系統配置問題"),
                include_diagnostic=True
            )
            return [TextContent(type="text", text=error_msg)]

        # 檢查 PDF 是否生成成功
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            error_msg = format_error_message(
                "Word 轉 PDF",
                Exception(f"PDF 文件未生成或大小為 0"),
                include_diagnostic=True
            )
            return [TextContent(type="text", text=error_msg)]

        # 讀取 PDF 並轉換為 base64
        pdf_base64 = file_to_base64(pdf_path)

        # 清理臨時檔案
        os.unlink(word_path)
        os.unlink(pdf_path)

        return [
            TextContent(type="text", text="✅ Word 轉 PDF 成功！"),
            EmbeddedResource(
                type="resource",
                resource={
                    "uri": f"data:application/pdf;base64,{pdf_base64}",
                    "mimeType": "application/pdf",
                    "text": "轉換後的 PDF 文件"
                }
            )
        ]

    except Exception as e:
        # 清理臨時檔案
        if word_path and os.path.exists(word_path):
            os.unlink(word_path)
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)

        error_msg = format_error_message("Word 轉 PDF", e, include_diagnostic=True)
        return [TextContent(type="text", text=error_msg)]


async def handle_pdf_to_word(arguments: dict) -> list[TextContent | EmbeddedResource]:
    """處理 PDF 轉 Word"""
    pdf_data = arguments["pdf_data"]
    pdf_path = None
    word_path = None

    try:
        # 保存 PDF 文件
        pdf_path = save_base64_file(pdf_data, ".pdf")

        # 驗證檔案大小
        validate_file_size(pdf_path, MAX_PDF_SIZE, "PDF")

        # 轉換
        word_path = pdf_path.replace(".pdf", ".docx")
        success = convert_pdf_to_word(pdf_path, word_path)

        if not success:
            # 轉換失敗，提供診斷資訊
            error_msg = format_error_message(
                "PDF 轉 Word",
                Exception("轉換函數返回 False，可能是依賴項缺失或 PDF 格式問題"),
                include_diagnostic=True
            )
            return [TextContent(type="text", text=error_msg)]

        # 檢查 Word 是否生成成功
        if not os.path.exists(word_path) or os.path.getsize(word_path) == 0:
            error_msg = format_error_message(
                "PDF 轉 Word",
                Exception(f"Word 文件未生成或大小為 0"),
                include_diagnostic=True
            )
            return [TextContent(type="text", text=error_msg)]

        # 讀取 Word 並轉換為 base64
        word_base64 = file_to_base64(word_path)

        # 清理臨時檔案
        os.unlink(pdf_path)
        os.unlink(word_path)

        return [
            TextContent(type="text", text="✅ PDF 轉 Word 成功！"),
            EmbeddedResource(
                type="resource",
                resource={
                    "uri": f"data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{word_base64}",
                    "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "text": "轉換後的 Word 文件"
                }
            )
        ]

    except Exception as e:
        # 清理臨時檔案
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)
        if word_path and os.path.exists(word_path):
            os.unlink(word_path)

        error_msg = format_error_message("PDF 轉 Word", e, include_diagnostic=True)
        return [TextContent(type="text", text=error_msg)]


async def handle_merge_pdfs(arguments: dict) -> list[TextContent | EmbeddedResource]:
    """處理 PDF 合併"""
    pdf_files_data = arguments["pdf_files"]
    add_toc = arguments.get("add_toc", False)
    add_page_numbers = arguments.get("add_page_numbers", False)

    if len(pdf_files_data) > MAX_PDFS_COUNT:
        return [TextContent(
            type="text",
            text=f"PDF 檔案過多：{len(pdf_files_data)} 個（限制：{MAX_PDFS_COUNT} 個）"
        )]

    # 保存所有 PDF
    pdf_paths = []
    try:
        for i, pdf_data in enumerate(pdf_files_data):
            pdf_path = save_base64_file(pdf_data, f"_{i}.pdf")
            validate_file_size(pdf_path, MAX_PDF_SIZE, f"PDF #{i+1}")
            pdf_paths.append(pdf_path)

        # 合併
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
        success = merge_pdfs(pdf_paths, output_path, add_toc, add_page_numbers)

        if not success:
            return [TextContent(type="text", text="PDF 合併失敗")]

        # 讀取合併後的 PDF
        merged_base64 = file_to_base64(output_path)

        # 清理臨時檔案
        for path in pdf_paths:
            os.unlink(path)
        os.unlink(output_path)

        return [
            TextContent(
                type="text",
                text=f"成功合併 {len(pdf_files_data)} 個 PDF！"
            ),
            EmbeddedResource(
                type="resource",
                resource={
                    "uri": f"data:application/pdf;base64,{merged_base64}",
                    "mimeType": "application/pdf",
                    "text": "合併後的 PDF 文件"
                }
            )
        ]

    except Exception as e:
        # 清理臨時檔案
        for path in pdf_paths:
            if os.path.exists(path):
                os.unlink(path)
        raise e


async def handle_merge_images(arguments: dict) -> list[TextContent | ImageContent]:
    """處理圖片拼接"""
    image_files_data = arguments["image_files"]
    rows = arguments.get("rows", 3)
    cols = arguments.get("cols", 3)
    strategy = arguments.get("strategy", "直接縮放")

    if len(image_files_data) > 9:
        return [TextContent(type="text", text=f"圖片過多：{len(image_files_data)} 張（限制：9 張）")]

    # 保存所有圖片
    image_paths = []
    try:
        for i, img_data in enumerate(image_files_data):
            img_path = save_base64_file(img_data, f"_{i}.png")
            validate_file_size(img_path, MAX_IMAGE_SIZE, f"圖片 #{i+1}")
            image_paths.append(img_path)

        # 拼接圖片
        images = [Image.open(p) for p in image_paths]
        min_w = min(img.width for img in images)
        min_h = min(img.height for img in images)

        gap = 10
        merged_w = cols * min_w + (cols + 1) * gap
        merged_h = rows * min_h + (rows + 1) * gap
        merged = Image.new("RGB", (merged_w, merged_h), (255, 255, 255))

        idx = 0
        for row in range(rows):
            for col in range(cols):
                if idx >= len(images):
                    break
                resized = resize_image(images[idx], (min_w, min_h), strategy)
                x = gap + col * (min_w + gap)
                y = gap + row * (min_h + gap)
                merged.paste(resized, (x, y))
                idx += 1

        # 保存拼接結果
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
        merged.save(output_path)

        # 讀取並轉換為 base64
        merged_base64 = file_to_base64(output_path)

        # 清理臨時檔案
        for path in image_paths:
            os.unlink(path)
        os.unlink(output_path)

        return [
            TextContent(type="text", text=f"成功拼接 {len(image_files_data)} 張圖片！"),
            ImageContent(
                type="image",
                data=merged_base64,
                mimeType="image/png"
            )
        ]

    except Exception as e:
        # 清理臨時檔案
        for path in image_paths:
            if os.path.exists(path):
                os.unlink(path)
        raise e


async def handle_create_gif(arguments: dict) -> list[TextContent | ImageContent]:
    """處理 GIF 創建"""
    image_files_data = arguments["image_files"]
    duration = arguments.get("duration", 500)

    if len(image_files_data) > MAX_IMAGES_COUNT:
        return [TextContent(
            type="text",
            text=f"圖片過多：{len(image_files_data)} 張（限制：{MAX_IMAGES_COUNT} 張）"
        )]

    # 保存所有圖片
    image_paths = []
    try:
        for i, img_data in enumerate(image_files_data):
            img_path = save_base64_file(img_data, f"_{i}.png")
            validate_file_size(img_path, MAX_IMAGE_SIZE, f"圖片 #{i+1}")
            image_paths.append(img_path)

        # 載入圖片
        images = [Image.open(p) for p in image_paths]

        # 統一大小
        min_w = min(img.width for img in images)
        min_h = min(img.height for img in images)
        frames = [resize_image(img, (min_w, min_h), "直接縮放") for img in images]

        # 保存 GIF
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".gif").name
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            optimize=True
        )

        # 讀取並轉換為 base64
        gif_base64 = file_to_base64(output_path)

        # 清理臨時檔案
        for path in image_paths:
            os.unlink(path)
        os.unlink(output_path)

        return [
            TextContent(type="text", text=f"成功創建 GIF！共 {len(image_files_data)} 幀"),
            ImageContent(
                type="image",
                data=gif_base64,
                mimeType="image/gif"
            )
        ]

    except Exception as e:
        # 清理臨時檔案
        for path in image_paths:
            if os.path.exists(path):
                os.unlink(path)
        raise e


async def handle_compress_images(arguments: dict) -> list[TextContent]:
    """處理圖片壓縮"""
    image_files_data = arguments["image_files"]
    quality = arguments.get("quality", 75)
    output_format = arguments.get("output_format", "jpg")

    if len(image_files_data) > 50:
        return [TextContent(
            type="text",
            text=f"圖片過多：{len(image_files_data)} 張（限制：50 張）"
        )]

    # 保存所有圖片
    image_paths = []
    compressed_data = []

    try:
        total_original = 0
        total_compressed = 0

        for i, img_data in enumerate(image_files_data):
            img_path = save_base64_file(img_data, f"_{i}.png")
            validate_file_size(img_path, MAX_IMAGE_SIZE, f"圖片 #{i+1}")
            image_paths.append(img_path)

            # 壓縮
            img = Image.open(img_path)
            orig_size = os.path.getsize(img_path)
            total_original += orig_size

            # 處理透明背景
            if output_format.lower() in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # 保存壓縮版本
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}").name

            if output_format.lower() in ['jpg', 'jpeg']:
                img.save(output_path, format='JPEG', quality=quality, optimize=True)
            elif output_format.lower() == 'png':
                img.save(output_path, format='PNG', optimize=True, compress_level=9)
            elif output_format.lower() == 'webp':
                img.save(output_path, format='WEBP', quality=quality)

            comp_size = os.path.getsize(output_path)
            total_compressed += comp_size

            # 轉換為 base64
            compressed_base64 = file_to_base64(output_path)
            compressed_data.append(compressed_base64)

            os.unlink(output_path)

        # 清理臨時檔案
        for path in image_paths:
            os.unlink(path)

        # 計算節省
        saved = total_original - total_compressed
        saved_percent = (saved / total_original * 100) if total_original > 0 else 0

        result_text = (
            f"成功壓縮 {len(image_files_data)} 張圖片！\n"
            f"原始大小：{total_original/(1024*1024):.2f} MB\n"
            f"壓縮後：{total_compressed/(1024*1024):.2f} MB\n"
            f"節省：{saved/(1024*1024):.2f} MB ({saved_percent:.1f}%)\n"
            f"注意：壓縮後的圖片以 base64 格式回傳，可保存使用。"
        )

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        # 清理臨時檔案
        for path in image_paths:
            if os.path.exists(path):
                os.unlink(path)
        raise e


async def handle_check_system(arguments: dict) -> list[TextContent]:
    """處理系統檢查"""
    try:
        diagnostic_info = get_diagnostic_info()

        # 添加額外的使用建議
        deps = check_dependencies()
        suggestions = []

        if not deps.get('docx2pdf'):
            suggestions.append("⚠️ Word 轉 PDF 功能可能受限")
            suggestions.append("   建議：")
            suggestions.append("   1. pip install docx2pdf")
            suggestions.append("   2. 或確保 LibreOffice 已安裝")

        if not deps.get('pdf2docx'):
            suggestions.append("⚠️ PDF 轉 Word 功能可能受限")
            suggestions.append("   建議：pip install pdf2docx")

        if not deps.get('reportlab'):
            suggestions.append("⚠️ PDF 目錄和頁碼功能將無法使用")
            suggestions.append("   建議：pip install reportlab")

        if not deps.get('pypdf'):
            suggestions.append("⚠️ PDF 處理功能將無法使用")
            suggestions.append("   建議：pip install pypdf")

        # 組合完整訊息
        full_message = diagnostic_info
        if suggestions:
            full_message += "\n\n" + "="*50
            full_message += "\n⚠️  問題和建議\n"
            full_message += "="*50 + "\n"
            full_message += "\n".join(suggestions)
        else:
            full_message += "\n\n✅ 所有依賴項已正確安裝，系統運行正常！"

        return [TextContent(type="text", text=full_message)]

    except Exception as e:
        return [TextContent(type="text", text=f"系統檢查失敗: {str(e)}\n{traceback.format_exc()}")]


async def main():
    """啟動 MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
