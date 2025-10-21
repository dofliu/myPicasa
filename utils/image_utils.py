"""
圖片處理工具函數
"""
from PIL import Image


def get_resample_filter():
    """
    根據 Pillow 版本選擇適用的縮放參數

    Returns:
        適用的縮放濾鏡
    """
    try:
        return Image.Resampling.LANCZOS
    except AttributeError:
        return Image.ANTIALIAS


# 取得全域的重採樣濾鏡
resample_filter = get_resample_filter()


def resize_with_padding(img, target_size, bg_color=(255, 255, 255)):
    """
    以保持原始比例縮放圖片，並將縮放後的圖片置中補足目標尺寸

    Args:
        img: PIL Image 物件
        target_size: 目標尺寸 (width, height)
        bg_color: 背景顏色，預設為白色 (255, 255, 255)

    Returns:
        PIL Image 物件，已調整至目標尺寸並保持原始比例
    """
    target_width, target_height = target_size
    ratio = min(target_width / img.width, target_height / img.height)
    new_width = int(img.width * ratio)
    new_height = int(img.height * ratio)

    # 縮放圖片
    resized_img = img.resize((new_width, new_height), resample=resample_filter)

    # 建立新圖片並貼上縮放後的圖片（置中）
    new_img = Image.new("RGB", (target_width, target_height), bg_color)
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    new_img.paste(resized_img, (paste_x, paste_y))

    return new_img


def resize_image(img, target_size, strategy):
    """
    根據縮放策略調整圖片大小

    Args:
        img: PIL Image 物件
        target_size: 目標尺寸 (width, height)
        strategy: 縮放策略
                 - "保持比例補白": 保持原比例縮放並補白
                 - "直接縮放": 直接縮放至目標尺寸（可能變形）

    Returns:
        PIL Image 物件，已調整至目標尺寸
    """
    if strategy == "保持比例補白":
        return resize_with_padding(img, target_size)
    else:
        return img.resize(target_size, resample=resample_filter)


def validate_image_file(file_path):
    """
    驗證圖片檔案是否有效

    Args:
        file_path: 圖片檔案路徑

    Returns:
        (bool, str): (是否有效, 錯誤訊息)
    """
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True, ""
    except Exception as e:
        return False, str(e)


def get_image_info(file_path):
    """
    取得圖片資訊

    Args:
        file_path: 圖片檔案路徑

    Returns:
        dict: 包含圖片資訊的字典
    """
    try:
        with Image.open(file_path) as img:
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode,
                'size': img.size
            }
    except Exception as e:
        return {'error': str(e)}
