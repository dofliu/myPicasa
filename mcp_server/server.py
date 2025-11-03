#!/usr/bin/env python3
"""
MediaToolkit MCP Server
提供文檔和圖片處理工具
"""

import os
import sys
import tempfile
import base64
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

        elif name == "compress_images":
            return await handle_compress_images(arguments)

        else:
            raise ValueError(f"未知工具: {name}")

    except Exception as e:
        return [TextContent(type="text", text=f"錯誤: {str(e)}")]


async def handle_word_to_pdf(arguments: dict) -> list[TextContent | EmbeddedResource]:
    """處理 Word 轉 PDF"""
    word_data = arguments["word_data"]

    # 保存 Word 文件
    word_path = save_base64_file(word_data, ".docx")

    try:
        # 驗證檔案大小
        validate_file_size(word_path, MAX_PDF_SIZE, "Word")

        # 轉換
        pdf_path = word_path.replace(".docx", ".pdf")
        success = convert_word_to_pdf(word_path, pdf_path)

        if not success:
            return [TextContent(type="text", text="Word 轉 PDF 失敗")]

        # 讀取 PDF 並轉換為 base64
        pdf_base64 = file_to_base64(pdf_path)

        # 清理臨時檔案
        os.unlink(word_path)
        os.unlink(pdf_path)

        return [
            TextContent(type="text", text="Word 轉 PDF 成功！"),
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
        if os.path.exists(word_path):
            os.unlink(word_path)
        raise e


async def handle_pdf_to_word(arguments: dict) -> list[TextContent | EmbeddedResource]:
    """處理 PDF 轉 Word"""
    pdf_data = arguments["pdf_data"]

    # 保存 PDF 文件
    pdf_path = save_base64_file(pdf_data, ".pdf")

    try:
        # 驗證檔案大小
        validate_file_size(pdf_path, MAX_PDF_SIZE, "PDF")

        # 轉換
        word_path = pdf_path.replace(".pdf", ".docx")
        success = convert_pdf_to_word(pdf_path, word_path)

        if not success:
            return [TextContent(type="text", text="PDF 轉 Word 失敗")]

        # 讀取 Word 並轉換為 base64
        word_base64 = file_to_base64(word_path)

        # 清理臨時檔案
        os.unlink(pdf_path)
        os.unlink(word_path)

        return [
            TextContent(type="text", text="PDF 轉 Word 成功！"),
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
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        raise e


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
