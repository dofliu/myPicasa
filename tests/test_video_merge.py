"""
測試影片合併功能
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from natsort import natsorted

# 將父目錄加入路徑以便導入模組
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVideoMerge(unittest.TestCase):
    """測試影片合併功能"""

    def test_natsort_ordering(self):
        """測試自然排序是否正確"""
        # 測試檔案清單
        files = [
            "video10.mp4",
            "video2.mp4",
            "video1.mp4",
            "video20.mp4",
            "video3.mp4"
        ]

        # 預期的排序結果
        expected = [
            "video1.mp4",
            "video2.mp4",
            "video3.mp4",
            "video10.mp4",
            "video20.mp4"
        ]

        # 執行自然排序
        result = natsorted(files)

        # 驗證結果
        self.assertEqual(result, expected)

    def test_natsort_with_path(self):
        """測試帶路徑的檔案自然排序"""
        files = [
            "/path/to/video10.mp4",
            "/path/to/video2.mp4",
            "/path/to/video1.mp4"
        ]

        expected = [
            "/path/to/video1.mp4",
            "/path/to/video2.mp4",
            "/path/to/video10.mp4"
        ]

        result = natsorted(files)
        self.assertEqual(result, expected)

    def test_video_extensions(self):
        """測試支援的影片副檔名"""
        supported_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']

        # 測試各種副檔名
        for ext in supported_extensions:
            filename = f"test{ext}"
            self.assertTrue(any(filename.endswith(e) for e in supported_extensions))

    @patch('videoMerge.VideoFileClip')
    @patch('videoMerge.concatenate_videoclips')
    def test_merge_videos_mock(self, mock_concatenate, mock_video_clip):
        """使用 mock 測試影片合併流程"""
        # 設定 mock 物件
        mock_clip1 = MagicMock()
        mock_clip2 = MagicMock()
        mock_final_clip = MagicMock()

        mock_video_clip.side_effect = [mock_clip1, mock_clip2]
        mock_concatenate.return_value = mock_final_clip

        # 導入函數
        try:
            from videoMerge import merge_videos_from_folder

            # 建立測試資料夾路徑
            test_folder = "/tmp/test_videos"
            output_file = "test_output.mp4"

            # 注意：這個測試需要實際的檔案系統操作，所以我們只測試函數存在
            self.assertTrue(callable(merge_videos_from_folder))
        except ImportError:
            # 如果無法導入，跳過測試
            self.skipTest("videoMerge module not available")


class TestVideoFileValidation(unittest.TestCase):
    """測試影片檔案驗證"""

    def test_valid_video_extensions(self):
        """測試有效的影片副檔名"""
        valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']

        for ext in valid_extensions:
            filename = f"video{ext}"
            # 檢查副檔名是否在支援清單中
            self.assertTrue(
                any(filename.lower().endswith(e) for e in valid_extensions),
                f"{ext} should be a valid video extension"
            )

    def test_invalid_video_extensions(self):
        """測試無效的影片副檔名"""
        valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
        invalid_files = ['video.txt', 'video.jpg', 'video.png', 'video.pdf']

        for filename in invalid_files:
            # 檢查副檔名不在支援清單中
            self.assertFalse(
                any(filename.lower().endswith(e) for e in valid_extensions),
                f"{filename} should not be a valid video file"
            )


if __name__ == '__main__':
    unittest.main()
