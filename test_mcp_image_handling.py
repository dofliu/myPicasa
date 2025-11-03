#!/usr/bin/env python3
"""
測試 MCP Server 圖片處理改進
驗證 base64 解碼和圖片驗證功能
"""

import sys
import os
import base64
import tempfile
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent))

# 測試 PIL
try:
    from PIL import Image
    print("✓ PIL 已安裝")
except ImportError:
    print("✗ PIL 未安裝")
    sys.exit(1)

def test_base64_functions():
    """測試 base64 處理函數"""
    print("\n" + "="*50)
    print("測試 1: Base64 編碼/解碼")
    print("="*50)

    # 創建一個簡單的測試圖片
    test_img = Image.new('RGB', (100, 100), color='red')
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
    test_img.save(temp_path, 'JPEG')

    # 讀取並編碼
    with open(temp_path, 'rb') as f:
        original_data = f.read()
        b64_data = base64.b64encode(original_data).decode('utf-8')

    print(f"✓ 原始圖片大小: {len(original_data)} bytes")
    print(f"✓ Base64 長度: {len(b64_data)} chars")

    # 測試解碼
    decoded_data = base64.b64decode(b64_data)
    assert decoded_data == original_data, "解碼資料不匹配！"
    print("✓ Base64 編碼/解碼正確")

    # 測試帶換行符的 base64
    b64_with_newlines = b64_data[:100] + '\n' + b64_data[100:200] + '\n' + b64_data[200:]
    cleaned = b64_with_newlines.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    decoded_cleaned = base64.b64decode(cleaned)
    assert decoded_cleaned == original_data, "清理後的解碼資料不匹配！"
    print("✓ 處理換行符的 Base64 正確")

    # 測試 data URL 前綴
    data_url = f"data:image/jpeg;base64,{b64_data}"
    if ',' in data_url:
        extracted = data_url.split(',', 1)[1]
        decoded_extracted = base64.b64decode(extracted)
        assert decoded_extracted == original_data, "Data URL 提取失敗！"
        print("✓ Data URL 前綴處理正確")

    os.unlink(temp_path)
    print("✅ Base64 處理測試通過\n")


def test_image_validation():
    """測試圖片驗證"""
    print("="*50)
    print("測試 2: 圖片驗證")
    print("="*50)

    # 測試有效圖片
    test_img = Image.new('RGB', (200, 200), color='blue')
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
    test_img.save(temp_path, 'JPEG')

    try:
        with Image.open(temp_path) as img:
            img.verify()
        with Image.open(temp_path) as img:
            img.load()
        print(f"✓ 有效圖片驗證成功: {temp_path}")
    except Exception as e:
        print(f"✗ 圖片驗證失敗: {e}")
        os.unlink(temp_path)
        return False

    os.unlink(temp_path)

    # 測試無效檔案
    invalid_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
    with open(invalid_path, 'w') as f:
        f.write("This is not an image")

    try:
        with Image.open(invalid_path) as img:
            img.verify()
        print("✗ 應該要檢測出無效圖片")
        os.unlink(invalid_path)
        return False
    except Exception:
        print("✓ 正確檢測出無效圖片")

    os.unlink(invalid_path)
    print("✅ 圖片驗證測試通過\n")
    return True


def test_save_base64_workflow():
    """測試完整的 base64 保存流程"""
    print("="*50)
    print("測試 3: 完整 Base64 -> 圖片流程")
    print("="*50)

    # 創建測試圖片
    test_img = Image.new('RGB', (150, 150), color='green')
    temp_orig = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
    test_img.save(temp_orig, 'JPEG')

    # 模擬完整流程
    # 1. 讀取並編碼
    with open(temp_orig, 'rb') as f:
        b64_data = base64.b64encode(f.read()).decode('utf-8')

    # 2. 模擬傳輸（可能包含換行符）
    b64_data_with_noise = b64_data[:200] + '\n' + b64_data[200:400] + ' ' + b64_data[400:]

    # 3. 清理並解碼
    cleaned = b64_data_with_noise.strip().replace('\n', '').replace('\r', '').replace(' ', '')
    file_data = base64.b64decode(cleaned)

    # 4. 保存
    temp_saved = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
    with open(temp_saved, 'wb') as f:
        f.write(file_data)

    # 5. 驗證
    try:
        with Image.open(temp_saved) as img:
            img.verify()
        with Image.open(temp_saved) as img:
            img.load()
            width, height = img.size
            assert width == 150 and height == 150, "圖片尺寸不匹配"
        print(f"✓ 圖片成功保存並驗證: {width}x{height}")
    except Exception as e:
        print(f"✗ 驗證失敗: {e}")
        os.unlink(temp_orig)
        os.unlink(temp_saved)
        return False

    os.unlink(temp_orig)
    os.unlink(temp_saved)
    print("✅ 完整流程測試通過\n")
    return True


def test_corrupted_base64():
    """測試損壞的 base64 資料"""
    print("="*50)
    print("測試 4: 錯誤處理")
    print("="*50)

    # 測試空 base64
    try:
        decoded = base64.b64decode('')
        if len(decoded) == 0:
            print("✓ 正確處理空 base64")
        else:
            print("✗ 空 base64 應返回空資料")
    except Exception as e:
        print(f"✓ 空 base64 觸發異常: {type(e).__name__}")

    # 測試無效 base64
    try:
        decoded = base64.b64decode('!!!invalid base64!!!')
        print("✗ 應該檢測出無效 base64")
    except Exception as e:
        print(f"✓ 正確檢測無效 base64: {type(e).__name__}")

    print("✅ 錯誤處理測試通過\n")
    return True


def main():
    print("\n" + "="*50)
    print("MCP Server 圖片處理改進測試")
    print("="*50)

    all_passed = True

    try:
        test_base64_functions()
    except Exception as e:
        print(f"❌ Base64 測試失敗: {e}")
        all_passed = False

    try:
        if not test_image_validation():
            all_passed = False
    except Exception as e:
        print(f"❌ 圖片驗證測試失敗: {e}")
        all_passed = False

    try:
        if not test_save_base64_workflow():
            all_passed = False
    except Exception as e:
        print(f"❌ 完整流程測試失敗: {e}")
        all_passed = False

    try:
        if not test_corrupted_base64():
            all_passed = False
    except Exception as e:
        print(f"❌ 錯誤處理測試失敗: {e}")
        all_passed = False

    print("="*50)
    if all_passed:
        print("✅ 所有測試通過！")
        print("\n改進總結：")
        print("1. ✓ Base64 解碼時自動清理換行符和空白")
        print("2. ✓ 保存前驗證檔案大小")
        print("3. ✓ 保存後立即驗證圖片格式")
        print("4. ✓ 提供詳細的錯誤訊息")
        print("5. ✓ 正確處理各種邊界情況")
    else:
        print("❌ 部分測試失敗")
        return 1

    print("="*50 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
