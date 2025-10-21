"""
應用程式配置管理
"""


class Config:
    """應用程式配置類別"""

    # 應用程式資訊
    APP_NAME = "Dof的圖片整理工具_2025版"
    APP_VERSION = "2025.1.0"
    APP_AUTHOR = "Dof Liu"

    # 預設參數
    DEFAULT_GRID_COLS = 2
    DEFAULT_GRID_ROWS = 2
    DEFAULT_IMAGE_GAP = 15
    DEFAULT_GIF_DURATION = 500  # 毫秒
    DEFAULT_BG_COLOR = (255, 255, 255)  # 白色

    # 縮放策略
    RESIZE_STRATEGY_DIRECT = "直接縮放"
    RESIZE_STRATEGY_PADDING = "保持比例補白"
    RESIZE_STRATEGIES = [RESIZE_STRATEGY_DIRECT, RESIZE_STRATEGY_PADDING]

    # 支援的圖片格式
    SUPPORTED_IMAGE_FORMATS = ['JPG', 'PNG', 'WEBP', 'BMP', 'GIF']
    IMAGE_FILE_FILTER = "Image Files (*.jpg *.jpeg *.png *.bmp *.gif *.webp)"

    # 支援的影片格式
    SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
    VIDEO_FILE_FILTER = "Video Files (*.mp4 *.avi *.mov *.mkv *.webm *.flv)"

    # 影片編碼設定
    VIDEO_CODEC = "libx264"
    AUDIO_CODEC = "aac"

    # UI 文字
    UI_TEXT = {
        'select_images': '選擇圖片檔案',
        'select_videos': '選擇影片檔案',
        'select_convert_images': '選擇要轉換的圖片檔案',
        'merge_images': '拼接圖片',
        'merge_videos': '合併影片',
        'create_gif': '生成 GIF 動畫',
        'convert_images': '開始轉換',
        'browse': '瀏覽',
        'warning': '警告',
        'error': '錯誤',
        'completed': '完成',
        'progress': '進度',
    }

    # 訊息文字
    MESSAGES = {
        'no_images_selected': '請先選擇圖片檔案',
        'no_videos_selected': '請先選擇影片檔案',
        'invalid_number_format': '請輸入正確的數字格式',
        'invalid_duration': '請輸入正確的動畫持續時間（毫秒）',
        'image_read_failed': '圖片讀取失敗：{}',
        'save_failed': '儲存失敗：{}',
        'video_read_error': '讀取影片時發生錯誤：{}',
        'video_merge_error': '合併影片或寫入檔案時發生錯誤：{}',
        'video_merge_start': '開始合併影片，這可能需要一些時間...',
        'no_output_filename': '請輸入輸出影片檔名',
        'no_videos_loaded': '沒有任何影片可以成功載入並合併。',
        'merge_success': '拼接圖片已儲存至\n{}',
        'gif_success': 'GIF 動畫已儲存至\n{}',
        'video_merge_success': '影片成功合併並儲存至\n{}',
        'convert_success': '成功轉換 {} 個檔案到 {}',
        'convert_failed': '沒有檔案成功轉換',
        'file_convert_failed': '檔案 {} 轉換失敗：{}',
    }

    @classmethod
    def get_window_title(cls):
        """取得視窗標題"""
        return f"{cls.APP_NAME} v{cls.APP_VERSION}"

    @classmethod
    def get_save_image_filter(cls):
        """取得儲存圖片的檔案過濾器"""
        return "JPEG (*.jpg);;PNG (*.png)"

    @classmethod
    def get_save_gif_filter(cls):
        """取得儲存 GIF 的檔案過濾器"""
        return "GIF (*.gif)"
