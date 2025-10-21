"""
測試圖片處理工具函數
"""
import unittest
import sys
import os
from PIL import Image

# 將父目錄加入路徑以便導入模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from picasa2 import resize_with_padding, resize_image


class TestImageUtils(unittest.TestCase):
    """測試圖片處理工具函數"""

    def setUp(self):
        """建立測試用的圖片"""
        # 建立一個 100x100 的測試圖片
        self.test_image = Image.new('RGB', (100, 100), color=(255, 0, 0))
        # 建立一個 200x100 的測試圖片（長方形）
        self.test_image_rect = Image.new('RGB', (200, 100), color=(0, 255, 0))

    def test_resize_with_padding_square(self):
        """測試正方形圖片的補白縮放"""
        target_size = (150, 150)
        result = resize_with_padding(self.test_image, target_size)

        # 檢查輸出尺寸是否正確
        self.assertEqual(result.size, target_size)

        # 檢查模式是否為 RGB
        self.assertEqual(result.mode, 'RGB')

    def test_resize_with_padding_rectangle(self):
        """測試長方形圖片的補白縮放"""
        target_size = (150, 150)
        result = resize_with_padding(self.test_image_rect, target_size)

        # 檢查輸出尺寸是否正確
        self.assertEqual(result.size, target_size)

        # 檢查模式是否為 RGB
        self.assertEqual(result.mode, 'RGB')

    def test_resize_with_padding_custom_bg_color(self):
        """測試自訂背景色的補白縮放"""
        target_size = (150, 150)
        bg_color = (0, 0, 255)  # 藍色
        result = resize_with_padding(self.test_image, target_size, bg_color)

        # 檢查輸出尺寸是否正確
        self.assertEqual(result.size, target_size)

    def test_resize_image_direct(self):
        """測試直接縮放策略"""
        target_size = (150, 150)
        strategy = "直接縮放"
        result = resize_image(self.test_image, target_size, strategy)

        # 檢查輸出尺寸是否正確
        self.assertEqual(result.size, target_size)

    def test_resize_image_with_padding(self):
        """測試保持比例補白策略"""
        target_size = (150, 150)
        strategy = "保持比例補白"
        result = resize_image(self.test_image, target_size, strategy)

        # 檢查輸出尺寸是否正確
        self.assertEqual(result.size, target_size)

    def test_resize_image_upscale(self):
        """測試放大圖片"""
        target_size = (200, 200)
        strategy = "直接縮放"
        result = resize_image(self.test_image, target_size, strategy)

        # 檢查輸出尺寸是否正確
        self.assertEqual(result.size, target_size)

    def test_resize_image_downscale(self):
        """測試縮小圖片"""
        target_size = (50, 50)
        strategy = "直接縮放"
        result = resize_image(self.test_image, target_size, strategy)

        # 檢查輸出尺寸是否正確
        self.assertEqual(result.size, target_size)


if __name__ == '__main__':
    unittest.main()
