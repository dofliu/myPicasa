"""
配置管理模組
自動保存和載入用戶偏好設定

Copyright © 2025 Dof Liu AI工作室
"""
import json
import os
from pathlib import Path


class ConfigManager:
    """配置管理器 - 處理用戶設定的保存和載入"""

    def __init__(self, app_name="MediaToolkit"):
        """初始化配置管理器"""
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.default_config = self._get_default_config()
        self.config = self.load_config()

    def _get_config_dir(self):
        """取得配置目錄路徑"""
        # 使用用戶家目錄下的隱藏資料夾
        home = Path.home()
        config_dir = os.path.join(home, f".{self.app_name.lower()}")

        # 確保目錄存在
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        return config_dir

    def _get_default_config(self):
        """取得預設配置"""
        return {
            # 主題設定
            "theme": "light",

            # 視窗設定
            "window": {
                "width": 1200,
                "height": 800,
                "x": None,  # None 表示置中
                "y": None,
                "maximized": False
            },

            # 圖片處理參數
            "image": {
                "grid_cols": 3,
                "grid_rows": 3,
                "resize_strategy": "直接縮放",
                "gif_duration": 500,
                "last_folder": ""
            },

            # 影片處理參數
            "video": {
                "output_name": "merged_video.mp4",
                "last_folder": ""
            },

            # 格式轉換參數
            "convert": {
                "output_format": "PNG",
                "output_folder": "converted_images",
                "last_folder": ""
            },

            # 文檔處理參數
            "document": {
                "last_word_folder": "",
                "last_pdf_folder": ""
            },

            # 最近使用記錄
            "recent": {
                "files": [],
                "max_items": 10
            }
        }

    def load_config(self):
        """載入配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)

                # 合併預設配置（處理新增的配置項）
                config = self._merge_config(self.default_config, loaded_config)
                print(f"✓ 已載入配置: {self.config_file}")
                return config
            except Exception as e:
                print(f"✗ 載入配置失敗: {e}")
                return self.default_config.copy()
        else:
            print("✓ 使用預設配置")
            return self.default_config.copy()

    def _merge_config(self, default, loaded):
        """合併配置（保留舊設定，添加新設定）"""
        merged = default.copy()

        for key, value in loaded.items():
            if key in merged:
                if isinstance(value, dict) and isinstance(merged[key], dict):
                    # 遞迴合併字典
                    merged[key] = self._merge_config(merged[key], value)
                else:
                    merged[key] = value

        return merged

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✓ 配置已保存: {self.config_file}")
            return True
        except Exception as e:
            print(f"✗ 保存配置失敗: {e}")
            return False

    # === 便捷方法 ===

    def get(self, key, default=None):
        """取得配置值（支援點號路徑，如 'window.width'）"""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key, value, auto_save=True):
        """設定配置值（支援點號路徑）"""
        keys = key.split('.')
        config = self.config

        # 遍歷到最後一個 key 之前
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # 設定值
        config[keys[-1]] = value

        # 自動保存
        if auto_save:
            self.save_config()

    def add_recent_file(self, file_path, file_type="image"):
        """添加最近使用的文件"""
        recent = self.config["recent"]["files"]
        max_items = self.config["recent"]["max_items"]

        # 移除重複項
        recent = [item for item in recent if item["path"] != file_path]

        # 添加到開頭
        recent.insert(0, {
            "path": file_path,
            "type": file_type,
            "name": os.path.basename(file_path)
        })

        # 限制數量
        self.config["recent"]["files"] = recent[:max_items]
        self.save_config()

    def get_recent_files(self, file_type=None):
        """取得最近使用的文件"""
        recent = self.config["recent"]["files"]

        if file_type:
            return [item for item in recent if item["type"] == file_type]

        return recent

    def clear_recent(self):
        """清空最近使用記錄"""
        self.config["recent"]["files"] = []
        self.save_config()

    def reset_to_default(self):
        """重置為預設配置"""
        self.config = self._get_default_config()
        self.save_config()
        print("✓ 配置已重置為預設值")


# 全域配置實例（單例模式）
_config_instance = None

def get_config_manager():
    """取得配置管理器實例（單例）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance
