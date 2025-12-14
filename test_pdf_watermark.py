#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF 浮水印功能測試腳本
測試文字和圖片浮水印功能
"""
import os
import sys
from utils.doc_converter import (
    add_text_watermark_to_pdf,
    add_image_watermark_to_pdf,
    check_dependencies
)

def test_text_watermark():
    """測試文字浮水印"""
    print("\n=== 測試文字浮水印 ===")

    # 這裡需要一個測試用的 PDF 文件
    # 請替換為實際的 PDF 文件路徑
    input_pdf = "test_input.pdf"
    output_pdf = "test_text_watermark.pdf"

    if not os.path.exists(input_pdf):
        print(f"[FAIL] 測試 PDF 文件不存在: {input_pdf}")
        print("請創建一個測試 PDF 文件或修改路徑")
        return False

    print(f"輸入文件: {input_pdf}")
    print(f"輸出文件: {output_pdf}")
    print("浮水印文字: © 2025 機密文件")
    print("位置: center")
    print("透明度: 0.3")
    print("字體大小: 40")
    print("旋轉角度: 45°")

    success = add_text_watermark_to_pdf(
        input_pdf,
        output_pdf,
        "© 2025 機密文件",
        position='center',
        opacity=0.3,
        font_size=40,
        rotation=45
    )

    if success:
        print(f"[OK] 文字浮水印添加成功: {output_pdf}")
        return True
    else:
        print("[FAIL] 文字浮水印添加失敗")
        return False


def test_image_watermark():
    """測試圖片浮水印"""
    print("\n=== 測試圖片浮水印 ===")

    # 這裡需要一個測試用的 PDF 文件和浮水印圖片
    input_pdf = "test_input.pdf"
    watermark_image = "watermark.png"
    output_pdf = "test_image_watermark.pdf"

    if not os.path.exists(input_pdf):
        print(f"[FAIL] 測試 PDF 文件不存在: {input_pdf}")
        return False

    if not os.path.exists(watermark_image):
        print(f"[FAIL] 浮水印圖片不存在: {watermark_image}")
        print("請準備一個 PNG 格式的浮水印圖片")
        return False

    print(f"輸入文件: {input_pdf}")
    print(f"浮水印圖片: {watermark_image}")
    print(f"輸出文件: {output_pdf}")
    print("位置: bottom-right")
    print("透明度: 0.5")
    print("縮放比例: 0.2")

    success = add_image_watermark_to_pdf(
        input_pdf,
        output_pdf,
        watermark_image,
        position='bottom-right',
        opacity=0.5,
        scale=0.2
    )

    if success:
        print(f"[OK] 圖片浮水印添加成功: {output_pdf}")
        return True
    else:
        print("[FAIL] 圖片浮水印添加失敗")
        return False


def main():
    """主測試函數"""
    print("=" * 60)
    print("PDF 浮水印功能測試")
    print("=" * 60)

    # 檢查依賴
    print("\n檢查依賴套件...")
    deps = check_dependencies()
    print(f"pypdf: {'OK' if deps['pypdf'] else 'MISSING'}")
    print(f"reportlab: {'OK' if deps['reportlab'] else 'MISSING'}")

    if not deps['pypdf'] or not deps['reportlab']:
        print("\n[FAIL] 缺少必要的套件，請安裝:")
        print("pip install pypdf reportlab")
        return

    # 執行測試
    results = []

    # 測試文字浮水印
    results.append(("文字浮水印", test_text_watermark()))

    # 測試圖片浮水印
    results.append(("圖片浮水印", test_image_watermark()))

    # 顯示測試結果
    print("\n" + "=" * 60)
    print("測試結果總結")
    print("=" * 60)
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{name}: {status}")

    print("\n注意:")
    print("1. 請確保有 test_input.pdf 文件進行測試")
    print("2. 測試圖片浮水印需要 watermark.png 文件")
    print("3. 成功後會生成 test_text_watermark.pdf 和 test_image_watermark.pdf")


if __name__ == '__main__':
    main()
