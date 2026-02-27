#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MediaToolkit - 多媒體與文檔處理工具套件 v6.0
整合圖片影像處理 + 文件轉換功能

Copyright © 2025 Dof Liu AI工作室
All Rights Reserved.
"""
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QComboBox, QFileDialog,
    QMessageBox, QTabWidget, QProgressBar, QGroupBox, QAction, QInputDialog,
    QGridLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QSlider, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
import time
import tempfile
from PIL import Image
from moviepy.editor import VideoFileClip, concatenate_videoclips
from natsort import natsorted

class DiskScanWorker(QThread):
    progress_signal = pyqtSignal(str)
    item_found_signal = pyqtSignal(dict)  # emits dict with path, size, type
    finished_signal = pyqtSignal(object, int) # emits total bytes, total items

    def __init__(self, drive_root, scan_common, scan_appdata, scan_large):
        super().__init__()
        self.drive_root = drive_root
        self.scan_common = scan_common
        self.scan_appdata = scan_appdata
        self.scan_large = scan_large
        self.min_large_file_mb = 500
        self._is_running = True
        self.total_size = 0
        self.total_count = 0

    def stop(self):
        self._is_running = False

    def run(self):
        # Scan common caches
        if self.scan_common:
            self.progress_signal.emit("正在掃描常見快取清單...")
            candidates = self.get_common_candidates(self.drive_root)
            for candidate in candidates:
                if not self._is_running: break
                path = candidate["path"]
                if os.path.exists(path):
                    self.progress_signal.emit(f"檢查快取: {candidate['label']}")
                    size = self.calculate_folder_size(path)
                    if size > 0:
                        self.item_found_signal.emit({
                            "type": "common",
                            "label": candidate["label"],
                            "path": path,
                            "size": size,
                            "isdir": True
                        })
                        self.total_size += size
                        self.total_count += 1

        # Scan large files in drive
        if self.scan_large and self._is_running:
            self.progress_signal.emit(f"正在全碟掃描超大檔案 (> {self.min_large_file_mb}MB)...")
            self.scan_large_files(self.drive_root)
            
        # Optional: Deep Scan AppData
        if self.scan_appdata and self._is_running:
            home_dir = os.path.expanduser("~")
            appdata_local = os.path.join(home_dir, "AppData", "Local")
            appdata_roaming = os.path.join(home_dir, "AppData", "Roaming")
            self.progress_signal.emit("深入分析 AppData (Local/Roaming)...")
            
            if os.path.exists(appdata_local):
                self.deep_scan_directory(appdata_local, "appdata")
            if os.path.exists(appdata_roaming):
                self.deep_scan_directory(appdata_roaming, "appdata")
                
        self.finished_signal.emit(self.total_size, self.total_count)

    def scan_large_files(self, start_path):
        min_bytes = self.min_large_file_mb * 1024 * 1024
        try:
            for root, dirs, files in os.walk(start_path):
                if not self._is_running: break
                
                # Skip some protected/system dirs that take forever or error out
                if "$Recycle.Bin" in root or "System Volume Information" in root:
                    continue
                    
                self.progress_signal.emit(f"掃描大型檔案: {root}")
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        if not os.path.islink(file_path):
                            size = os.path.getsize(file_path)
                            if size > min_bytes:
                                self.item_found_signal.emit({
                                    "type": "large_file",
                                    "label": file_name,
                                    "path": file_path,
                                    "size": size,
                                    "isdir": False
                                })
                                self.total_size += size
                                self.total_count += 1
                    except OSError:
                        continue
        except OSError:
            pass

    def deep_scan_directory(self, start_path, type_label):
        # We only return top level folders inside the start_path that are > 10MB to avoid clutter
        try:
            for item in os.listdir(start_path):
                if not self._is_running: break
                item_path = os.path.join(start_path, item)
                if os.path.isdir(item_path):
                    self.progress_signal.emit(f"分析資料夾: {item}")
                    size = self.calculate_folder_size(item_path)
                    if size > 10 * 1024 * 1024:  # Only report folders > 10MB
                        self.item_found_signal.emit({
                            "type": type_label,
                            "label": item,
                            "path": item_path,
                            "size": size,
                            "isdir": True
                        })
                        self.total_size += size
                        self.total_count += 1
        except OSError:
            pass

    def calculate_folder_size(self, path):
        total_size = 0
        try:
            if os.path.isfile(path):
                return os.path.getsize(path)

            for root, _, files in os.walk(path):
                if not self._is_running: break
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        if not os.path.islink(file_path):
                            total_size += os.path.getsize(file_path)
                    except OSError:
                        continue
        except OSError:
            return 0
        return total_size

    def get_common_candidates(self, drive_root):
        candidates = []
        if os.name != "nt":
            return [
                {"label": "系統暫存資料夾", "path": "/tmp"},
                {"label": "使用者快取資料夾", "path": os.path.expanduser("~/.cache")},
            ]

        drive = drive_root.rstrip("\\/")
        home_dir = os.path.expanduser("~")
        user_profile = home_dir if home_dir.startswith(drive) else None

        candidates.extend([
            {"label": "Windows 暫存資料夾", "path": f"{drive}\\Windows\\Temp"},
            {"label": "Windows 更新下載快取", "path": f"{drive}\\Windows\\SoftwareDistribution\\Download"},
            {"label": "系統回收桶", "path": f"{drive}\\$Recycle.Bin"},
        ])

        if user_profile:
            candidates.extend([
                {"label": "使用者 Temp", "path": os.path.join(user_profile, "AppData", "Local", "Temp")},
                {"label": "IE/Edge 快取", "path": os.path.join(user_profile, "AppData", "Local", "Microsoft", "Windows", "INetCache")},
                {"label": "縮圖快取", "path": os.path.join(user_profile, "AppData", "Local", "Microsoft", "Windows", "Explorer")},
                {"label": "程式崩潰記錄", "path": os.path.join(user_profile, "AppData", "Local", "CrashDumps")},
                {"label": "NPM 快取", "path": os.path.join(user_profile, "AppData", "Local", "npm-cache")},
                {"label": "Python Pip 快取", "path": os.path.join(user_profile, "AppData", "Local", "pip", "Cache")},
                {"label": "Discord 快取", "path": os.path.join(user_profile, "AppData", "Roaming", "discord", "Cache")},
                {"label": "Slack 快取", "path": os.path.join(user_profile, "AppData", "Roaming", "Slack", "Cache")},
                {"label": "Chrome 快取", "path": os.path.join(user_profile, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache")},
                {"label": "LINE 資料 (貼圖/快取可能會很大)", "path": os.path.join(user_profile, "AppData", "Local", "LINE", "Data")},
                {"label": "Firefox Profiles", "path": os.path.join(user_profile, "AppData", "Roaming", "Mozilla", "Firefox", "Profiles")},
            ])

        return candidates

from utils import (
    resize_with_padding, resize_image, Config,
    DragDropListWidget, ImagePreviewGrid, ImageViewerDialog,
    add_watermark, convert_word_to_pdf, convert_pdf_to_word,
    merge_pdfs, get_pdf_info, check_dependencies, get_config_manager,
    convert_image_to_pdf, detect_file_type, ensure_unlocked_pdf,
    PasswordRequiredError, WrongPasswordProvided
)
from utils.doc_converter import add_text_watermark_to_pdf, add_image_watermark_to_pdf
from utils.md2docx_converter import MarkdownToDocxConverter
from utils.modern_style import ModernStyle
from utils.task_manager import TaskManager, TaskQueueDialog
from utils.pdf_worker import PDFToolsWorker


class PasswordPromptCancelled(Exception):
    """User cancelled PDF password entry."""


# === Worker Threads for Background Processing ===

class VideoMergeWorker(QThread):
    """影片合併工作執行緒"""
    progress = pyqtSignal(int)  # 進度百分比
    status = pyqtSignal(str)     # 狀態訊息
    finished = pyqtSignal(bool, str)  # 完成(成功/失敗, 訊息)

    def __init__(self, files, output_path):
        super().__init__()
        self.files = files
        self.output_path = output_path
        self.is_cancelled = False

    def run(self):
        try:
            self.status.emit("正在載入影片檔案...")
            self.progress.emit(5)

            clips = []
            total_files = len(self.files)

            for i, file in enumerate(self.files):
                if self.is_cancelled:
                    self.cleanup_clips(clips)
                    self.finished.emit(False, "操作已取消")
                    return

                self.status.emit(f"載入影片 {i+1}/{total_files}...")
                clip = VideoFileClip(file)
                clips.append(clip)
                progress_pct = 5 + int((i + 1) / total_files * 25)
                self.progress.emit(progress_pct)

            if self.is_cancelled:
                self.cleanup_clips(clips)
                self.finished.emit(False, "操作已取消")
                return

            self.status.emit("正在合併影片...")
            self.progress.emit(35)

            final = concatenate_videoclips(clips, method="compose")

            if self.is_cancelled:
                self.cleanup_clips(clips)
                final.close()
                self.finished.emit(False, "操作已取消")
                return

            self.status.emit("正在輸出影片檔案...")

            # 使用 logger 來追蹤進度
            def progress_callback(current_frame, total_frames):
                if self.is_cancelled:
                    return
                if total_frames > 0:
                    progress_pct = 35 + int((current_frame / total_frames) * 60)
                    self.progress.emit(min(progress_pct, 95))

            final.write_videofile(
                self.output_path,
                codec=Config.VIDEO_CODEC,
                audio_codec=Config.AUDIO_CODEC,
                logger=None,  # 禁用 moviepy 的內建日誌
                verbose=False
            )

            self.cleanup_clips(clips)
            final.close()

            if self.is_cancelled:
                self.finished.emit(False, "操作已取消")
            else:
                self.progress.emit(100)
                self.finished.emit(True, f"影片合併完成！\n{self.output_path}")

        except Exception as e:
            self.finished.emit(False, f"合併失敗：{str(e)}")

    def cleanup_clips(self, clips):
        """清理影片片段"""
        for clip in clips:
            try:
                clip.close()
            except:
                pass

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True


class GifCreationWorker(QThread):
    """GIF 建立工作執行緒"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_path, duration, strategy):
        super().__init__()
        self.files = files
        self.output_path = output_path
        self.duration = duration
        self.strategy = strategy
        self.is_cancelled = False

    def run(self):
        try:
            total = len(self.files)
            self.status.emit(f"正在載入 {total} 個圖片...")
            self.progress.emit(5)

            # 載入圖片
            images = []
            for i, file in enumerate(self.files):
                if self.is_cancelled:
                    self.finished.emit(False, "操作已取消")
                    return

                self.status.emit(f"載入圖片 {i+1}/{total}...")
                images.append(Image.open(file))
                progress_pct = 5 + int((i + 1) / total * 30)
                self.progress.emit(progress_pct)

            if self.is_cancelled:
                self.finished.emit(False, "操作已取消")
                return

            # 計算統一尺寸
            self.status.emit("計算圖片尺寸...")
            self.progress.emit(40)

            min_w = min(img.width for img in images)
            min_h = min(img.height for img in images)

            # 調整大小
            frames = []
            for i, img in enumerate(images):
                if self.is_cancelled:
                    self.finished.emit(False, "操作已取消")
                    return

                self.status.emit(f"處理圖片 {i+1}/{total}...")
                resized = resize_image(img, (min_w, min_h), self.strategy)
                frames.append(resized)
                progress_pct = 40 + int((i + 1) / total * 40)
                self.progress.emit(progress_pct)

            if self.is_cancelled:
                self.finished.emit(False, "操作已取消")
                return

            # 儲存 GIF
            self.status.emit("正在儲存 GIF...")
            self.progress.emit(85)

            frames[0].save(
                self.output_path,
                save_all=True,
                append_images=frames[1:],
                duration=self.duration,
                loop=0
            )

            self.progress.emit(100)
            self.finished.emit(True, f"GIF 建立完成！\n{self.output_path}")

        except Exception as e:
            self.finished.emit(False, f"建立 GIF 失敗：{str(e)}")

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True


class ImageConversionWorker(QThread):
    """圖片格式轉換工作執行緒"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, output_format, output_folder):
        super().__init__()
        self.files = files
        self.output_format = output_format
        self.output_folder = output_folder
        self.is_cancelled = False

    def run(self):
        try:
            total = len(self.files)
            success_count = 0

            # 建立輸出資料夾
            if self.output_folder and not os.path.exists(self.output_folder):
                os.makedirs(self.output_folder)

            for i, file in enumerate(self.files):
                if self.is_cancelled:
                    self.finished.emit(False, f"操作已取消（已轉換 {success_count}/{total}）")
                    return

                try:
                    self.status.emit(f"轉換 {i+1}/{total}: {os.path.basename(file)}")

                    img = Image.open(file)
                    base = os.path.splitext(os.path.basename(file))[0]

                    if self.output_folder:
                        save_path = os.path.join(self.output_folder, f"{base}.{self.output_format}")
                    else:
                        save_path = os.path.join(os.path.dirname(file), f"{base}.{self.output_format}")

                    img.save(save_path, format=self.output_format.upper())
                    success_count += 1

                except Exception as e:
                    print(f"轉換失敗：{file} - {e}")

                progress_pct = int((i + 1) / total * 100)
                self.progress.emit(progress_pct)

            if success_count > 0:
                self.finished.emit(True, f"成功轉換 {success_count}/{total} 個檔案！")
            else:
                self.finished.emit(False, "轉換失敗")

        except Exception as e:
            self.finished.emit(False, f"轉換過程發生錯誤：{str(e)}")

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True


class VideoToGifWorker(QThread):
    """影片轉 GIF 工作執行緒"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, video_path, output_path, mode, start_time=0, end_time=0, fps=10,
                 resize_width=0, sample_interval=10, frame_duration=500):
        super().__init__()
        self.video_path = video_path
        self.output_path = output_path
        self.mode = mode  # 'continuous' 或 'sampling'
        self.start_time = start_time
        self.end_time = end_time
        self.fps = fps
        self.resize_width = resize_width
        self.sample_interval = sample_interval  # 採樣間隔（秒）
        self.frame_duration = frame_duration    # 每幀停留時間（毫秒）
        self.is_cancelled = False

    def run(self):
        try:
            if self.mode == 'continuous':
                self._run_continuous_mode()
            else:
                self._run_sampling_mode()
        except Exception as e:
            self.finished.emit(False, f"轉換失敗：{str(e)}")

    def _run_continuous_mode(self):
        """連續模式：截取時間範圍，生成流暢動畫"""
        self.status.emit("正在載入影片...")
        self.progress.emit(5)

        clip = VideoFileClip(self.video_path)

        if self.is_cancelled:
            clip.close()
            self.finished.emit(False, "操作已取消")
            return

        # 截取時間範圍
        duration = clip.duration
        start = max(0, self.start_time)
        end = min(duration, self.end_time) if self.end_time > 0 else duration

        if start >= end:
            clip.close()
            self.finished.emit(False, "起始時間必須小於結束時間")
            return

        self.status.emit(f"截取片段：{start:.1f}s - {end:.1f}s")
        self.progress.emit(15)

        subclip = clip.subclip(start, end)

        if self.is_cancelled:
            subclip.close()
            clip.close()
            self.finished.emit(False, "操作已取消")
            return

        # 調整大小
        if self.resize_width and self.resize_width > 0:
            self.status.emit("調整影片尺寸...")
            self.progress.emit(25)
            subclip = subclip.resize(width=self.resize_width)

        if self.is_cancelled:
            subclip.close()
            clip.close()
            self.finished.emit(False, "操作已取消")
            return

        # 轉換為 GIF
        self.status.emit("正在生成 GIF（可能需要一些時間）...")
        self.progress.emit(40)

        subclip.write_gif(
            self.output_path,
            fps=self.fps,
            program='ffmpeg',
            opt='nq',
            logger=None
        )

        self.progress.emit(100)
        clip.close()

        if self.is_cancelled:
            self.finished.emit(False, "操作已取消")
        else:
            file_size = os.path.getsize(self.output_path) / (1024 * 1024)
            self.finished.emit(True, f"GIF 生成完成！\n{self.output_path}\n檔案大小：{file_size:.2f} MB")

    def _run_sampling_mode(self):
        """採樣模式：每隔 N 秒取一幀"""
        self.status.emit("正在載入影片...")
        self.progress.emit(5)

        clip = VideoFileClip(self.video_path)

        if self.is_cancelled:
            clip.close()
            self.finished.emit(False, "操作已取消")
            return

        duration = clip.duration

        # 計算採樣點
        sample_times = []
        current_time = 0
        while current_time < duration:
            sample_times.append(current_time)
            current_time += self.sample_interval

        total_frames = len(sample_times)
        self.status.emit(f"將從影片中採樣 {total_frames} 幀...")
        self.progress.emit(10)

        if total_frames == 0:
            clip.close()
            self.finished.emit(False, "採樣間隔過大，無法產生幀")
            return

        # 逐一採樣
        frames = []
        for i, sample_time in enumerate(sample_times):
            if self.is_cancelled:
                clip.close()
                self.finished.emit(False, "操作已取消")
                return

            self.status.emit(f"採樣第 {i+1}/{total_frames} 幀（{sample_time:.1f}秒）...")

            # 取得該時間點的幀
            frame = clip.get_frame(sample_time)

            # 轉換為 PIL Image
            from PIL import Image as PILImage
            import numpy as np
            pil_image = PILImage.fromarray(np.uint8(frame))

            # 調整大小
            if self.resize_width and self.resize_width > 0:
                aspect_ratio = pil_image.height / pil_image.width
                new_height = int(self.resize_width * aspect_ratio)
                pil_image = pil_image.resize((self.resize_width, new_height), PILImage.Resampling.LANCZOS)

            frames.append(pil_image)

            progress = 10 + int((i + 1) / total_frames * 70)
            self.progress.emit(progress)

        clip.close()

        if self.is_cancelled:
            self.finished.emit(False, "操作已取消")
            return

        # 儲存為 GIF
        self.status.emit("正在儲存 GIF...")
        self.progress.emit(85)

        frames[0].save(
            self.output_path,
            save_all=True,
            append_images=frames[1:],
            duration=self.frame_duration,
            loop=0,
            optimize=True
        )

        self.progress.emit(100)

        file_size = os.path.getsize(self.output_path) / (1024 * 1024)
        self.finished.emit(True,
            f"GIF 生成完成！\n{self.output_path}\n"
            f"總幀數：{total_frames}\n"
            f"檔案大小：{file_size:.2f} MB")

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True


class ImageCompressionWorker(QThread):
    """圖片壓縮工作執行緒"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    stats = pyqtSignal(str)  # 壓縮統計資訊
    finished = pyqtSignal(bool, str)

    def __init__(self, files, quality, output_format, output_folder):
        super().__init__()
        self.files = files
        self.quality = quality
        self.output_format = output_format
        self.output_folder = output_folder
        self.is_cancelled = False

    def run(self):
        try:
            total = len(self.files)
            success_count = 0
            original_size = 0
            compressed_size = 0

            # 建立輸出資料夾
            if self.output_folder and not os.path.exists(self.output_folder):
                os.makedirs(self.output_folder)

            for i, file in enumerate(self.files):
                if self.is_cancelled:
                    self.finished.emit(False, f"操作已取消（已壓縮 {success_count}/{total}）")
                    return

                try:
                    self.status.emit(f"壓縮 {i+1}/{total}: {os.path.basename(file)}")

                    # 獲取原始檔案大小
                    orig_size = os.path.getsize(file)
                    original_size += orig_size

                    img = Image.open(file)

                    # 如果是 PNG 且目標是 JPG，需要轉換模式
                    if self.output_format.lower() in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
                        # 創建白色背景
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background

                    base = os.path.splitext(os.path.basename(file))[0]

                    if self.output_folder:
                        save_path = os.path.join(self.output_folder, f"{base}_compressed.{self.output_format}")
                    else:
                        save_path = os.path.join(os.path.dirname(file), f"{base}_compressed.{self.output_format}")

                    # 壓縮保存
                    if self.output_format.lower() in ['jpg', 'jpeg']:
                        img.save(save_path, format='JPEG', quality=self.quality, optimize=True)
                    elif self.output_format.lower() == 'png':
                        img.save(save_path, format='PNG', optimize=True, compress_level=9)
                    elif self.output_format.lower() == 'webp':
                        img.save(save_path, format='WEBP', quality=self.quality)
                    else:
                        img.save(save_path, quality=self.quality, optimize=True)

                    # 獲取壓縮後檔案大小
                    comp_size = os.path.getsize(save_path)
                    compressed_size += comp_size

                    success_count += 1

                    # 計算節省百分比
                    if orig_size > 0:
                        saved_percent = ((orig_size - comp_size) / orig_size) * 100
                        self.stats.emit(
                            f"原始：{orig_size/1024:.1f} KB → "
                            f"壓縮：{comp_size/1024:.1f} KB "
                            f"（節省 {saved_percent:.1f}%）"
                        )

                except Exception as e:
                    print(f"壓縮失敗：{file} - {e}")

                progress_pct = int((i + 1) / total * 100)
                self.progress.emit(progress_pct)

            if success_count > 0:
                total_saved = original_size - compressed_size
                total_saved_percent = (total_saved / original_size * 100) if original_size > 0 else 0

                message = (
                    f"成功壓縮 {success_count}/{total} 個檔案！\n\n"
                    f"原始總大小：{original_size/(1024*1024):.2f} MB\n"
                    f"壓縮後大小：{compressed_size/(1024*1024):.2f} MB\n"
                    f"節省空間：{total_saved/(1024*1024):.2f} MB ({total_saved_percent:.1f}%)"
                )
                self.finished.emit(True, message)
            else:
                self.finished.emit(False, "壓縮失敗")

        except Exception as e:
            self.finished.emit(False, f"壓縮過程發生錯誤：{str(e)}")

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True



class VideoCompressionWorker(QThread):
    """影片壓縮工作執行緒"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    stats = pyqtSignal(str)  # 壓縮統計資訊
    finished = pyqtSignal(bool, str)

    def __init__(self, files, resolution, crf, output_folder):
        super().__init__()
        self.files = files
        self.resolution = resolution  # 'Original', '1080p', '720p', '480p'
        self.crf = crf
        self.output_folder = output_folder
        self.is_cancelled = False

    def run(self):
        try:
            total = len(self.files)
            success_count = 0
            original_size = 0
            compressed_size = 0

            # 建立輸出資料夾
            if self.output_folder and not os.path.exists(self.output_folder):
                os.makedirs(self.output_folder)

            for i, file in enumerate(self.files):
                if self.is_cancelled:
                    self.finished.emit(False, f"操作已取消（已壓縮 {success_count}/{total}）")
                    return

                try:
                    self.status.emit(f"壓縮 {i+1}/{total}: {os.path.basename(file)}")

                    # 獲取原始檔案大小
                    orig_size = os.path.getsize(file)
                    original_size += orig_size

                    # 設定輸出路徑
                    base = os.path.splitext(os.path.basename(file))[0]
                    # 預設輸出為 MP4 以確保相容性
                    if self.output_folder:
                        save_path = os.path.join(self.output_folder, f"{base}_compressed.mp4")
                    else:
                        save_path = os.path.join(os.path.dirname(file), f"{base}_compressed.mp4")

                    # 載入影片
                    clip = VideoFileClip(file)
                    
                    # 處理解析度
                    if self.resolution != 'Original':
                        target_h = int(self.resolution.replace('p', ''))
                        if clip.h > target_h:
                            clip = clip.resize(height=target_h)

                    # 壓縮並儲存
                    # audio_codec='aac' 確保音訊相容性
                    # preset='medium' 平衡速度與壓縮率
                    # threads=4 使用多執行緒
                    clip.write_videofile(
                        save_path,
                        codec=Config.VIDEO_CODEC,
                        audio_codec=Config.AUDIO_CODEC,
                        ffmpeg_params=['-crf', str(self.crf), '-pix_fmt', 'yuv420p'],
                        preset='medium',
                        threads=4,
                        logger=None,
                        temp_audiofile='temp-audio.m4a',
                        remove_temp=True
                    )
                    
                    clip.close()

                    # 獲取壓縮後檔案大小
                    comp_size = os.path.getsize(save_path)
                    compressed_size += comp_size

                    success_count += 1

                    # 計算節省百分比
                    if orig_size > 0:
                        saved_percent = ((orig_size - comp_size) / orig_size) * 100
                        self.stats.emit(
                            f"原始：{orig_size/(1024*1024):.1f} MB → "
                            f"壓縮：{comp_size/(1024*1024):.1f} MB "
                            f"（節省 {saved_percent:.1f}%）"
                        )

                except Exception as e:
                    print(f"壓縮失敗：{file} - {e}")

                progress_pct = int((i + 1) / total * 100)
                self.progress.emit(progress_pct)

            if success_count > 0:
                total_saved = original_size - compressed_size
                total_saved_percent = (total_saved / original_size * 100) if original_size > 0 else 0

                message = (
                    f"成功壓縮 {success_count}/{total} 個檔案！\n\n"
                    f"原始總大小：{original_size/(1024*1024):.2f} MB\n"
                    f"壓縮後大小：{compressed_size/(1024*1024):.2f} MB\n"
                    f"節省空間：{total_saved/(1024*1024):.2f} MB ({total_saved_percent:.1f}%)"
                )
                self.finished.emit(True, message)
            else:
                self.finished.emit(False, "壓縮失敗")

        except Exception as e:
            self.finished.emit(False, f"壓縮過程發生錯誤：{str(e)}")

    def cancel(self):
        """取消操作"""
        self.is_cancelled = True


class MarkdownConversionWorker(QThread):

    """Markdown 轉換 Word 工作執行緒"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_file, output_file):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.is_cancelled = False

    def run(self):
        try:
            self.status.emit("正在初始化轉換器...")
            converter = MarkdownToDocxConverter()
            
            if self.is_cancelled:
                self.finished.emit(False, "操作已取消")
                return

            self.status.emit("正在讀取並轉換文件...")
            # 由於 docx 轉換是同步的且通常很快，我們這裡做一個簡單的模擬進度或者直接轉換
            
            converter.convert_file(self.input_file, self.output_file)
            
            self.progress.emit(100)
            self.finished.emit(True, f"成功轉換為：\n{self.output_file}")
            
        except Exception as e:
            self.finished.emit(False, f"轉換失敗：{str(e)}")

    def cancel(self):
        self.is_cancelled = True


class MarkdownToolsWorker(QThread):
    """
    通用 Markdown 轉換工作執行緒
    支援：md_to_pdf, md_to_docx, docx_to_md, pdf_to_md
    """
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, mode: str, input_file: str, output_file: str):
        super().__init__()
        self.mode = mode
        self.input_file = input_file
        self.output_file = output_file
        self.is_cancelled = False

    def run(self):
        try:
            from utils.md_converter import MarkdownConverter
            
            def callback(p, s):
                if self.is_cancelled:
                    raise Exception("已取消")
                self.progress.emit(p)
                self.status.emit(s)
            
            if self.mode == 'md_to_pdf':
                callback(5, "準備轉換 Markdown → PDF...")
                MarkdownConverter.md_to_pdf(self.input_file, self.output_file, callback)
                
            elif self.mode == 'md_to_docx':
                callback(5, "準備轉換 Markdown → Word...")
                MarkdownConverter.md_to_docx(self.input_file, self.output_file, callback)
                
            elif self.mode == 'docx_to_md':
                callback(5, "準備轉換 Word → Markdown...")
                MarkdownConverter.docx_to_md(self.input_file, self.output_file, callback)
                
            elif self.mode == 'pdf_to_md':
                callback(5, "準備轉換 PDF → Markdown...")
                MarkdownConverter.pdf_to_md(self.input_file, self.output_file, callback)
            
            else:
                self.finished.emit(False, f"未知的轉換模式：{self.mode}")
                return
            
            self.progress.emit(100)
            self.finished.emit(True, f"轉換成功！\n已儲存至：{self.output_file}")
            
        except Exception as e:
            if "已取消" in str(e):
                self.finished.emit(False, "操作已取消")
            else:
                self.finished.emit(False, f"轉換失敗：{str(e)}")

    def cancel(self):
        self.is_cancelled = True


class BatchRenameWorker(QThread):
    """批次重新命名工作執行緒"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, rules):
        super().__init__()
        self.files = files
        self.rules = rules  # 字典包含: prefix, suffix, replace_old, replace_new, start_num, num_digits
        self.is_cancelled = False

    def run(self):
        try:
            total = len(self.files)
            success_count = 0
            
            # 排序檔案以確保編號順序
            sorted_files = natsorted(self.files)

            prefix = self.rules.get('prefix', '')
            suffix = self.rules.get('suffix', '')
            replace_old = self.rules.get('replace_old', '')
            replace_new = self.rules.get('replace_new', '')
            start_num = self.rules.get('start_num', 1)
            num_digits = self.rules.get('num_digits', 3)
            use_num = self.rules.get('use_num', False)
            ext_mode = self.rules.get('ext_mode', 'keep') # keep, lower, upper

            for i, file_path in enumerate(sorted_files):
                if self.is_cancelled:
                    self.finished.emit(False, "操作已取消")
                    return

                dirname = os.path.dirname(file_path)
                filename = os.path.basename(file_path)
                name, ext = os.path.splitext(filename)

                # 1. 替換文字
                if replace_old:
                    name = name.replace(replace_old, replace_new)

                # 2. 添加前綴後綴
                new_name = f"{prefix}{name}{suffix}"

                # 3. 編號
                if use_num:
                    num_str = str(start_num + i).zfill(num_digits)
                    new_name = f"{new_name}_{num_str}"
                
                # 4. 副檔名處理
                if ext_mode == 'lower':
                    ext = ext.lower()
                elif ext_mode == 'upper':
                    ext = ext.upper()

                final_name = f"{new_name}{ext}"
                new_path = os.path.join(dirname, final_name)

                # 檢查檔名衝突
                if os.path.exists(new_path) and new_path != file_path:
                    # 自動重新命名避免覆蓋
                    base, ex = os.path.splitext(final_name)
                    final_name = f"{base}_new{ex}"
                    new_path = os.path.join(dirname, final_name)

                try:
                    os.rename(file_path, new_path)
                    success_count += 1
                except Exception as e:
                    print(f"Rename failed: {file_path} -> {new_path}: {e}")

                progress = int((i + 1) / total * 100)
                self.progress.emit(progress)
                self.status.emit(f"已重新命名 {i+1}/{total}: {final_name}")

            self.finished.emit(True, f"成功重新命名 {success_count}/{total} 個檔案")

        except Exception as e:
            self.finished.emit(False, f"重新命名失敗：{str(e)}")

    def cancel(self):
        self.is_cancelled = True


class ImageEditWorker(QThread):
    """圖片編輯工作執行緒"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, files, operations, output_folder=None):
        super().__init__()
        self.files = files
        self.operations = operations # list of dict: {'type': 'rotate', 'value': 90}, {'type': 'flip', 'mode': 'horizontal'}
        self.output_folder = output_folder
        self.is_cancelled = False

    def run(self):
        try:
            total = len(self.files)
            success_count = 0

            if self.output_folder and not os.path.exists(self.output_folder):
                os.makedirs(self.output_folder)

            for i, file_path in enumerate(self.files):
                if self.is_cancelled:
                    self.finished.emit(False, "操作已取消")
                    return

                self.status.emit(f"處理圖片 {i+1}/{total}...")
                
                try:
                    img = Image.open(file_path)
                    
                    # 應用操作
                    for op in self.operations:
                        if op['type'] == 'rotate':
                            # Expand=True 以確保旋轉後圖片不被裁切
                            img = img.rotate(-op['value'], expand=True) 
                        elif op['type'] == 'flip':
                            if op['mode'] == 'horizontal':
                                img = img.transpose(Image.FLIP_LEFT_RIGHT)
                            elif op['mode'] == 'vertical':
                                img = img.transpose(Image.FLIP_TOP_BOTTOM)
                    
                    # 儲存
                    filename = os.path.basename(file_path)
                    if self.output_folder:
                        save_path = os.path.join(self.output_folder, filename)
                    else:
                        # 覆蓋原檔或另存新檔
                        base, ext = os.path.splitext(file_path)
                        save_path = f"{base}_edited{ext}"

                    img.save(save_path)
                    success_count += 1
                    
                except Exception as e:
                    print(f"Edit failed {file_path}: {e}")

                self.progress.emit(int((i + 1) / total * 100))

            self.finished.emit(True, f"成功編輯 {success_count}/{total} 張圖片")

        except Exception as e:
            self.finished.emit(False, f"編輯失敗：{str(e)}")

    def cancel(self):
        self.is_cancelled = True


class MediaToolkit(QMainWindow):
    """多媒體與文檔處理工具套件"""

    def __init__(self):
        super().__init__()

        # 載入配置管理器
        self.config = get_config_manager()
        self._pdf_password_cache = {}
        self._loading_preferences = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.config.save_config)

        # 從配置載入設定
        self.current_theme = self.config.get('theme', 'light')
        self._group_boxes = []
        self.setWindowTitle("📦 MediaToolkit v6.0 - 多媒體與文檔處理工具套件")

        # 從配置恢復視窗大小和位置
        self._restore_window_geometry()
        self.setMinimumSize(1000, 700)

        # 工作執行緒
        self.video_worker = None
        self.gif_worker = None
        self.convert_worker = None
        self.video_to_gif_worker = None
        self.compress_worker = None
        self.compress_worker = None
        self.md_worker = None
        self.pdf_tool_worker = None
        self.batch_rename_worker = None
        self.image_edit_worker = None
        
        # 任務管理器
        self.task_manager = TaskManager()

        # 時間追蹤
        self.operation_start_time = None

        self.doc_deps = check_dependencies()
        self._init_ui()
        self._create_menus()
        self._apply_theme(self.current_theme)

        # 載入保存的參數
        self._load_parameters()

    def _init_ui(self):
        """初始化 UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        central_widget.setLayout(main_layout)

        # 標題
        header_layout = QHBoxLayout()
        title = QLabel("📦 MediaToolkit")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #3B82F6;")
        header_layout.addWidget(title)
        subtitle = QLabel("多媒體與文檔處理工具套件")
        subtitle.setStyleSheet("color: #64748B; font-size: 11pt; margin-left: 10px;")
        header_layout.addWidget(subtitle)
        header_layout.addStretch()
        
        version_label = QLabel("v6.0")
        version_label.setStyleSheet("color: #64748B; font-size: 9pt;")
        header_layout.addWidget(version_label)
        
        # 頂部工具列按鈕
        tools_layout = QHBoxLayout()
        
        # 任務按鈕
        self.btn_tasks = QPushButton("📋 任務")
        self.btn_tasks.setProperty("secondary", True)
        self.btn_tasks.setFixedWidth(80)
        self.btn_tasks.clicked.connect(self._show_task_manager)
        tools_layout.addWidget(self.btn_tasks)

        header_layout.addLayout(tools_layout)
        main_layout.addLayout(header_layout)

        # 頂層分類分頁
        self.category_tabs = QTabWidget()
        self.category_tabs.setDocumentMode(True)
        
        # 圖片影像處理類別
        media_widget = QWidget()
        media_layout = QVBoxLayout(media_widget)
        media_layout.setContentsMargins(0, 10, 0, 0)
        self.media_tabs = QTabWidget()
        self.media_tabs.setDocumentMode(True)
        self._create_image_tab()
        self._create_video_tab()
        self._create_convert_tab()
        self._create_video_to_gif_tab()
        self._create_image_compression_tab()
        self._create_video_compression_tab()  # 新增影片壓縮分頁
        self._create_image_editor_tab()
        media_layout.addWidget(self.media_tabs)
        
        # 文件轉換類別
        doc_widget = QWidget()
        doc_layout = QVBoxLayout(doc_widget)
        doc_layout.setContentsMargins(0, 10, 0, 0)
        self.doc_tabs = QTabWidget()
        self.doc_tabs.setDocumentMode(True)
        self._create_word_pdf_tab()
        self._create_markdown_tab()
        self._create_pdf_tools_tab()
        self._create_pdf_merge_tab()
        self._create_pdf_watermark_tab()
        doc_layout.addWidget(self.doc_tabs)
        
        self.category_tabs.addTab(media_widget, "🎨 圖片影像處理")
        self.category_tabs.addTab(doc_widget, "📄 文件轉換工具")
        
        # 實用工具分頁
        utils_widget = QWidget()
        utils_layout = QVBoxLayout(utils_widget)
        utils_layout.setContentsMargins(0, 10, 0, 0)
        self.utils_tabs = QTabWidget()
        self.utils_tabs.setDocumentMode(True)
        self._create_batch_rename_tab()
        self._createCleanupTab()
        utils_layout.addWidget(self.utils_tabs)
        
        self.category_tabs.addTab(utils_widget, "🛠️ 實用工具")

        main_layout.addWidget(self.category_tabs)
        
        self.statusBar().showMessage('🎉 MediaToolkit 已就緒！  |  © 2025 Dof Liu AI工作室')
        
        # 檢查是否有最近開啟的檔案
        QTimer.singleShot(1000, self._check_recent_files_on_startup)

    def _check_recent_files_on_startup(self):
        """啟動時檢查並提示最近的檔案"""
        # 可以選擇是否實作此功能，這裡先保留接口
        pass

    def _create_image_tab(self):
        """圖片處理分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # 檔案選擇
        group = self._create_group_box("📁 選擇圖片檔案 - 支援拖放")
        file_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        btn_select = QPushButton("📂 選擇圖片")
        btn_select.clicked.connect(self.select_files)
        btn_select.setMinimumHeight(40)
        btn_layout.addWidget(btn_select)
        btn_layout.addWidget(QLabel("或拖放檔案到下方"))
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)
        
        self.image_preview = ImagePreviewGrid()
        self.image_preview.file_clicked.connect(self._show_image_viewer)
        self.image_preview.files_changed.connect(self._update_image_stats)
        self.image_preview.ingest_completed.connect(self._on_image_ingest_completed)
        self.image_preview.setMinimumHeight(200)
        file_layout.addWidget(self.image_preview)
        group.setLayout(file_layout)
        layout.addWidget(group)

        # 參數設定
        params = self._create_group_box("⚙️ 參數設定")
        p_layout = QVBoxLayout()
        
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(QLabel("列數:"))
        self.edit_cols = QLineEdit(str(Config.DEFAULT_GRID_COLS))
        self.edit_cols.setMaximumWidth(80)
        self.edit_cols.editingFinished.connect(
            lambda: self._on_numeric_pref_changed(self.edit_cols, 'image.grid_cols', 1, Config.DEFAULT_GRID_COLS)
        )
        grid_layout.addWidget(self.edit_cols)
        grid_layout.addWidget(QLabel("行數:"))
        self.edit_rows = QLineEdit(str(Config.DEFAULT_GRID_ROWS))
        self.edit_rows.setMaximumWidth(80)
        self.edit_rows.editingFinished.connect(
            lambda: self._on_numeric_pref_changed(self.edit_rows, 'image.grid_rows', 1, Config.DEFAULT_GRID_ROWS)
        )
        grid_layout.addWidget(self.edit_rows)
        grid_layout.addStretch()
        p_layout.addLayout(grid_layout)
        
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("縮放策略:"))
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(Config.RESIZE_STRATEGIES)
        self.combo_strategy.currentTextChanged.connect(
            lambda text: self._on_combo_pref_changed('image.resize_strategy', text)
        )
        strategy_layout.addWidget(self.combo_strategy)
        strategy_layout.addStretch()
        p_layout.addLayout(strategy_layout)
        
        gif_layout = QHBoxLayout()
        gif_layout.addWidget(QLabel("GIF 持續時間 (ms):"))
        self.edit_duration = QLineEdit(str(Config.DEFAULT_GIF_DURATION))
        self.edit_duration.setMaximumWidth(100)
        self.edit_duration.editingFinished.connect(
            lambda: self._on_numeric_pref_changed(self.edit_duration, 'image.gif_duration', 50, Config.DEFAULT_GIF_DURATION)
        )
        gif_layout.addWidget(self.edit_duration)
        gif_layout.addStretch()
        p_layout.addLayout(gif_layout)
        
        params.setLayout(p_layout)
        layout.addWidget(params)

        pref_buttons = QHBoxLayout()
        self.btn_save_prefs = QPushButton("保存設定")
        self.btn_save_prefs.setProperty("secondary", True)
        self.btn_save_prefs.clicked.connect(self._manual_save_preferences)
        pref_buttons.addWidget(self.btn_save_prefs)

        self.btn_reset_prefs = QPushButton("恢復預設")
        self.btn_reset_prefs.setProperty("secondary", True)
        self.btn_reset_prefs.clicked.connect(self._reset_preferences)
        pref_buttons.addWidget(self.btn_reset_prefs)
        pref_buttons.addStretch()
        layout.addLayout(pref_buttons)

        # GIF 進度顯示區域
        self.gif_progress_widget = QWidget()
        gif_progress_layout = QVBoxLayout(self.gif_progress_widget)
        gif_progress_layout.setContentsMargins(0, 0, 0, 0)

        self.gif_status_label = QLabel("就緒")
        self.gif_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        gif_progress_layout.addWidget(self.gif_status_label)

        self.gif_progress = QProgressBar()
        self.gif_progress.setTextVisible(True)
        gif_progress_layout.addWidget(self.gif_progress)

        self.gif_time_label = QLabel("")
        self.gif_time_label.setStyleSheet("color: #64748B; font-size: 9pt;")
        gif_progress_layout.addWidget(self.gif_time_label)

        self.gif_progress_widget.setVisible(False)
        layout.addWidget(self.gif_progress_widget)

        # 操作按鈕
        action_layout = QHBoxLayout()
        btn_merge = QPushButton("🖼️ 拼接圖片")
        btn_merge.clicked.connect(self.merge_images)
        btn_merge.setMinimumHeight(44)
        action_layout.addWidget(btn_merge)

        self.btn_create_gif = QPushButton("🎞️ 生成 GIF")
        self.btn_create_gif.clicked.connect(self.create_gif)
        self.btn_create_gif.setMinimumHeight(44)
        action_layout.addWidget(self.btn_create_gif)

        btn_watermark = QPushButton("🏷️ 添加浮水印")
        btn_watermark.clicked.connect(self._add_watermark)
        btn_watermark.setMinimumHeight(44)
        action_layout.addWidget(btn_watermark)

        layout.addLayout(action_layout)

        # GIF 取消按鈕
        cancel_layout = QHBoxLayout()
        self.btn_cancel_gif = QPushButton("❌ 取消 GIF 建立")
        self.btn_cancel_gif.setProperty("secondary", True)
        self.btn_cancel_gif.clicked.connect(self._cancel_gif_creation)
        self.btn_cancel_gif.setMinimumHeight(40)
        self.btn_cancel_gif.setVisible(False)
        cancel_layout.addWidget(self.btn_cancel_gif)
        layout.addLayout(cancel_layout)

        layout.addStretch()
        self.media_tabs.addTab(tab, "🖼️ 圖片處理")

    def _create_video_tab(self):
        """影片處理分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = self._create_group_box("📹 選擇影片檔案")
        file_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        btn_select = QPushButton("📂 選擇影片")
        btn_select.clicked.connect(self.select_video_files)
        btn_select.setMinimumHeight(40)
        btn_layout.addWidget(btn_select)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)
        
        self.video_files_list = DragDropListWidget(file_extensions=Config.SUPPORTED_VIDEO_FORMATS)
        self.video_files_list.drop_completed.connect(self._on_video_dropped)
        file_layout.addWidget(self.video_files_list)
        group.setLayout(file_layout)
        layout.addWidget(group)
        
        output_group = self._create_group_box("💾 輸出設定")
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("輸出檔名:"))
        self.edit_output_video = QLineEdit("merged_video.mp4")
        self.edit_output_video.editingFinished.connect(
            lambda: self._on_text_pref_changed(self.edit_output_video, 'video.output_name')
        )
        out_layout.addWidget(self.edit_output_video)
        output_group.setLayout(out_layout)
        layout.addWidget(output_group)

        # 進度顯示區域
        self.video_progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.video_progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        self.video_status_label = QLabel("就緒")
        self.video_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        progress_layout.addWidget(self.video_status_label)

        self.video_progress = QProgressBar()
        self.video_progress.setTextVisible(True)
        progress_layout.addWidget(self.video_progress)

        self.video_time_label = QLabel("")
        self.video_time_label.setStyleSheet("color: #64748B; font-size: 9pt;")
        progress_layout.addWidget(self.video_time_label)

        self.video_progress_widget.setVisible(False)
        layout.addWidget(self.video_progress_widget)

        # 按鈕區域
        btn_layout = QHBoxLayout()
        self.btn_merge_video = QPushButton("🎬 合併影片")
        self.btn_merge_video.clicked.connect(self.merge_videos)
        self.btn_merge_video.setMinimumHeight(44)
        btn_layout.addWidget(self.btn_merge_video)

        self.btn_cancel_video = QPushButton("❌ 取消")
        self.btn_cancel_video.setProperty("secondary", True)
        self.btn_cancel_video.clicked.connect(self._cancel_video_merge)
        self.btn_cancel_video.setMinimumHeight(44)
        self.btn_cancel_video.setVisible(False)
        btn_layout.addWidget(self.btn_cancel_video)

        layout.addLayout(btn_layout)
        
        layout.addStretch()
        self.media_tabs.addTab(tab, "🎬 影片處理")

    def _create_convert_tab(self):
        """格式轉換分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        group = self._create_group_box("📁 選擇圖片")
        file_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        btn = QPushButton("📂 選擇圖片")
        btn.clicked.connect(self.select_convert_images)
        btn.setMinimumHeight(40)
        btn_layout.addWidget(btn)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)
        
        exts = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']
        self.convert_list = DragDropListWidget(file_extensions=exts)
        self.convert_list.drop_completed.connect(self._on_convert_dropped)
        file_layout.addWidget(self.convert_list)
        group.setLayout(file_layout)
        layout.addWidget(group)
        
        settings = self._create_group_box("🔄 轉換設定")
        s_layout = QVBoxLayout()
        
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("輸出格式:"))
        self.combo_output_format = QComboBox()
        self.combo_output_format.addItems(Config.SUPPORTED_IMAGE_FORMATS)
        self.combo_output_format.currentTextChanged.connect(
            lambda text: self._on_combo_pref_changed('convert.output_format', text)
        )
        fmt_layout.addWidget(self.combo_output_format)
        fmt_layout.addStretch()
        s_layout.addLayout(fmt_layout)
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("輸出資料夾:"))
        self.edit_output_folder = QLineEdit("converted_images")
        self.edit_output_folder.editingFinished.connect(
            lambda: self._on_text_pref_changed(self.edit_output_folder, 'convert.output_folder')
        )
        folder_layout.addWidget(self.edit_output_folder)
        btn_browse = QPushButton("📂 瀏覽")
        btn_browse.setProperty("secondary", True)
        btn_browse.clicked.connect(self.browse_output_folder)
        folder_layout.addWidget(btn_browse)
        s_layout.addLayout(folder_layout)
        
        settings.setLayout(s_layout)
        layout.addWidget(settings)

        # 進度顯示區域
        self.convert_progress_widget = QWidget()
        convert_progress_layout = QVBoxLayout(self.convert_progress_widget)
        convert_progress_layout.setContentsMargins(0, 0, 0, 0)

        self.convert_status_label = QLabel("就緒")
        self.convert_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        convert_progress_layout.addWidget(self.convert_status_label)

        self.convert_progress = QProgressBar()
        self.convert_progress.setTextVisible(True)
        convert_progress_layout.addWidget(self.convert_progress)

        self.convert_time_label = QLabel("")
        self.convert_time_label.setStyleSheet("color: #64748B; font-size: 9pt;")
        convert_progress_layout.addWidget(self.convert_time_label)

        self.convert_progress_widget.setVisible(False)
        layout.addWidget(self.convert_progress_widget)

        # 按鈕區域
        btn_layout = QHBoxLayout()
        self.btn_convert = QPushButton("✨ 開始轉換")
        self.btn_convert.clicked.connect(self.convert_images)
        self.btn_convert.setMinimumHeight(44)
        btn_layout.addWidget(self.btn_convert)

        self.btn_cancel_convert = QPushButton("❌ 取消")
        self.btn_cancel_convert.setProperty("secondary", True)
        self.btn_cancel_convert.clicked.connect(self._cancel_conversion)
        self.btn_cancel_convert.setMinimumHeight(44)
        self.btn_cancel_convert.setVisible(False)
        btn_layout.addWidget(self.btn_cancel_convert)

        layout.addLayout(btn_layout)

        layout.addStretch()
        self.media_tabs.addTab(tab, "🔄 格式轉換")

    def _create_video_to_gif_tab(self):
        """影片轉 GIF 分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 影片選擇
        group = self._create_group_box("🎬 選擇影片檔案")
        file_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        btn = QPushButton("📂 選擇影片")
        btn.clicked.connect(self._select_video_for_gif)
        btn.setMinimumHeight(40)
        btn_layout.addWidget(btn)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        self.video_to_gif_path = QLineEdit()
        self.video_to_gif_path.setPlaceholderText("未選擇影片...")
        self.video_to_gif_path.setReadOnly(True)
        file_layout.addWidget(self.video_to_gif_path)

        group.setLayout(file_layout)
        layout.addWidget(group)

        # 模式選擇
        mode_group = self._create_group_box("🎯 轉換模式")
        mode_layout = QVBoxLayout()

        from PyQt5.QtWidgets import QRadioButton, QButtonGroup

        self.gif_mode_group = QButtonGroup()

        self.gif_mode_continuous = QRadioButton("連續模式 - 流暢動畫（截取時間範圍）")
        self.gif_mode_continuous.setChecked(True)
        self.gif_mode_continuous.toggled.connect(self._on_gif_mode_changed)
        self.gif_mode_group.addButton(self.gif_mode_continuous)
        mode_layout.addWidget(self.gif_mode_continuous)

        self.gif_mode_sampling = QRadioButton("採樣模式 - 縮時效果（每隔 N 秒取一幀）")
        self.gif_mode_sampling.toggled.connect(self._on_gif_mode_changed)
        self.gif_mode_group.addButton(self.gif_mode_sampling)
        mode_layout.addWidget(self.gif_mode_sampling)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # 連續模式參數
        self.continuous_params = self._create_group_box("⚙️ 連續模式參數")
        cp_layout = QVBoxLayout()

        # 時間範圍
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("起始時間 (秒):"))
        self.gif_start_time = QLineEdit("0")
        self.gif_start_time.setMaximumWidth(100)
        time_layout.addWidget(self.gif_start_time)

        time_layout.addWidget(QLabel("結束時間 (秒):"))
        self.gif_end_time = QLineEdit("0")
        self.gif_end_time.setMaximumWidth(100)
        self.gif_end_time.setPlaceholderText("0=完整影片")
        time_layout.addWidget(self.gif_end_time)
        time_layout.addStretch()
        cp_layout.addLayout(time_layout)

        # FPS
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("幀率 (FPS):"))
        self.gif_fps = QLineEdit("10")
        self.gif_fps.setMaximumWidth(80)
        fps_layout.addWidget(self.gif_fps)
        fps_layout.addWidget(QLabel("（建議 8-15）"))
        fps_layout.addStretch()
        cp_layout.addLayout(fps_layout)

        self.continuous_params.setLayout(cp_layout)
        layout.addWidget(self.continuous_params)

        # 採樣模式參數
        self.sampling_params = self._create_group_box("⚙️ 採樣模式參數")
        sp_layout = QVBoxLayout()

        # 採樣間隔
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("採樣間隔 (秒):"))
        self.gif_sample_interval = QLineEdit("10")
        self.gif_sample_interval.setMaximumWidth(100)
        interval_layout.addWidget(self.gif_sample_interval)
        interval_layout.addWidget(QLabel("（每隔幾秒取一幀）"))
        interval_layout.addStretch()
        sp_layout.addLayout(interval_layout)

        # 每幀停留時間
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("每幀停留時間 (毫秒):"))
        self.gif_frame_duration = QLineEdit("500")
        self.gif_frame_duration.setMaximumWidth(100)
        duration_layout.addWidget(self.gif_frame_duration)
        duration_layout.addWidget(QLabel("（建議 300-1000）"))
        duration_layout.addStretch()
        sp_layout.addLayout(duration_layout)

        self.sampling_params.setLayout(sp_layout)
        self.sampling_params.setVisible(False)  # 預設隱藏
        layout.addWidget(self.sampling_params)

        # 共用參數
        common_params = self._create_group_box("🔧 共用參數")
        common_layout = QVBoxLayout()

        width_layout = QHBoxLayout()
        width_layout.addWidget(QLabel("寬度 (像素):"))
        self.gif_width = QLineEdit("0")
        self.gif_width.setMaximumWidth(100)
        self.gif_width.setPlaceholderText("0=原始大小")
        width_layout.addWidget(self.gif_width)
        width_layout.addWidget(QLabel("（建議 480-640）"))
        width_layout.addStretch()
        common_layout.addLayout(width_layout)

        common_params.setLayout(common_layout)
        layout.addWidget(common_params)

        # 進度顯示
        self.v2g_progress_widget = QWidget()
        v2g_progress_layout = QVBoxLayout(self.v2g_progress_widget)
        v2g_progress_layout.setContentsMargins(0, 0, 0, 0)

        self.v2g_status_label = QLabel("就緒")
        self.v2g_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        v2g_progress_layout.addWidget(self.v2g_status_label)

        self.v2g_progress = QProgressBar()
        self.v2g_progress.setTextVisible(True)
        v2g_progress_layout.addWidget(self.v2g_progress)

        self.v2g_time_label = QLabel("")
        self.v2g_time_label.setStyleSheet("color: #64748B; font-size: 9pt;")
        v2g_progress_layout.addWidget(self.v2g_time_label)

        self.v2g_progress_widget.setVisible(False)
        layout.addWidget(self.v2g_progress_widget)

        # 按鈕
        btn_layout = QHBoxLayout()
        self.btn_video_to_gif = QPushButton("✨ 生成 GIF")
        self.btn_video_to_gif.clicked.connect(self._start_video_to_gif)
        self.btn_video_to_gif.setMinimumHeight(44)
        btn_layout.addWidget(self.btn_video_to_gif)

        self.btn_cancel_v2g = QPushButton("❌ 取消")
        self.btn_cancel_v2g.setProperty("secondary", True)
        self.btn_cancel_v2g.clicked.connect(self._cancel_video_to_gif)
        self.btn_cancel_v2g.setMinimumHeight(44)
        self.btn_cancel_v2g.setVisible(False)
        btn_layout.addWidget(self.btn_cancel_v2g)

        layout.addLayout(btn_layout)

        layout.addStretch()
        self.media_tabs.addTab(tab, "🎞️ 影片轉GIF")

    def _create_image_compression_tab(self):
        """圖片壓縮分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 檔案選擇
        group = self._create_group_box("📁 選擇圖片檔案")
        file_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        btn = QPushButton("📂 選擇圖片")
        btn.clicked.connect(self._select_images_for_compression)
        btn.setMinimumHeight(40)
        btn_layout.addWidget(btn)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        exts = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
        self.compress_list = DragDropListWidget(file_extensions=exts)
        self.compress_list.drop_completed.connect(self._on_compress_dropped)
        file_layout.addWidget(self.compress_list)

        group.setLayout(file_layout)
        layout.addWidget(group)

        # 壓縮設定
        settings = self._create_group_box("🗜️ 壓縮設定")
        s_layout = QVBoxLayout()

        # 品質滑桿
        from PyQt5.QtWidgets import QSlider
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("品質:"))

        self.compress_quality_slider = QSlider(Qt.Horizontal)
        self.compress_quality_slider.setMinimum(1)
        self.compress_quality_slider.setMaximum(100)
        self.compress_quality_slider.setValue(75)
        self.compress_quality_slider.valueChanged.connect(self._update_quality_label)
        quality_layout.addWidget(self.compress_quality_slider)

        self.compress_quality_label = QLabel("75")
        self.compress_quality_label.setMinimumWidth(40)
        self.compress_quality_label.setStyleSheet("font-weight: bold;")
        quality_layout.addWidget(self.compress_quality_label)
        s_layout.addLayout(quality_layout)

        # 快速設定按鈕
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("快速設定:"))

        btn_high = QPushButton("高品質 (90)")
        btn_high.setProperty("secondary", True)
        btn_high.clicked.connect(lambda: self.compress_quality_slider.setValue(90))
        preset_layout.addWidget(btn_high)

        btn_balanced = QPushButton("平衡 (75)")
        btn_balanced.setProperty("secondary", True)
        btn_balanced.clicked.connect(lambda: self.compress_quality_slider.setValue(75))
        preset_layout.addWidget(btn_balanced)

        btn_small = QPushButton("小檔案 (60)")
        btn_small.setProperty("secondary", True)
        btn_small.clicked.connect(lambda: self.compress_quality_slider.setValue(60))
        preset_layout.addWidget(btn_small)

        preset_layout.addStretch()
        s_layout.addLayout(preset_layout)

        # 輸出格式
        fmt_layout = QHBoxLayout()
        fmt_layout.addWidget(QLabel("輸出格式:"))
        self.compress_format = QComboBox()
        self.compress_format.addItems(['jpg', 'png', 'webp'])
        self.compress_format.currentTextChanged.connect(
            lambda text: self._on_combo_pref_changed('compression.output_format', text)
        )
        fmt_layout.addWidget(self.compress_format)
        fmt_layout.addStretch()
        s_layout.addLayout(fmt_layout)

        # 輸出資料夾
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("輸出資料夾:"))
        self.compress_output_folder = QLineEdit("compressed_images")
        self.compress_output_folder.editingFinished.connect(
            lambda: self._on_text_pref_changed(self.compress_output_folder, 'compression.output_folder')
        )
        folder_layout.addWidget(self.compress_output_folder)
        btn_browse = QPushButton("📂 瀏覽")
        btn_browse.setProperty("secondary", True)
        btn_browse.clicked.connect(self._browse_compress_folder)
        folder_layout.addWidget(btn_browse)
        s_layout.addLayout(folder_layout)

        settings.setLayout(s_layout)
        layout.addWidget(settings)

        # 壓縮統計
        self.compress_stats_label = QLabel("")
        self.compress_stats_label.setStyleSheet("color: #64748B; font-size: 9pt;")
        layout.addWidget(self.compress_stats_label)

        # 進度顯示
        self.compress_progress_widget = QWidget()
        compress_progress_layout = QVBoxLayout(self.compress_progress_widget)
        compress_progress_layout.setContentsMargins(0, 0, 0, 0)

        self.compress_status_label = QLabel("就緒")
        self.compress_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        compress_progress_layout.addWidget(self.compress_status_label)

        self.compress_progress = QProgressBar()
        self.compress_progress.setTextVisible(True)
        compress_progress_layout.addWidget(self.compress_progress)

        self.compress_time_label = QLabel("")
        self.compress_time_label.setStyleSheet("color: #64748B; font-size: 9pt;")
        compress_progress_layout.addWidget(self.compress_time_label)

        self.compress_progress_widget.setVisible(False)
        layout.addWidget(self.compress_progress_widget)

        # 按鈕
        btn_layout = QHBoxLayout()
        self.btn_compress = QPushButton("🗜️ 開始壓縮")
        self.btn_compress.clicked.connect(self._start_compression)
        self.btn_compress.setMinimumHeight(44)
        btn_layout.addWidget(self.btn_compress)

        self.btn_cancel_compress = QPushButton("❌ 取消")
        self.btn_cancel_compress.setProperty("secondary", True)
        self.btn_cancel_compress.clicked.connect(self._cancel_compression)
        self.btn_cancel_compress.setMinimumHeight(44)
        self.btn_cancel_compress.setVisible(False)
        btn_layout.addWidget(self.btn_cancel_compress)

        layout.addLayout(btn_layout)

        layout.addStretch()
        self.media_tabs.addTab(tab, "🗜️ 圖片壓縮")

    def _create_word_pdf_tab(self):
        """Word/PDF 轉換分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Word 轉 PDF
        word2pdf = self._create_group_box("📝 Word 轉 PDF")
        w2p_layout = QVBoxLayout()
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Word 文件:"))
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("選擇 .docx 文件...")
        input_layout.addWidget(self.word_input)
        btn = QPushButton("📂 瀏覽")
        btn.setProperty("secondary", True)
        btn.clicked.connect(self._browse_word)
        input_layout.addWidget(btn)
        w2p_layout.addLayout(input_layout)
        
        btn_convert = QPushButton("📄 轉換為 PDF")
        btn_convert.clicked.connect(self._word_to_pdf)
        btn_convert.setMinimumHeight(44)
        w2p_layout.addWidget(btn_convert)
        
        word2pdf.setLayout(w2p_layout)
        layout.addWidget(word2pdf)
        
        # PDF 轉 Word
        pdf2word = self._create_group_box("📄 PDF 轉 Word")
        p2w_layout = QVBoxLayout()
        
        input_layout2 = QHBoxLayout()
        input_layout2.addWidget(QLabel("PDF 文件:"))
        self.pdf_input = QLineEdit()
        self.pdf_input.setPlaceholderText("選擇 .pdf 文件...")
        input_layout2.addWidget(self.pdf_input)
        btn2 = QPushButton("📂 瀏覽")
        btn2.setProperty("secondary", True)
        btn2.clicked.connect(self._browse_pdf)
        input_layout2.addWidget(btn2)
        p2w_layout.addLayout(input_layout2)
        
        btn_convert2 = QPushButton("📝 轉換為 Word")
        btn_convert2.clicked.connect(self._pdf_to_word)
        btn_convert2.setMinimumHeight(44)
        p2w_layout.addWidget(btn_convert2)
        
        pdf2word.setLayout(p2w_layout)
        layout.addWidget(pdf2word)
        
        layout.addStretch()
        self.doc_tabs.addTab(tab, "🔄 格式轉換")

    def _create_markdown_tab(self):
        """Markdown 工具分頁 - 支援多種轉換"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        
        # === 區塊 1: Markdown 輸出轉換 ===
        md_out_group = self._create_group_box("📝 Markdown → 其他格式")
        md_out_layout = QVBoxLayout()
        
        # 輸入檔案
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Markdown 文件:"))
        self.md_input = QLineEdit()
        self.md_input.setPlaceholderText("選擇 .md 文件...")
        input_layout.addWidget(self.md_input)
        
        btn_browse = QPushButton("📂 瀏覽")
        btn_browse.setProperty("secondary", True)
        btn_browse.clicked.connect(self._browse_markdown)
        input_layout.addWidget(btn_browse)
        md_out_layout.addLayout(input_layout)
        
        # 輸出格式選擇
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("輸出格式:"))
        
        from PyQt5.QtWidgets import QButtonGroup, QRadioButton
        
        self.md_output_format_group = QButtonGroup(self)
        
        self.radio_md_to_docx = QRadioButton("Word (.docx)")
        self.radio_md_to_docx.setChecked(True)
        self.md_output_format_group.addButton(self.radio_md_to_docx, 0)
        format_layout.addWidget(self.radio_md_to_docx)
        
        self.radio_md_to_pdf = QRadioButton("PDF (.pdf)")
        self.md_output_format_group.addButton(self.radio_md_to_pdf, 1)
        format_layout.addWidget(self.radio_md_to_pdf)
        
        format_layout.addStretch()
        md_out_layout.addLayout(format_layout)
        
        # 輸出路徑
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("輸出路徑:"))
        self.docx_output = QLineEdit()
        self.docx_output.setPlaceholderText("轉換後的文件路徑...")
        out_layout.addWidget(self.docx_output)
        
        btn_out = QPushButton("📂 瀏覽")
        btn_out.setProperty("secondary", True)
        btn_out.clicked.connect(self._browse_md_output)
        out_layout.addWidget(btn_out)
        md_out_layout.addLayout(out_layout)
        
        # 轉換按鈕
        btn_convert_md = QPushButton("✨ 開始轉換")
        btn_convert_md.clicked.connect(self._convert_md_to_other)
        btn_convert_md.setMinimumHeight(40)
        md_out_layout.addWidget(btn_convert_md)
        
        md_out_group.setLayout(md_out_layout)
        layout.addWidget(md_out_group)
        
        # === 區塊 2: 反向轉換 (DOCX/PDF → Markdown) ===
        reverse_group = self._create_group_box("🔄 其他格式 → Markdown")
        reverse_layout = QVBoxLayout()
        
        # 輸入檔案
        rev_input_layout = QHBoxLayout()
        rev_input_layout.addWidget(QLabel("來源文件:"))
        self.reverse_md_input = QLineEdit()
        self.reverse_md_input.setPlaceholderText("選擇 .docx 或 .pdf 文件...")
        rev_input_layout.addWidget(self.reverse_md_input)
        
        btn_rev_browse = QPushButton("📂 瀏覽")
        btn_rev_browse.setProperty("secondary", True)
        btn_rev_browse.clicked.connect(self._browse_reverse_input)
        rev_input_layout.addWidget(btn_rev_browse)
        reverse_layout.addLayout(rev_input_layout)
        
        # 輸出路徑
        rev_out_layout = QHBoxLayout()
        rev_out_layout.addWidget(QLabel("輸出 Markdown:"))
        self.reverse_md_output = QLineEdit()
        self.reverse_md_output.setPlaceholderText("轉換後的 .md 文件路徑...")
        rev_out_layout.addWidget(self.reverse_md_output)
        
        btn_rev_out = QPushButton("📂 瀏覽")
        btn_rev_out.setProperty("secondary", True)
        btn_rev_out.clicked.connect(self._browse_reverse_output)
        rev_out_layout.addWidget(btn_rev_out)
        reverse_layout.addLayout(rev_out_layout)
        
        # 轉換按鈕
        btn_reverse = QPushButton("🔄 轉換為 Markdown")
        btn_reverse.clicked.connect(self._convert_to_markdown)
        btn_reverse.setMinimumHeight(40)
        reverse_layout.addWidget(btn_reverse)
        
        reverse_group.setLayout(reverse_layout)
        layout.addWidget(reverse_group)
        
        # 進度顯示
        self.md_progress_widget = QWidget()
        md_progress_layout = QVBoxLayout(self.md_progress_widget)
        md_progress_layout.setContentsMargins(0, 0, 0, 0)

        self.md_status_label = QLabel("就緒")
        self.md_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        md_progress_layout.addWidget(self.md_status_label)

        self.md_progress = QProgressBar()
        self.md_progress.setTextVisible(True)
        md_progress_layout.addWidget(self.md_progress)
        
        self.md_progress_widget.setVisible(False)
        layout.addWidget(self.md_progress_widget)
        
        layout.addStretch()
        self.doc_tabs.addTab(tab, "📝 Markdown 工具")


    def _browse_markdown(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇 Markdown 文件", "", "Markdown 文件 (*.md);;All Files (*)"
        )
        if file_path:
            self.md_input.setText(file_path)
            # 自動設定輸出路徑
            base_name = os.path.splitext(file_path)[0]
            self.docx_output.setText(f"{base_name}.docx")

    def _browse_docx_output(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "儲存 Word 文件", self.docx_output.text(), "Word 文件 (*.docx)"
        )
        if file_path:
            self.docx_output.setText(file_path)

    def _convert_md_to_docx(self):
        md_file = self.md_input.text()
        docx_file = self.docx_output.text()
        
        if not md_file or not os.path.exists(md_file):
            QMessageBox.warning(self, "錯誤", "請選擇有效的 Markdown 文件！")
            return
            
        if not docx_file:
            QMessageBox.warning(self, "錯誤", "請設定輸出路徑！")
            return
            
        # 準備 UI
        self.md_progress_widget.setVisible(True)
        self.md_progress.setValue(0)
        self.md_status_label.setText("準備中...")
        self.md_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        
        # 啟動工作執行緒
        self.md_worker = MarkdownConversionWorker(md_file, docx_file)
        self.md_worker.status.connect(self.md_status_label.setText)
        self.md_worker.progress.connect(self.md_progress.setValue)
        self.md_worker.finished.connect(self._on_md_conversion_finished)
        self.md_worker.start()

    def _on_md_conversion_finished(self, success, message):
        self.md_progress_widget.setVisible(False)
        if success:
            QMessageBox.information(self, "成功", message)
            self.statusBar().showMessage("✅ 轉換完成", 5000)
        else:
            QMessageBox.critical(self, "錯誤", message)
            self.md_status_label.setText("轉換失敗")
            self.md_status_label.setStyleSheet("color: #EF4444; font-size: 10pt;")
            self.md_progress_widget.setVisible(True)

    def _browse_md_output(self):
        """瀏覽 Markdown 輸出路徑"""
        format_id = self.md_output_format_group.checkedId()
        if format_id == 0:  # Word
            file_filter = "Word 文件 (*.docx)"
            default_ext = ".docx"
        else:  # PDF
            file_filter = "PDF 文件 (*.pdf)"
            default_ext = ".pdf"
        
        # 根據輸入自動建議輸出路徑
        current_path = self.docx_output.text()
        if not current_path and self.md_input.text():
            base_name = os.path.splitext(self.md_input.text())[0]
            current_path = f"{base_name}{default_ext}"
        
        file_path, _ = QFileDialog.getSaveFileName(self, "儲存文件", current_path, file_filter)
        if file_path:
            self.docx_output.setText(file_path)

    def _browse_reverse_input(self):
        """瀏覽反向轉換的來源文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇來源文件", "", "Word/PDF 文件 (*.docx *.pdf);;Word 文件 (*.docx);;PDF 文件 (*.pdf);;All Files (*)"
        )
        if file_path:
            self.reverse_md_input.setText(file_path)
            # 自動設定輸出路徑
            base_name = os.path.splitext(file_path)[0]
            self.reverse_md_output.setText(f"{base_name}.md")

    def _browse_reverse_output(self):
        """瀏覽反向轉換的輸出路徑"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "儲存 Markdown 文件", self.reverse_md_output.text(), "Markdown 文件 (*.md)"
        )
        if file_path:
            self.reverse_md_output.setText(file_path)

    def _convert_md_to_other(self):
        """轉換 Markdown 到其他格式"""
        md_file = self.md_input.text()
        output_file = self.docx_output.text()
        
        if not md_file or not os.path.exists(md_file):
            self.show_warning("請選擇有效的 Markdown 文件！")
            return
            
        if not output_file:
            self.show_warning("請設定輸出路徑！")
            return
        
        # 判斷輸出格式
        format_id = self.md_output_format_group.checkedId()
        if format_id == 0:
            mode = 'md_to_docx'
        else:
            mode = 'md_to_pdf'
        
        # 準備 UI
        self.md_progress_widget.setVisible(True)
        self.md_progress.setValue(0)
        self.md_status_label.setText("準備中...")
        self.md_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        
        # 啟動工作執行緒
        self.md_tools_worker = MarkdownToolsWorker(mode, md_file, output_file)
        self.md_tools_worker.status.connect(self.md_status_label.setText)
        self.md_tools_worker.progress.connect(self.md_progress.setValue)
        self.md_tools_worker.finished.connect(self._on_md_conversion_finished)
        self.md_tools_worker.start()

    def _convert_to_markdown(self):
        """轉換其他格式到 Markdown"""
        input_file = self.reverse_md_input.text()
        output_file = self.reverse_md_output.text()
        
        if not input_file or not os.path.exists(input_file):
            self.show_warning("請選擇有效的來源文件！")
            return
            
        if not output_file:
            self.show_warning("請設定輸出路徑！")
            return
        
        # 判斷輸入格式
        ext = os.path.splitext(input_file)[1].lower()
        if ext == '.docx':
            mode = 'docx_to_md'
        elif ext == '.pdf':
            mode = 'pdf_to_md'
        else:
            self.show_warning(f"不支援的文件格式：{ext}")
            return
        
        # 準備 UI
        self.md_progress_widget.setVisible(True)
        self.md_progress.setValue(0)
        self.md_status_label.setText("準備中...")
        self.md_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        
        # 啟動工作執行緒
        self.md_tools_worker = MarkdownToolsWorker(mode, input_file, output_file)
        self.md_tools_worker.status.connect(self.md_status_label.setText)
        self.md_tools_worker.progress.connect(self.md_progress.setValue)
        self.md_tools_worker.finished.connect(self._on_md_conversion_finished)
        self.md_tools_worker.start()

    def _create_pdf_merge_tab(self):

        """PDF 合併分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        group = self._create_group_box("📁 選擇 PDF 文件")
        file_layout = QHBoxLayout()

        # 左側：PDF 列表
        list_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        btn = QPushButton("📂 選擇 PDF")
        btn.clicked.connect(self._select_pdfs)
        btn.setMinimumHeight(40)
        btn_layout.addWidget(btn)
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)

        merge_exts = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff']
        self.pdf_list = DragDropListWidget(file_extensions=merge_exts)
        self.pdf_list.drop_completed.connect(self._on_pdf_dropped)
        list_layout.addWidget(self.pdf_list)

        file_layout.addLayout(list_layout, 4)

        # 右側：控制按鈕
        control_layout = QVBoxLayout()

        btn_move_up = QPushButton("⬆️ 上移")
        btn_move_up.clicked.connect(self._pdf_move_up)
        btn_move_up.setProperty("secondary", True)
        control_layout.addWidget(btn_move_up)

        btn_move_down = QPushButton("⬇️ 下移")
        btn_move_down.clicked.connect(self._pdf_move_down)
        btn_move_down.setProperty("secondary", True)
        control_layout.addWidget(btn_move_down)

        control_layout.addSpacing(10)

        btn_remove = QPushButton("🗑️ 刪除")
        btn_remove.clicked.connect(self._pdf_remove_selected)
        btn_remove.setProperty("secondary", True)
        control_layout.addWidget(btn_remove)

        btn_clear = QPushButton("🧹 清空")
        btn_clear.clicked.connect(self._pdf_clear_all)
        btn_clear.setProperty("secondary", True)
        control_layout.addWidget(btn_clear)

        control_layout.addStretch()
        file_layout.addLayout(control_layout, 1)

        group.setLayout(file_layout)
        layout.addWidget(group)

        # 合併選項
        options_group = self._create_group_box("⚙️ 合併選項")
        options_layout = QVBoxLayout()

        from PyQt5.QtWidgets import QCheckBox

        self.pdf_add_toc = QCheckBox("添加目錄頁面（列出所有 PDF 檔名）")
        self.pdf_add_toc.setChecked(False)
        options_layout.addWidget(self.pdf_add_toc)

        self.pdf_add_page_numbers = QCheckBox("添加頁碼（底部居中）")
        self.pdf_add_page_numbers.setChecked(False)
        options_layout.addWidget(self.pdf_add_page_numbers)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        btn = QPushButton("🔗 合併 PDF")
        btn.clicked.connect(self._merge_pdfs)
        btn.setMinimumHeight(44)
        layout.addWidget(btn)

        layout.addStretch()
        self.doc_tabs.addTab(tab, "🔗 PDF 合併")

    def _create_pdf_watermark_tab(self):
        """PDF 浮水印分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 檔案選擇
        file_group = self._create_group_box("📄 選擇 PDF 文件")
        file_layout = QVBoxLayout()

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("PDF 文件:"))
        self.watermark_pdf_input = QLineEdit()
        self.watermark_pdf_input.setPlaceholderText("選擇要添加浮水印的 PDF 文件...")
        input_layout.addWidget(self.watermark_pdf_input)

        btn_browse = QPushButton("📂 瀏覽")
        btn_browse.setProperty("secondary", True)
        btn_browse.clicked.connect(self._browse_watermark_pdf)
        input_layout.addWidget(btn_browse)
        file_layout.addLayout(input_layout)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # 浮水印類型選擇
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup
        type_group = self._create_group_box("🏷️ 浮水印類型")
        type_layout = QVBoxLayout()

        self.watermark_type_group = QButtonGroup()
        self.watermark_text_radio = QRadioButton("文字浮水印")
        self.watermark_image_radio = QRadioButton("圖片浮水印")
        self.watermark_text_radio.setChecked(True)

        self.watermark_type_group.addButton(self.watermark_text_radio)
        self.watermark_type_group.addButton(self.watermark_image_radio)

        self.watermark_text_radio.toggled.connect(self._toggle_watermark_type)

        type_layout.addWidget(self.watermark_text_radio)
        type_layout.addWidget(self.watermark_image_radio)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # 文字浮水印設定
        self.text_watermark_group = self._create_group_box("📝 文字浮水印設定")
        text_layout = QVBoxLayout()

        # 浮水印文字
        text_input_layout = QHBoxLayout()
        text_input_layout.addWidget(QLabel("浮水印文字:"))
        self.watermark_text_input = QLineEdit("© 2025 Confidential")
        self.watermark_text_input.setPlaceholderText("輸入浮水印文字...")
        text_input_layout.addWidget(self.watermark_text_input)
        text_layout.addLayout(text_input_layout)

        # 字體大小
        from PyQt5.QtWidgets import QSpinBox, QSlider
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("字體大小:"))
        self.watermark_font_size = QSpinBox()
        self.watermark_font_size.setRange(10, 200)
        self.watermark_font_size.setValue(40)
        size_layout.addWidget(self.watermark_font_size)
        size_layout.addStretch()
        text_layout.addLayout(size_layout)

        # 旋轉角度
        rotation_layout = QHBoxLayout()
        rotation_layout.addWidget(QLabel("旋轉角度:"))
        self.watermark_rotation = QSpinBox()
        self.watermark_rotation.setRange(-180, 180)
        self.watermark_rotation.setValue(45)
        self.watermark_rotation.setSuffix("°")
        rotation_layout.addWidget(self.watermark_rotation)
        rotation_layout.addStretch()
        text_layout.addLayout(rotation_layout)

        self.text_watermark_group.setLayout(text_layout)
        layout.addWidget(self.text_watermark_group)

        # 圖片浮水印設定
        self.image_watermark_group = self._create_group_box("🖼️ 圖片浮水印設定")
        image_layout = QVBoxLayout()

        # 選擇浮水印圖片
        image_input_layout = QHBoxLayout()
        image_input_layout.addWidget(QLabel("浮水印圖片:"))
        self.watermark_image_input = QLineEdit()
        self.watermark_image_input.setPlaceholderText("選擇浮水印圖片（PNG 格式支援透明背景）...")
        image_input_layout.addWidget(self.watermark_image_input)

        btn_browse_img = QPushButton("📂 瀏覽")
        btn_browse_img.setProperty("secondary", True)
        btn_browse_img.clicked.connect(self._browse_watermark_image)
        image_input_layout.addWidget(btn_browse_img)
        image_layout.addLayout(image_input_layout)

        # 縮放比例
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("縮放比例:"))
        self.watermark_scale_slider = QSlider(Qt.Horizontal)
        self.watermark_scale_slider.setRange(5, 50)
        self.watermark_scale_slider.setValue(20)
        self.watermark_scale_slider.valueChanged.connect(self._update_scale_label)
        scale_layout.addWidget(self.watermark_scale_slider)
        self.watermark_scale_label = QLabel("20%")
        self.watermark_scale_label.setFixedWidth(50)
        scale_layout.addWidget(self.watermark_scale_label)
        image_layout.addLayout(scale_layout)

        self.image_watermark_group.setLayout(image_layout)
        self.image_watermark_group.setVisible(False)
        layout.addWidget(self.image_watermark_group)

        # 通用設定
        common_group = self._create_group_box("⚙️ 通用設定")
        common_layout = QVBoxLayout()

        # 位置選擇
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("浮水印位置:"))
        self.watermark_position = QComboBox()
        self.watermark_position.addItems([
            "正中央", "左上角", "右上角", "左下角", "右下角"
        ])
        position_layout.addWidget(self.watermark_position)
        position_layout.addStretch()
        common_layout.addLayout(position_layout)

        # 透明度
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.watermark_opacity_slider = QSlider(Qt.Horizontal)
        self.watermark_opacity_slider.setRange(10, 100)
        self.watermark_opacity_slider.setValue(30)
        self.watermark_opacity_slider.valueChanged.connect(self._update_opacity_label)
        opacity_layout.addWidget(self.watermark_opacity_slider)
        self.watermark_opacity_label = QLabel("30%")
        self.watermark_opacity_label.setFixedWidth(50)
        opacity_layout.addWidget(self.watermark_opacity_label)
        common_layout.addLayout(opacity_layout)

        # 邊距調整
        from PyQt5.QtWidgets import QSpinBox
        margin_layout = QHBoxLayout()
        margin_layout.addWidget(QLabel("邊距 (px):"))
        self.watermark_margin = QSpinBox()
        self.watermark_margin.setRange(0, 100)
        self.watermark_margin.setValue(10)
        self.watermark_margin.setToolTip("浮水印到頁面邊緣的距離（像素）")
        margin_layout.addWidget(self.watermark_margin)
        margin_layout.addStretch()
        common_layout.addLayout(margin_layout)

        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        # 按鈕
        btn = QPushButton("✨ 添加浮水印")
        btn.clicked.connect(self._add_pdf_watermark)
        btn.setMinimumHeight(44)
        layout.addWidget(btn)

        layout.addStretch()
        self.doc_tabs.addTab(tab, "🏷️ PDF 浮水印")

    def _create_group_box(self, title):
        """創建群組框"""
        group = QGroupBox(title)
        self._group_boxes.append(group)
        group.setStyleSheet(ModernStyle.get_card_style(self.current_theme))
        return group

    def _remember_folder(self, config_key, file_path):
        """記住最後使用的資料夾並加入最近使用記錄"""
        if not file_path:
            return
        folder = os.path.dirname(file_path)
        self.config.set(config_key, folder)
        self.config.add_recent_file(file_path)

    def _toggle_theme(self):
        """切換主題"""
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.theme_btn.setText("☀️ 淺色模式" if self.current_theme == "dark" else "🌙 深色模式")
        self._apply_theme(self.current_theme)
        # 保存主題設定
        self.config.set('theme', self.current_theme)

    def _apply_theme(self, theme):
        """套用主題"""
        stylesheet = ModernStyle.get_dark_stylesheet() if theme == "dark" else ModernStyle.get_light_stylesheet()
        self.setStyleSheet(stylesheet)
        card_style = ModernStyle.get_card_style(theme)
        for group in self._group_boxes:
            group.setStyleSheet(card_style)

    # === 配置管理方法 ===
    def _restore_window_geometry(self):
        """從配置恢復視窗大小和位置"""
        width = self.config.get('window.width', 1200)
        height = self.config.get('window.height', 800)
        self.resize(width, height)

        x = self.config.get('window.x')
        y = self.config.get('window.y')
        if x is not None and y is not None:
            self.move(x, y)

        if self.config.get('window.maximized', False):
            self.showMaximized()

    def _save_window_geometry(self):
        """保存視窗大小與位置"""
        self.config.set('window.width', self.width(), auto_save=False)
        self.config.set('window.height', self.height(), auto_save=False)
        self.config.set('window.x', self.x(), auto_save=False)
        self.config.set('window.y', self.y(), auto_save=False)
        self.config.set('window.maximized', self.isMaximized(), auto_save=False)
        self._request_config_save()

    def _load_parameters(self):
        """從設定檔載入參數"""
        self._loading_preferences = True

        # 圖片拼貼參數
        self.edit_cols.setText(str(self.config.get('image.grid_cols', Config.DEFAULT_GRID_COLS)))
        self.edit_rows.setText(str(self.config.get('image.grid_rows', Config.DEFAULT_GRID_ROWS)))
        self.edit_duration.setText(str(self.config.get('image.gif_duration', Config.DEFAULT_GIF_DURATION)))

        strategy = self.config.get('image.resize_strategy', Config.RESIZE_STRATEGY_DIRECT)
        index = self.combo_strategy.findText(strategy)
        if index >= 0:
            self.combo_strategy.setCurrentIndex(index)

        # 影片輸出參數
        self.edit_output_video.setText(self.config.get('video.output_name', 'merged_video.mp4'))

        # 圖片轉檔參數
        self.edit_output_folder.setText(self.config.get('convert.output_folder', 'converted_images'))

        fmt = self.config.get('convert.output_format', 'PNG')
        index = self.combo_output_format.findText(fmt)
        if index >= 0:
            self.combo_output_format.setCurrentIndex(index)

        # 圖片壓縮參數
        self.compress_output_folder.setText(self.config.get('compression.output_folder', 'compressed_images'))
        compress_fmt = self.config.get('compression.output_format', 'jpg')
        index = self.compress_format.findText(compress_fmt, Qt.MatchFixedString)
        if index >= 0:
            self.compress_format.setCurrentIndex(index)

        self._loading_preferences = False

    def _save_parameters(self):
        """保存參數設置"""
        try:
            self._update_config_value('image.grid_cols', int(self.edit_cols.text()))
            self._update_config_value('image.grid_rows', int(self.edit_rows.text()))
            self._update_config_value('image.gif_duration', int(self.edit_duration.text()))
            self._update_config_value('image.resize_strategy', self.combo_strategy.currentText())
            self._update_config_value('video.output_name', self.edit_output_video.text())
            self._update_config_value('convert.output_folder', self.edit_output_folder.text())
            self._update_config_value('convert.output_format', self.combo_output_format.currentText())
        except Exception:
            pass

    def _request_config_save(self):
        """Queue a debounced config save to disk."""
        self._save_timer.start(300)

    def _update_config_value(self, key, value):
        """Update config and trigger debounced save."""
        self.config.set(key, value, auto_save=False)
        self._request_config_save()

    def _on_numeric_pref_changed(self, widget, key, minimum, default):
        if self._loading_preferences:
            return
        try:
            value = int(widget.text())
        except ValueError:
            value = default
        if value < minimum:
            value = minimum
        widget.setText(str(value))
        self._update_config_value(key, value)
        self._show_pref_status("Preferences updated")

    def _on_text_pref_changed(self, widget, key):
        if self._loading_preferences:
            return
        value = widget.text().strip()
        self._update_config_value(key, value)
        self._show_pref_status("Preferences updated")

    def _on_combo_pref_changed(self, key, value):
        if self._loading_preferences:
            return
        self._update_config_value(key, value)
        self._show_pref_status("Preferences updated")

    def _manual_save_preferences(self):
        if self.config.save_config():
            self._show_pref_status("Preferences saved")

    def _reset_preferences(self):
        reply = QMessageBox.question(self, "重設設定", "確定要恢復所有設定為預設值嗎？", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.config.reset_to_default()
        self.current_theme = self.config.get('theme', 'light')
        self._apply_theme(self.current_theme)
        self._load_parameters()
        self._show_pref_status("已恢復預設設定")

    def _show_pref_status(self, message):
        self.statusBar().showMessage(message, 4000)

    def _remember_folder(self, key, file_path):
        if not file_path:
            return
        folder = os.path.dirname(file_path)
        if folder:
            self._update_config_value(key, folder)

    def closeEvent(self, event):
        """關閉視窗時保存配置"""
        self._save_window_geometry()
        self._save_parameters()
        self.config.save_config()
        event.accept()

    # === 輔助方法 ===
    def _format_time(self, seconds):
        """格式化時間顯示"""
        if seconds < 60:
            return f"{int(seconds)} 秒"
        elif seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins} 分 {secs} 秒"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours} 小時 {mins} 分"

    def _update_time_label(self, label, progress):
        """更新時間標籤"""
        if self.operation_start_time and progress > 0:
            elapsed = time.time() - self.operation_start_time
            if progress < 100:
                estimated_total = elapsed / (progress / 100)
                remaining = estimated_total - elapsed
                label.setText(
                    f"已用時間: {self._format_time(elapsed)} | "
                    f"預估剩餘: {self._format_time(remaining)}"
                )
            else:
                label.setText(f"完成！總用時: {self._format_time(elapsed)}")

    # === 圖片影像處理方法 ===
    def _show_image_viewer(self, path):
        dialog = ImageViewerDialog(path, self)
        dialog.exec_()

    def _update_image_stats(self):
        count = len(self.image_preview.get_files())
        self.statusBar().showMessage(f'Images ready: {count} files selected')

    def _on_image_ingest_completed(self, source, added, duplicates, skipped):
        source_label = 'Drag' if source == 'drag-drop' else 'Select'
        self._show_ingest_feedback('Image queue', source_label, added, duplicates, skipped)

    def _on_video_dropped(self, files, skipped):
        self._handle_list_drop(self.video_files_list, 'Video queue', files, skipped)

    def _on_convert_dropped(self, files, skipped):
        self._handle_list_drop(self.convert_list, 'Convert queue', files, skipped)

    def _on_pdf_dropped(self, files, skipped):
        self._handle_list_drop(self.pdf_list, 'PDF queue', files, skipped)

    def _handle_list_drop(self, widget, label, files, skipped, source_label="Drag"):
        added = []
        duplicates = []
        skipped_all = list(skipped or [])
        if files:
            added, duplicates, skipped_extra = widget.add_files(files)
            skipped_all.extend(skipped_extra)
        self._show_ingest_feedback(label, source_label, len(added), len(duplicates), skipped_all)

    def _show_ingest_feedback(self, target, source_label, added_count, duplicate_count, skipped_files):
        if not (added_count or duplicate_count or skipped_files):
            return

        parts = []
        if added_count:
            parts.append(f'Added {added_count}')
        if duplicate_count:
            parts.append(f'Duplicates {duplicate_count}')
        if skipped_files:
            sample_names = [os.path.basename(path) or path for path in skipped_files[:3]]
            sample_text = ', '.join(sample_names)
            if len(skipped_files) > 3:
                sample_text += ' ...'
            parts.append(f'Skipped {len(skipped_files)} unsupported: {sample_text}')

        message = f"{target} [{source_label}]: " + '; '.join(parts)
        self.statusBar().showMessage(message, 6000)

    def _prompt_pdf_password(self, file_path, invalid=False):
        """顯示密碼輸入對話框，回傳輸入值或 None。"""
        base = os.path.basename(file_path)
        prompt = f"{base} 需要輸入密碼"
        if invalid:
            prompt += "\n密碼不正確，請再試一次。"
        password, ok = QInputDialog.getText(
            self,
            "輸入 PDF 密碼",
            prompt,
            QLineEdit.Password
        )
        if ok and password:
            return password
        return None

    def _unlock_pdf_with_prompt(self, pdf_path):
        """確保 PDF 可供讀取，如需密碼則提示使用者。"""
        cache_key = os.path.abspath(pdf_path)
        password = self._pdf_password_cache.get(cache_key)
        while True:
            try:
                unlocked_path, temp_path = ensure_unlocked_pdf(pdf_path, password=password)
                if password:
                    self._pdf_password_cache[cache_key] = password
                return unlocked_path, temp_path
            except PasswordRequiredError:
                password = self._prompt_pdf_password(pdf_path, invalid=False)
                if password is None:
                    raise PasswordPromptCancelled()
            except WrongPasswordProvided:
                password = self._prompt_pdf_password(pdf_path, invalid=True)
                if password is None:
                    raise PasswordPromptCancelled()

    def _execute_pdf_operation(self, pdf_path, operation):
        """執行需要 PDF 密碼的操作，必要時提示使用者。"""
        cache_key = os.path.abspath(pdf_path)
        password = self._pdf_password_cache.get(cache_key)
        while True:
            try:
                result = operation(password)
                if password:
                    self._pdf_password_cache[cache_key] = password
                return result
            except PasswordRequiredError:
                password = self._prompt_pdf_password(pdf_path, invalid=False)
                if password is None:
                    raise PasswordPromptCancelled()
            except WrongPasswordProvided:
                password = self._prompt_pdf_password(pdf_path, invalid=True)
                if password is None:
                    raise PasswordPromptCancelled()

    def _create_temp_pdf_path(self):
        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        return temp_path

    def _prepare_merge_sources(self, files):
        """對合併來源進行預處理（解密、轉檔）。"""
        prepared = []
        temp_files = []
        summary = []

        for file_path in files:
            file_type = detect_file_type(file_path)
            display_name = os.path.basename(file_path)
            try:
                if file_type == 'pdf':
                    unlocked_path, temp_path = self._unlock_pdf_with_prompt(file_path)
                    prepared.append(unlocked_path)
                    if temp_path:
                        temp_files.append(temp_path)
                        summary.append(f"{display_name}：已解密並加入")
                    else:
                        summary.append(f"{display_name}：已加入 PDF")
                elif file_type == 'word':
                    temp_pdf = self._create_temp_pdf_path()
                    if convert_word_to_pdf(file_path, temp_pdf):
                        prepared.append(temp_pdf)
                        temp_files.append(temp_pdf)
                        summary.append(f"{display_name}：Word 轉 PDF 成功")
                    else:
                        os.remove(temp_pdf)
                        summary.append(f"{display_name}：Word 轉 PDF 失敗，已略過")
                elif file_type == 'image':
                    temp_pdf = self._create_temp_pdf_path()
                    if convert_image_to_pdf(file_path, temp_pdf):
                        prepared.append(temp_pdf)
                        temp_files.append(temp_pdf)
                        summary.append(f"{display_name}：圖片轉 PDF 成功")
                    else:
                        os.remove(temp_pdf)
                        summary.append(f"{display_name}：圖片轉 PDF 失敗，已略過")
                else:
                    summary.append(f"{display_name}：不支援的檔案格式，已略過")
            except PasswordPromptCancelled:
                summary.append(f"{display_name}：使用者取消輸入密碼，已略過")
            except PasswordRequiredError:
                summary.append(f"{display_name}：需要密碼但未輸入，已略過")
            except WrongPasswordProvided:
                summary.append(f"{display_name}：密碼多次錯誤，已略過")
            except Exception as exc:
                summary.append(f"{display_name}：處理失敗（{exc}），已略過")

        return prepared, temp_files, summary

    def _show_merge_summary(self, summary_lines):
        if not summary_lines:
            return
        message = "處理摘要：\n" + "\n".join(f"- {line}" for line in summary_lines)
        QMessageBox.information(self, "PDF 合併摘要", message)

    def _add_watermark(self):
        files = self.image_preview.get_files()
        if not files:
            self.show_warning("請先選擇圖片")
            return
        if add_watermark(files, self):
            self.show_info("浮水印添加完成！")

    def _set_ui_enabled(self, enabled):
        """啟用/禁用 UI"""
        self.category_tabs.setEnabled(enabled)
        # 確保按鈕狀態正確
        if hasattr(self, 'btn_start_compress_video'):
            self.btn_start_compress_video.setEnabled(enabled)

    def _update_progress(self, value):
        """通用進度更新"""
        # 嘗試更新影片壓縮的進度條
        if hasattr(self, 'compress_progress') and self.compress_progress.isVisible():
            self.compress_progress.setValue(value)

    def _update_status(self, message):
        """通用狀態更新"""
        # 嘗試更新影片壓縮的狀態標籤
        if hasattr(self, 'compress_status_label') and self.compress_status_label.isVisible():
            self.compress_status_label.setText(message) 
        # 也可以顯示在狀態列
        self.statusBar().showMessage(message)

    def _on_worker_finished(self, success, message):
        """通用 Worker 完成回調"""
        if success:
            QMessageBox.information(self, Config.UI_TEXT['success'], message)
        else:
            QMessageBox.critical(self, Config.UI_TEXT['error'], f"操作失敗：\n{message}")

    def select_files_for_list(self, list_widget, filter_str, title="選擇檔案"):
        """通用檔案選擇方法"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            title,
            "",
            f"{filter_str};;All Files (*)"
        )
        if files:
            list_widget.add_files(files)

    def _browse_folder(self, line_edit):
        """通用資料夾瀏覽方法"""
        folder = QFileDialog.getExistingDirectory(self, "選擇資料夾")
        if folder:
            line_edit.setText(folder)

    def select_files(self):
        start_dir = self.config.get('image.last_folder', '')
        files, _ = QFileDialog.getOpenFileNames(self, "選擇圖片", start_dir or "", Config.IMAGE_FILE_FILTER)
        if files:
            self.image_preview.add_files(files, source="manual")
            self._remember_folder('image.last_folder', files[0])

    def select_video_files(self):
        start_dir = self.config.get('video.last_folder', '')
        files, _ = QFileDialog.getOpenFileNames(self, "選擇影片", start_dir or "", Config.VIDEO_FILE_FILTER)
        if files:
            self._handle_list_drop(self.video_files_list, "Video queue", files, [], source_label="Select")
            self._remember_folder('video.last_folder', files[0])

    def select_convert_images(self):
        start_dir = self.config.get('convert.last_folder', '')
        files, _ = QFileDialog.getOpenFileNames(self, "選擇圖片", start_dir or "", Config.IMAGE_FILE_FILTER)
        if files:
            self._handle_list_drop(self.convert_list, "Convert queue", files, [], source_label="Select")
            self._remember_folder('convert.last_folder', files[0])

    def browse_output_folder(self):
        start_dir = self.config.get('convert.output_folder', '')
        folder = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾", start_dir or "")
        if folder:
            self.edit_output_folder.setText(folder)
            self._on_text_pref_changed(self.edit_output_folder, 'convert.output_folder')

    def generate_merged_image(self):
        files = self.image_preview.get_files()
        if not files:
            return None
        try:
            cols = int(self.edit_cols.text())
            rows = int(self.edit_rows.text())
        except:
            return None
        
        images = [Image.open(p) for p in files]
        min_w = min(img.width for img in images)
        min_h = min(img.height for img in images)
        gap = Config.DEFAULT_IMAGE_GAP
        merged_w = cols * min_w + (cols + 1) * gap
        merged_h = rows * min_h + (rows + 1) * gap
        merged = Image.new("RGB", (merged_w, merged_h), Config.DEFAULT_BG_COLOR)
        
        strategy = self.combo_strategy.currentText()
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
        return merged

    def merge_images(self):
        merged = self.generate_merged_image()
        if not merged:
            self.show_warning("請先選擇圖片")
            return
        path, _ = QFileDialog.getSaveFileName(self, "儲存圖片", "", Config.get_save_image_filter())
        if path:
            merged.save(path)
            self.show_info(f"拼接完成！\n{path}")

    def create_gif(self):
        """GIF 建立 - 使用工作執行緒"""
        files = self.image_preview.get_files()
        if not files:
            self.show_warning("請先選擇圖片")
            return
        try:
            duration = int(self.edit_duration.text())
        except:
            duration = Config.DEFAULT_GIF_DURATION

        strategy = self.combo_strategy.currentText()

        # 詢問儲存路徑
        path, _ = QFileDialog.getSaveFileName(self, "儲存 GIF", "", Config.get_save_gif_filter())
        if not path:
            return

        # 初始化工作執行緒
        self.gif_worker = GifCreationWorker(files, path, duration, strategy)
        self.gif_worker.progress.connect(self._on_gif_progress)
        self.gif_worker.status.connect(self._on_gif_status)
        self.gif_worker.finished.connect(self._on_gif_finished)

        # 顯示進度介面
        self.gif_progress_widget.setVisible(True)
        self.gif_progress.setValue(0)
        self.btn_create_gif.setEnabled(False)
        self.btn_cancel_gif.setVisible(True)

        # 開始計時
        self.operation_start_time = time.time()

        # 啟動執行緒
        self.gif_worker.start()

    def _on_gif_progress(self, value):
        """更新 GIF 建立進度"""
        self.gif_progress.setValue(value)
        self._update_time_label(self.gif_time_label, value)

    def _on_gif_status(self, status):
        """更新 GIF 建立狀態"""
        self.gif_status_label.setText(status)

    def _on_gif_finished(self, success, message):
        """GIF 建立完成"""
        self.gif_progress_widget.setVisible(False)
        self.btn_create_gif.setEnabled(True)
        self.btn_cancel_gif.setVisible(False)
        self.operation_start_time = None

        if success:
            self.show_info(message)
        else:
            if "取消" not in message:
                self.show_error(message)
            else:
                self.statusBar().showMessage(f"⚠️ {message}", 3000)

    def _cancel_gif_creation(self):
        """取消 GIF 建立"""
        if self.gif_worker and self.gif_worker.isRunning():
            self.gif_status_label.setText("正在取消操作...")
            self.gif_worker.cancel()
            self.btn_cancel_gif.setEnabled(False)

    def merge_videos(self):
        """影片合併 - 使用工作執行緒"""
        files = self.video_files_list.get_all_files()
        if not files:
            self.show_warning("請先選擇影片")
            return
        output = self.edit_output_video.text()
        if not output:
            self.show_warning("請輸入輸出檔名")
            return

        files = natsorted(files)

        # 初始化工作執行緒
        self.video_worker = VideoMergeWorker(files, output)
        self.video_worker.progress.connect(self._on_video_progress)
        self.video_worker.status.connect(self._on_video_status)
        self.video_worker.finished.connect(self._on_video_finished)

        # 顯示進度介面
        self.video_progress_widget.setVisible(True)
        self.video_progress.setValue(0)
        self.btn_merge_video.setEnabled(False)
        self.btn_cancel_video.setVisible(True)

        # 開始計時
        self.operation_start_time = time.time()

        # 啟動執行緒
        self.video_worker.start()

    def _on_video_progress(self, value):
        """更新影片合併進度"""
        self.video_progress.setValue(value)
        self._update_time_label(self.video_time_label, value)

    def _on_video_status(self, status):
        """更新影片合併狀態"""
        self.video_status_label.setText(status)

    def _on_video_finished(self, success, message):
        """影片合併完成"""
        self.video_progress_widget.setVisible(False)
        self.btn_merge_video.setEnabled(True)
        self.btn_cancel_video.setVisible(False)
        self.operation_start_time = None

        if success:
            self.show_info(message)
        else:
            if "取消" not in message:
                self.show_error(message)
            else:
                self.statusBar().showMessage(f"⚠️ {message}", 3000)

    def _cancel_video_merge(self):
        """取消影片合併"""
        if self.video_worker and self.video_worker.isRunning():
            self.video_status_label.setText("正在取消操作...")
            self.video_worker.cancel()
            self.btn_cancel_video.setEnabled(False)

    def convert_images(self):
        """圖片格式轉換 - 使用工作執行緒"""
        files = self.convert_list.get_all_files()
        if not files:
            self.show_warning("請先選擇圖片")
            return

        fmt = self.combo_output_format.currentText().lower()
        folder = self.edit_output_folder.text()

        # 初始化工作執行緒
        self.convert_worker = ImageConversionWorker(files, fmt, folder)
        self.convert_worker.progress.connect(self._on_convert_progress)
        self.convert_worker.status.connect(self._on_convert_status)
        self.convert_worker.finished.connect(self._on_convert_finished)

        # 顯示進度介面
        self.convert_progress_widget.setVisible(True)
        self.convert_progress.setValue(0)
        self.btn_convert.setEnabled(False)
        self.btn_cancel_convert.setVisible(True)

        # 開始計時
        self.operation_start_time = time.time()

        # 啟動執行緒
        self.convert_worker.start()

    def _on_convert_progress(self, value):
        """更新圖片轉換進度"""
        self.convert_progress.setValue(value)
        self._update_time_label(self.convert_time_label, value)

    def _on_convert_status(self, status):
        """更新圖片轉換狀態"""
        self.convert_status_label.setText(status)

    def _on_convert_finished(self, success, message):
        """圖片轉換完成"""
        self.convert_progress_widget.setVisible(False)
        self.btn_convert.setEnabled(True)
        self.btn_cancel_convert.setVisible(False)
        self.operation_start_time = None

        if success:
            self.show_info(message)
        else:
            if "取消" not in message:
                self.show_error(message)
            else:
                self.statusBar().showMessage(f"⚠️ {message}", 3000)

    def _cancel_conversion(self):
        """取消圖片轉換"""
        if self.convert_worker and self.convert_worker.isRunning():
            self.convert_status_label.setText("正在取消操作...")
            self.convert_worker.cancel()
            self.btn_cancel_convert.setEnabled(False)

    # === 文檔處理方法 ===
    def _browse_word(self):
        start_dir = self.config.get('document.last_word_folder', '')
        file, _ = QFileDialog.getOpenFileName(self, "選擇 Word", start_dir or "", "Word (*.docx *.doc)")
        if file:
            self.word_input.setText(file)
            self._remember_folder('document.last_word_folder', file)

    def _browse_pdf(self):
        start_dir = self.config.get('document.last_pdf_folder', '')
        file, _ = QFileDialog.getOpenFileName(self, "選擇 PDF", start_dir or "", "PDF (*.pdf)")
        if file:
            self.pdf_input.setText(file)
            self._remember_folder('document.last_pdf_folder', file)

    def _word_to_pdf(self):
        word = self.word_input.text()
        if not word or not os.path.exists(word):
            self.show_warning("請選擇有效的 Word 文件")
            return
        pdf, _ = QFileDialog.getSaveFileName(self, "儲存 PDF", "", "PDF (*.pdf)")
        if pdf:
            if convert_word_to_pdf(word, pdf):
                self.show_info(f"轉換成功！\n{pdf}")
            else:
                self.show_error("Word 轉 PDF 失敗")

    def _pdf_to_word(self):
        pdf = self.pdf_input.text()
        if not pdf or not os.path.exists(pdf):
            self.show_warning("請選擇有效的 PDF 文件")
            return
        word, _ = QFileDialog.getSaveFileName(self, "儲存 Word", "", "Word (*.docx)")
        if not word:
            return

        try:
            def action(password):
                return convert_pdf_to_word(pdf, word, password=password)

            if self._execute_pdf_operation(pdf, action):
                self.show_info(f"轉換成功！\n{word}")
            else:
                self.show_error("PDF 轉 Word 失敗")
        except PasswordPromptCancelled:
            self.statusBar().showMessage("已取消輸入密碼", 4000)

    def _select_pdfs(self):
        start_dir = self.config.get('document.last_pdf_folder', '')
        filter_str = "支援檔案 (*.pdf *.doc *.docx *.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff)"
        files, _ = QFileDialog.getOpenFileNames(self, "選擇檔案", start_dir or "", filter_str)
        if files:
            self._handle_list_drop(self.pdf_list, "PDF queue", files, [], source_label="Select")
            self._remember_folder('document.last_pdf_folder', files[0])

    def _pdf_move_up(self):
        """上移選中的 PDF"""
        current_row = self.pdf_list.currentRow()
        if current_row > 0:
            item = self.pdf_list.takeItem(current_row)
            self.pdf_list.insertItem(current_row - 1, item)
            self.pdf_list.setCurrentRow(current_row - 1)

    def _pdf_move_down(self):
        """下移選中的 PDF"""
        current_row = self.pdf_list.currentRow()
        if current_row < self.pdf_list.count() - 1 and current_row >= 0:
            item = self.pdf_list.takeItem(current_row)
            self.pdf_list.insertItem(current_row + 1, item)
            self.pdf_list.setCurrentRow(current_row + 1)

    def _pdf_remove_selected(self):
        """刪除選中的 PDF"""
        current_row = self.pdf_list.currentRow()
        if current_row >= 0:
            self.pdf_list.takeItem(current_row)

    def _pdf_clear_all(self):
        """清空所有 PDF"""
        if self.pdf_list.count() > 0:
            reply = QMessageBox.question(
                self,
                "確認清空",
                "確定要清空所有 PDF 文件嗎？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.pdf_list.clear_all()

    def _merge_pdfs(self):
        files = self.pdf_list.get_all_files()
        if not files:
            self.show_warning("請選擇檔案")
            return
        output, _ = QFileDialog.getSaveFileName(self, "儲存 PDF", "", "PDF (*.pdf)")
        if not output:
            return

        add_toc = self.pdf_add_toc.isChecked()
        add_page_numbers = self.pdf_add_page_numbers.isChecked()

        prepared, temp_files, summary = self._prepare_merge_sources(files)
        if not prepared:
            self._show_merge_summary(summary)
            self.show_warning("沒有可合併的檔案")
            return

        try:
            if merge_pdfs(prepared, output, add_toc=add_toc, add_page_numbers=add_page_numbers):
                self.show_info(f"合併完成！\n{output}")
            else:
                self.show_error("PDF 合併失敗")
        finally:
            for temp_path in temp_files:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

        summary.append(f"輸出檔案：{output}")
        self._show_merge_summary(summary)

    # === PDF 浮水印方法 ===
    def _browse_watermark_pdf(self):
        """選擇要添加浮水印的 PDF 文件"""
        start_dir = self.config.get('pdf.last_folder', '')
        file, _ = QFileDialog.getOpenFileName(
            self, "選擇 PDF 文件", start_dir or "", "PDF 文件 (*.pdf)"
        )
        if file:
            self.watermark_pdf_input.setText(file)
            self._remember_folder('pdf.last_folder', file)

    def _browse_watermark_image(self):
        """選擇浮水印圖片"""
        start_dir = self.config.get('image.last_folder', '')
        file, _ = QFileDialog.getOpenFileName(
            self, "選擇浮水印圖片", start_dir or "",
            "圖片檔案 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file:
            self.watermark_image_input.setText(file)
            self._remember_folder('image.last_folder', file)

    def _toggle_watermark_type(self):
        """切換浮水印類型"""
        is_text = self.watermark_text_radio.isChecked()
        self.text_watermark_group.setVisible(is_text)
        self.image_watermark_group.setVisible(not is_text)

    def _update_opacity_label(self, value):
        """更新透明度標籤"""
        self.watermark_opacity_label.setText(f"{value}%")

    def _update_scale_label(self, value):
        """更新縮放比例標籤"""
        self.watermark_scale_label.setText(f"{value}%")

    def _add_pdf_watermark(self):
        """添加 PDF 浮水印"""
        pdf_path = self.watermark_pdf_input.text()
        if not pdf_path or not os.path.exists(pdf_path):
            self.show_warning("請先選擇有效的 PDF 文件")
            return

        # 檢查浮水印類型
        is_text = self.watermark_text_radio.isChecked()

        if is_text:
            # 文字浮水印
            watermark_text = self.watermark_text_input.text()
            if not watermark_text.strip():
                self.show_warning("請輸入浮水印文字")
                return
        else:
            # 圖片浮水印
            watermark_image = self.watermark_image_input.text()
            if not watermark_image or not os.path.exists(watermark_image):
                self.show_warning("請選擇有效的浮水印圖片")
                return

        # 選擇輸出路徑
        default_name = os.path.splitext(os.path.basename(pdf_path))[0] + "_watermarked.pdf"
        output_path, _ = QFileDialog.getSaveFileName(
            self, "儲存 PDF", default_name, "PDF 文件 (*.pdf)"
        )
        if not output_path:
            return

        # 獲取設定參數
        position_map = {
            "正中央": "center",
            "左上角": "top-left",
            "右上角": "top-right",
            "左下角": "bottom-left",
            "右下角": "bottom-right"
        }
        position = position_map.get(self.watermark_position.currentText(), "center")
        opacity = self.watermark_opacity_slider.value() / 100.0
        margin = self.watermark_margin.value()

        try:
            if is_text:
                # 添加文字浮水印
                font_size = self.watermark_font_size.value()
                rotation = self.watermark_rotation.value()
                success = add_text_watermark_to_pdf(
                    pdf_path, output_path, watermark_text,
                    position=position, opacity=opacity,
                    font_size=font_size, rotation=rotation,
                    margin=margin
                )
            else:
                # 添加圖片浮水印
                scale = self.watermark_scale_slider.value() / 100.0
                success = add_image_watermark_to_pdf(
                    pdf_path, output_path, watermark_image,
                    position=position, opacity=opacity, scale=scale,
                    margin=margin
                )

            if success:
                self.show_info(f"PDF 浮水印添加完成！\n\n輸出檔案：{output_path}")
            else:
                self.show_error("PDF 浮水印添加失敗，請查看錯誤訊息")

        except Exception as e:
            self.show_error(f"添加 PDF 浮水印時發生錯誤：\n{str(e)}")

    # === 影片轉 GIF 方法 ===
    def _select_video_for_gif(self):
        """選擇影片檔案"""
        start_dir = self.config.get('video.last_folder', '')
        file, _ = QFileDialog.getOpenFileName(self, "選擇影片", start_dir or "", Config.VIDEO_FILE_FILTER)
        if file:
            self.video_to_gif_path.setText(file)
            self._remember_folder('video.last_folder', file)

    def _on_gif_mode_changed(self):
        """模式切換時更新 UI"""
        is_continuous = self.gif_mode_continuous.isChecked()
        self.continuous_params.setVisible(is_continuous)
        self.sampling_params.setVisible(not is_continuous)

    def _start_video_to_gif(self):
        """開始影片轉 GIF"""
        video_path = self.video_to_gif_path.text()
        if not video_path or not os.path.exists(video_path):
            self.show_warning("請先選擇有效的影片檔案")
            return

        # 判斷模式
        is_continuous = self.gif_mode_continuous.isChecked()
        mode = 'continuous' if is_continuous else 'sampling'

        # 共用參數
        try:
            width = int(self.gif_width.text()) if self.gif_width.text() else 0
        except ValueError:
            self.show_warning("請輸入有效的寬度數字")
            return

        # 模式特定參數
        if is_continuous:
            try:
                start_time = float(self.gif_start_time.text())
                end_time = float(self.gif_end_time.text())
                fps = int(self.gif_fps.text())
            except ValueError:
                self.show_warning("請輸入有效的數字參數")
                return

            if fps < 1 or fps > 30:
                self.show_warning("FPS 必須在 1-30 之間")
                return

            sample_interval = 10  # 預設值，連續模式不使用
            frame_duration = 500  # 預設值，連續模式不使用
        else:
            try:
                sample_interval = float(self.gif_sample_interval.text())
                frame_duration = int(self.gif_frame_duration.text())
            except ValueError:
                self.show_warning("請輸入有效的數字參數")
                return

            if sample_interval <= 0:
                self.show_warning("採樣間隔必須大於 0")
                return

            if frame_duration < 100 or frame_duration > 5000:
                self.show_warning("每幀停留時間建議在 100-5000 毫秒之間")
                return

            start_time = 0  # 預設值，採樣模式不使用
            end_time = 0    # 預設值，採樣模式不使用
            fps = 10        # 預設值，採樣模式不使用

        # 詢問儲存路徑
        output_path, _ = QFileDialog.getSaveFileName(self, "儲存 GIF", "", "GIF (*.gif)")
        if not output_path:
            return

        # 初始化工作執行緒
        self.video_to_gif_worker = VideoToGifWorker(
            video_path=video_path,
            output_path=output_path,
            mode=mode,
            start_time=start_time,
            end_time=end_time,
            fps=fps,
            resize_width=width,
            sample_interval=sample_interval,
            frame_duration=frame_duration
        )
        self.video_to_gif_worker.progress.connect(self._on_v2g_progress)
        self.video_to_gif_worker.status.connect(self._on_v2g_status)
        self.video_to_gif_worker.finished.connect(self._on_v2g_finished)

        # 顯示進度介面
        self.v2g_progress_widget.setVisible(True)
        self.v2g_progress.setValue(0)
        self.btn_video_to_gif.setEnabled(False)
        self.btn_cancel_v2g.setVisible(True)

        # 開始計時
        self.operation_start_time = time.time()

        # 啟動執行緒
        self.video_to_gif_worker.start()

    def _on_v2g_progress(self, value):
        """更新影片轉 GIF 進度"""
        self.v2g_progress.setValue(value)
        self._update_time_label(self.v2g_time_label, value)

    def _on_v2g_status(self, status):
        """更新影片轉 GIF 狀態"""
        self.v2g_status_label.setText(status)

    def _on_v2g_finished(self, success, message):
        """影片轉 GIF 完成"""
        self.v2g_progress_widget.setVisible(False)
        self.btn_video_to_gif.setEnabled(True)
        self.btn_cancel_v2g.setVisible(False)
        self.operation_start_time = None

        if success:
            self.show_info(message)
        else:
            if "取消" not in message:
                self.show_error(message)
            else:
                self.statusBar().showMessage(f"⚠️ {message}", 3000)

    def _cancel_video_to_gif(self):
        """取消影片轉 GIF"""
        if self.video_to_gif_worker and self.video_to_gif_worker.isRunning():
            self.v2g_status_label.setText("正在取消操作...")
            self.video_to_gif_worker.cancel()
            self.btn_cancel_v2g.setEnabled(False)

    # === 圖片壓縮方法 ===
    def _select_images_for_compression(self):
        """選擇圖片進行壓縮"""
        start_dir = self.config.get('compression.last_folder', '')
        files, _ = QFileDialog.getOpenFileNames(self, "選擇圖片", start_dir or "", Config.IMAGE_FILE_FILTER)
        if files:
            self._handle_list_drop(self.compress_list, "Compress queue", files, [], source_label="Select")
            self._remember_folder('compression.last_folder', files[0])

    def _on_compress_dropped(self, files, skipped):
        """Handle drag-and-drop for compression queue."""
        self._handle_list_drop(self.compress_list, 'Compress queue', files, skipped)


    def _update_quality_label(self, value):
        """更新品質標籤"""
        self.compress_quality_label.setText(str(value))

    def _browse_compress_folder(self):
        """瀏覽輸出資料夾"""
        start_dir = self.config.get('compression.output_folder', '')
        folder = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾", start_dir or "")
        if folder:
            self.compress_output_folder.setText(folder)
            self._on_text_pref_changed(self.compress_output_folder, 'compression.output_folder')

    def _start_compression(self):
        """開始壓縮圖片"""
        files = self.compress_list.get_all_files()
        if not files:
            self.show_warning("請先選擇圖片")
            return

        quality = self.compress_quality_slider.value()
        output_format = self.compress_format.currentText()
        output_folder = self.compress_output_folder.text()

        # 初始化工作執行緒
        self.compress_worker = ImageCompressionWorker(files, quality, output_format, output_folder)
        self.compress_worker.progress.connect(self._on_compress_progress)
        self.compress_worker.status.connect(self._on_compress_status)
        self.compress_worker.stats.connect(self._on_compress_stats)
        self.compress_worker.finished.connect(self._on_compress_finished)

        # 顯示進度介面
        self.compress_progress_widget.setVisible(True)
        self.compress_progress.setValue(0)
        self.compress_stats_label.setText("")
        self.btn_compress.setEnabled(False)
        self.btn_cancel_compress.setVisible(True)

        # 開始計時
        self.operation_start_time = time.time()

        # 啟動執行緒
        self.compress_worker.start()

    def _on_compress_progress(self, value):
        """更新圖片壓縮進度"""
        self.compress_progress.setValue(value)
        self._update_time_label(self.compress_time_label, value)

    def _on_compress_status(self, status):
        """更新圖片壓縮狀態"""
        self.compress_status_label.setText(status)

    def _on_compress_stats(self, stats):
        """更新壓縮統計資訊"""
        self.compress_stats_label.setText(stats)

    def _on_compress_finished(self, success, message):
        """圖片壓縮完成"""
        self.compress_progress_widget.setVisible(False)
        self.btn_compress.setEnabled(True)
        self.btn_cancel_compress.setVisible(False)
        self.operation_start_time = None

        if success:
            self.show_info(message)
        else:
            if "取消" not in message:
                self.show_error(message)
            else:
                self.statusBar().showMessage(f"⚠️ {message}", 3000)

    def _cancel_compression(self):
        """取消圖片壓縮"""
        if self.compress_worker and self.compress_worker.isRunning():
            self.compress_status_label.setText("正在取消操作...")
            self.compress_worker.cancel()
            self.btn_cancel_compress.setEnabled(False)

    def show_about(self):
        QMessageBox.about(self, "關於 MediaToolkit",
            "<h2>📦 MediaToolkit v6.0</h2>"
            "<p><b>多媒體與文檔處理工具套件</b></p>"
            "<p>整合圖片、影片與文檔處理功能</p>"
            "<br>"
            "<p><b>功能模組：</b></p>"
            "<p>• 圖片處理：拼接、GIF、浮水印、批次編輯</p>"
            "<p>• 影片處理：合併、格式轉換</p>"
            "<p>• 文檔處理：Word↔PDF、PDF 合併</p>"
            "<br>"
            "<p style='color:#5B9BD5; font-weight:bold;'>© 2025 Dof Liu AI工作室</p>"
            "<p style='color:#607D8B; font-size:9pt;'>All Rights Reserved.</p>")

    def show_warning(self, msg):
        QMessageBox.warning(self, "⚠️ 警告", msg)

    def _create_menus(self):
        """建立選單列"""
        menubar = self.menuBar()
        menubar.clear()
        
        # 檔案選單
        file_menu = menubar.addMenu("檔案 (&F)")
        
        # 最近使用記錄
        self.recent_menu = file_menu.addMenu("最近開啟的檔案")
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        
        file_menu.addSeparator()
        
        save_config_action = QAction("保存設定", self)
        save_config_action.triggered.connect(self.config.save_config)
        file_menu.addAction(save_config_action)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 檢視選單
        view_menu = menubar.addMenu("檢視 (&V)")
        
        # 主題切換
        theme_menu = view_menu.addMenu("主題風格")
        
        light_theme_action = QAction("淺色主題", self)
        light_theme_action.triggered.connect(lambda: self._apply_theme("light"))
        theme_menu.addAction(light_theme_action)
        
        dark_theme_action = QAction("深色主題", self)
        dark_theme_action.triggered.connect(lambda: self._apply_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        
        # 說明選單
        help_menu = menubar.addMenu("說明 (&H)")
        
        about_action = QAction("關於 MediaToolkit", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _update_recent_menu(self):
        """更新最近使用檔案清單"""
        self.recent_menu.clear()
        recent_files = self.config.get_recent_files()
        
        if not recent_files:
            no_action = QAction("無最近記錄", self)
            no_action.setEnabled(False)
            self.recent_menu.addAction(no_action)
            return
            
        for item in recent_files:
            path = item.get('path')
            if not path or not os.path.exists(path):
                continue
                
            name = item.get('name', os.path.basename(path))
            action = QAction(f"{name}", self)
            action.setData(path)
            action.triggered.connect(lambda checked, p=path: self._open_recent_file(p))
            self.recent_menu.addAction(action)
            
        self.recent_menu.addSeparator()
        clear_action = QAction("清除記錄", self)
        clear_action.triggered.connect(self.config.clear_recent)
        self.recent_menu.addAction(clear_action)

    def _open_recent_file(self, path):
        """開啟最近的檔案"""
        if not os.path.exists(path):
            QMessageBox.warning(self, "錯誤", "檔案不存在")
            return
            
        # 簡單判斷檔案類型並跳轉到對應頁面
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']:
            self._add_files_to_image_processor([path])
        elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
            self._add_files_to_video_processor([path])
        elif ext == '.pdf':
            # 自動跳轉到 PDF 工具
            self.category_tabs.setCurrentIndex(1) # PDF 頁面
            # 這裡可以進一步優化自動載入...

    def _add_files_to_image_processor(self, files):
        """將檔案加入圖片處理器（輔助方法）"""
        self.category_tabs.setCurrentIndex(0) # 圖片頁面
        self.media_tabs.setCurrentIndex(0) # 圖片處理分頁
        self.image_preview.add_files(files)

    def _add_files_to_video_processor(self, files):
        """將檔案加入影片處理器（輔助方法）"""
        self.category_tabs.setCurrentIndex(0)
        self.media_tabs.setCurrentIndex(1)
        # 注意：這裡需要 VideoMerge 頁面向外暴露添加檔案的方法
        # 暫時先把功能做進 _create_video_tab 的區域變數 refactor

    # === 新增功能 UI 實作 ===

    def _create_batch_rename_tab(self):
        """建立批次重新命名分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 檔案選擇
        group = self._create_group_box("📁 選擇檔案 - 支援拖放")
        file_layout = QVBoxLayout()
        
        self.rename_list = DragDropListWidget()
        self.rename_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.rename_list.files_dropped.connect(self._on_rename_files_dropped)
        file_layout.addWidget(self.rename_list)
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("➕ 加入檔案")
        btn_add.clicked.connect(self._browse_rename_files)
        btn_clear = QPushButton("🗑️ 清空列表")
        btn_clear.clicked.connect(self.rename_list.clear)
        btn_clear.setProperty("secondary", True)
        
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)
        
        group.setLayout(file_layout)
        layout.addWidget(group)
        
        # 命名規則設定
        rules_group = self._create_group_box("⚙️ 命名規則")
        rules_layout = QGridLayout()
        
        # 1. 替換文字
        rules_layout.addWidget(QLabel("替換文字:"), 0, 0)
        self.edit_replace_old = QLineEdit()
        self.edit_replace_old.setPlaceholderText("原文字")
        rules_layout.addWidget(self.edit_replace_old, 0, 1)
        
        rules_layout.addWidget(QLabel("→"), 0, 2)
        self.edit_replace_new = QLineEdit()
        self.edit_replace_new.setPlaceholderText("新文字")
        rules_layout.addWidget(self.edit_replace_new, 0, 3)
        
        # 2. 前綴後綴
        rules_layout.addWidget(QLabel("添加前綴:"), 1, 0)
        self.edit_prefix = QLineEdit()
        rules_layout.addWidget(self.edit_prefix, 1, 1)
        
        rules_layout.addWidget(QLabel("添加後綴:"), 1, 2)
        self.edit_suffix = QLineEdit()
        rules_layout.addWidget(self.edit_suffix, 1, 3)
        
        # 3. 自動編號
        self.chk_numbering = QGroupBox("🔢 自動編號")
        self.chk_numbering.setCheckable(True)
        self.chk_numbering.setChecked(False)
        num_layout = QHBoxLayout()
        
        num_layout.addWidget(QLabel("起始數字:"))
        self.spin_start_num = QSpinBox()
        self.spin_start_num.setRange(0, 999999)
        self.spin_start_num.setValue(1)
        num_layout.addWidget(self.spin_start_num)
        
        num_layout.addWidget(QLabel("位數:"))
        self.spin_num_digits = QSpinBox()
        self.spin_num_digits.setRange(1, 10)
        self.spin_num_digits.setValue(3)
        num_layout.addWidget(self.spin_num_digits)
        
        self.chk_numbering.setLayout(num_layout)
        rules_layout.addWidget(self.chk_numbering, 2, 0, 1, 4)
        
        rules_group.setLayout(rules_layout)
        layout.addWidget(rules_group)
        
        # 操作按鈕
        action_layout = QHBoxLayout()
        btn_preview = QPushButton("👁️ 預覽結果")
        btn_preview.clicked.connect(self._preview_rename)
        btn_preview.setProperty("secondary", True)
        
        self.btn_start_rename = QPushButton("🚀 開始重新命名")
        self.btn_start_rename.clicked.connect(self._start_batch_rename)
        self.btn_start_rename.setMinimumHeight(45)
        
        action_layout.addWidget(btn_preview)
        action_layout.addWidget(self.btn_start_rename)
        layout.addLayout(action_layout)
        
        self.utils_tabs.addTab(tab, "📝 批次重新命名")

    def _createCleanupTab(self):
        cleanup_tab = QWidget()
        cleanup_layout = QVBoxLayout(cleanup_tab)

        cleanup_desc = QLabel(
            "掃描 Windows 常見會持續累積的暫存資料夾（例如 Temp、快取、回收桶），\n"
            "勾選後可一鍵清理。請先確認資料夾內容。"
        )
        cleanup_desc.setWordWrap(True)
        cleanup_layout.addWidget(cleanup_desc)

        drive_layout = QHBoxLayout()
        drive_layout.addWidget(QLabel("目標磁碟:"))
        self.comboCleanupDrive = QComboBox()
        self.comboCleanupDrive.addItems(self.get_available_drives())
        drive_layout.addWidget(self.comboCleanupDrive)

        btn_scan_cleanup = QPushButton("掃描清理建議")
        btn_scan_cleanup.clicked.connect(self.scanCleanupCandidates)
        drive_layout.addWidget(btn_scan_cleanup)
        drive_layout.addStretch()
        cleanup_layout.addLayout(drive_layout)

        self.chk_scan_common = QCheckBox("掃描常見快取 (快速)")
        self.chk_scan_common.setChecked(True)
        self.chk_scan_appdata = QCheckBox("深入分析 AppData (較慢)")
        self.chk_scan_large = QCheckBox("找出超大檔案 (>500MB)")
        
        options_layout = QHBoxLayout()
        options_layout.addWidget(self.chk_scan_common)
        options_layout.addWidget(self.chk_scan_appdata)
        options_layout.addWidget(self.chk_scan_large)
        options_layout.addStretch()
        cleanup_layout.addLayout(options_layout)

        self.cleanupTree = QTreeWidget()
        self.cleanupTree.setHeaderLabels(["名稱", "大小", "類型", "完整路徑"])
        self.cleanupTree.setColumnWidth(0, 250)
        self.cleanupTree.setColumnWidth(1, 100)
        self.cleanupTree.setColumnWidth(2, 60)
        cleanup_layout.addWidget(self.cleanupTree)

        self.lblCleanupSummary = QLabel("尚未掃描")
        cleanup_layout.addWidget(self.lblCleanupSummary)

        btn_delete_selected = QPushButton("刪除勾選項目")
        btn_delete_selected.clicked.connect(self.deleteSelectedCleanupItems)
        cleanup_layout.addWidget(btn_delete_selected)

        self.utils_tabs.addTab(cleanup_tab, "🧹 硬碟清理建議")

    def get_available_drives(self):
        if os.name != "nt":
            return ["/"]

        drives = []
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                drives.append(drive_path)
        return drives if drives else ["C:\\"]

    def get_cleanup_candidates(self, drive_root):
        candidates = []
        if os.name != "nt":
            return [
                {"label": "系統暫存資料夾", "path": "/tmp"},
                {"label": "使用者快取資料夾", "path": os.path.expanduser("~/.cache")},
            ]

        drive = drive_root.rstrip("\\/")
        home_dir = os.path.expanduser("~")
        user_profile = home_dir if home_dir.startswith(drive) else None

        candidates.extend([
            {"label": "Windows 暫存資料夾", "path": f"{drive}\\Windows\\Temp"},
            {"label": "Windows 更新下載快取", "path": f"{drive}\\Windows\\SoftwareDistribution\\Download"},
            {"label": "系統回收桶", "path": f"{drive}\\$Recycle.Bin"},
        ])

        if user_profile:
            candidates.extend([
                {"label": "使用者 Temp", "path": os.path.join(user_profile, "AppData", "Local", "Temp")},
                {"label": "IE/Edge 快取", "path": os.path.join(user_profile, "AppData", "Local", "Microsoft", "Windows", "INetCache")},
                {"label": "縮圖快取", "path": os.path.join(user_profile, "AppData", "Local", "Microsoft", "Windows", "Explorer")},
                {"label": "程式崩潰記錄", "path": os.path.join(user_profile, "AppData", "Local", "CrashDumps")},
                {"label": "NPM 快取", "path": os.path.join(user_profile, "AppData", "Local", "npm-cache")},
                {"label": "Python Pip 快取", "path": os.path.join(user_profile, "AppData", "Local", "pip", "Cache")},
                {"label": "Discord 快取", "path": os.path.join(user_profile, "AppData", "Roaming", "discord", "Cache")},
                {"label": "Slack 快取", "path": os.path.join(user_profile, "AppData", "Roaming", "Slack", "Cache")},
                {"label": "Chrome 快取", "path": os.path.join(user_profile, "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache")},
                {"label": "LINE 資料 (貼圖/快取可能會很大)", "path": os.path.join(user_profile, "AppData", "Local", "LINE", "Data")},
                {"label": "Firefox Profiles", "path": os.path.join(user_profile, "AppData", "Roaming", "Mozilla", "Firefox", "Profiles")},
            ])

        return candidates

    def calculate_folder_size(self, path):
        total_size = 0
        try:
            if os.path.isfile(path):
                return os.path.getsize(path)

            for root, _, files in os.walk(path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        if not os.path.islink(file_path):
                            total_size += os.path.getsize(file_path)
                    except OSError:
                        continue
        except OSError:
            return 0
        return total_size

    def format_size(self, size_bytes):
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        for unit in units:
            if size < 1024 or unit == units[-1]:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size_bytes} B"

    def scanCleanupCandidates(self):
        self.cleanupTree.clear()
        self.cleanup_candidates_map = {}
        
        drive_root = self.comboCleanupDrive.currentText()
        scan_common = self.chk_scan_common.isChecked()
        scan_appdata = self.chk_scan_appdata.isChecked()
        scan_large = self.chk_scan_large.isChecked()
        
        if not any([scan_common, scan_appdata, scan_large]):
            QMessageBox.warning(self, "未選擇項目", "請至少勾選一項掃描範圍")
            return

        self.lblCleanupSummary.setText("開始深入掃描中... 請稍候")
        
        self.worker = DiskScanWorker(drive_root, scan_common, scan_appdata, scan_large)
        self.worker.progress_signal.connect(self._on_scan_progress)
        self.worker.item_found_signal.connect(self._on_item_found)
        self.worker.finished_signal.connect(self._on_scan_finished)
        self.worker.start()

    def _on_scan_progress(self, msg):
        self.lblCleanupSummary.setText(f"掃描中: {msg}")

    def _on_item_found(self, item_data):
        # We categorize the items into top level nodes
        type_group = item_data.get("type", "其他")
        
        # Mapping groups to readable names
        group_names = {
            "common": "🧹 常見快取與暫存檔",
            "large_file": "📁 超大檔案 (>500MB)",
            "appdata": "🌐 AppData 分析 (較大資料夾)"
        }
        
        group_name = group_names.get(type_group, "其他")
        
        # Find or create root node
        root_items = self.cleanupTree.findItems(group_name, Qt.MatchExactly, 0)
        if root_items:
            root_node = root_items[0]
        else:
            root_node = QTreeWidgetItem(self.cleanupTree)
            root_node.setText(0, group_name)
            root_node.setFlags(root_node.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
            root_node.setCheckState(0, Qt.Unchecked)
            self.cleanupTree.addTopLevelItem(root_node)

        # Create child item
        path = item_data["path"]
        self.cleanup_candidates_map[path] = item_data["label"]
        
        child = QTreeWidgetItem(root_node)
        child.setText(0, item_data["label"])
        child.setText(1, self.format_size(item_data["size"]))
        child.setText(2, "資料夾" if item_data.get("isdir") else "檔案")
        child.setText(3, path)  # Show full path in the 4th column
        child.setToolTip(0, path)
        child.setToolTip(3, path)
        child.setData(0, Qt.UserRole, path)
        child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
        child.setCheckState(0, Qt.Unchecked)
        
        # Expand the root to see items coming in
        root_node.setExpanded(True)

    def _on_scan_finished(self, total_size, total_count):
        if total_count == 0:
            self.lblCleanupSummary.setText("未找到可建議清理的項目，或目前選取的範圍大小為 0")
            QMessageBox.information(self, "掃描完成", "沒有找到符合的清理建議項目。")
        else:
            self.lblCleanupSummary.setText(
                f"✅ 掃描完成！共找到 {total_count} 個建議項目，預估可釋放 {self.format_size(total_size)}"
            )

    def deleteSelectedCleanupItems(self):
        import shutil
        selected_paths = []
        
        # Traverse tree to find checked leaf items
        root_count = self.cleanupTree.topLevelItemCount()
        for i in range(root_count):
            root = self.cleanupTree.topLevelItem(i)
            for j in range(root.childCount()):
                child = root.child(j)
                if child.checkState(0) == Qt.Checked:
                    path = child.data(0, Qt.UserRole)
                    if path:
                        selected_paths.append(path)

        if not selected_paths:
            QMessageBox.warning(self, "警告", "請先勾選要刪除的項目")
            return

        confirm = QMessageBox.question(
            self,
            "確認刪除",
            f"即將刪除 {len(selected_paths)} 個項目，這個動作無法復原。是否繼續？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        deleted_count = 0
        error_messages = []

        for path in selected_paths:
            try:
                # To prevent accidental deletions, we still check against our map
                if path not in self.cleanup_candidates_map:
                    error_messages.append(f"{path}: 不在安全清單中，已略過")
                    continue

                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    for name in os.listdir(path):
                        child = os.path.join(path, name)
                        try:
                            if os.path.isdir(child):
                                shutil.rmtree(child)
                            else:
                                os.remove(child)
                        except Exception as child_err:
                            error_messages.append(f"{child}: {child_err}")
                deleted_count += 1
            except Exception as e:
                error_messages.append(f"{path}: {e}")

        # Rescan after deletion to refresh tree
        self.scanCleanupCandidates()

        message = f"已處理 {deleted_count} 個項目。"
        if error_messages:
            message += "\n\n以下項目刪除失敗：\n" + "\n".join(error_messages[:5])
        QMessageBox.information(self, "清理完成", message)

    
    def _create_video_compression_tab(self):
        """影片壓縮分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)

        # 檔案選擇
        group = self._create_group_box("📁 選擇影片檔案 - 支援多選與拖放")
        file_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        btn_select = QPushButton("📂 選擇影片")
        btn_select.clicked.connect(lambda: self.select_files_for_list(
            self.compress_video_list, 
            Config.VIDEO_FILE_FILTER,
            "選擇影片檔案"
        ))
        btn_select.setMinimumHeight(40)
        btn_layout.addWidget(btn_select)
        
        btn_clear = QPushButton("🗑️ 清空列表")
        btn_clear.clicked.connect(lambda: self.compress_video_list.clear())
        btn_clear.setFixedWidth(100)
        btn_clear.setMinimumHeight(40)
        btn_layout.addWidget(btn_clear)
        
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)
        
        self.compress_video_list = DragDropListWidget()
        self.compress_video_list.setMinimumHeight(150)
        file_layout.addWidget(self.compress_video_list)
        group.setLayout(file_layout)
        layout.addWidget(group)

        # 壓縮設定
        params = self._create_group_box("⚙️ 壓縮參數")
        p_layout = QVBoxLayout()
        
        # 解析度選擇
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("目標解析度:"))
        self.compress_res_combo = QComboBox()
        self.compress_res_combo.addItems(["Original", "1080p", "720p", "480p"])
        self.compress_res_combo.setCurrentText("720p") # 預設 720p
        res_layout.addWidget(self.compress_res_combo)
        res_layout.addStretch()
        p_layout.addLayout(res_layout)
        
        # 品質 CRF
        crf_layout = QHBoxLayout()
        crf_layout.addWidget(QLabel("壓縮品質 (CRF):"))
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(18, 35)
        self.crf_spin.setValue(23) # 預設 23 (良好平衡)
        crf_layout.addWidget(self.crf_spin)
        
        self.crf_slider = QSlider(Qt.Horizontal)
        self.crf_slider.setRange(18, 35)
        self.crf_slider.setValue(23)
        self.crf_slider.valueChanged.connect(self.crf_spin.setValue)
        self.crf_spin.valueChanged.connect(self.crf_slider.setValue)
        crf_layout.addWidget(self.crf_slider)
        
        note_label = QLabel("(數值越小畫質越好，預設 23，範圍 18-35)")
        note_label.setStyleSheet("color: gray; font-size: 9pt;")
        crf_layout.addWidget(note_label)
        
        p_layout.addLayout(crf_layout)
        params.setLayout(p_layout)
        layout.addWidget(params)

        # 輸出設定
        out_group = self._create_group_box("💾 輸出設定")
        out_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        self.compress_out_path = QLineEdit()
        self.compress_out_path.setPlaceholderText("留空則儲存於原資料夾 (自動加上 _compressed)")
        path_layout.addWidget(QLabel("輸出資料夾:"))
        path_layout.addWidget(self.compress_out_path)
        
        btn_browse = QPushButton("瀏覽")
        btn_browse.clicked.connect(lambda: self._browse_folder(self.compress_out_path))
        path_layout.addWidget(btn_browse)
        out_layout.addLayout(path_layout)
        out_group.setLayout(out_layout)
        layout.addWidget(out_group)

        # 進度顯示區域
        self.compress_progress_widget = QWidget()
        prog_layout = QVBoxLayout(self.compress_progress_widget)
        prog_layout.setContentsMargins(0, 0, 0, 0)

        self.compress_status_label = QLabel("就緒")
        self.compress_status_label.setStyleSheet("color: #64748B; font-size: 10pt;")
        prog_layout.addWidget(self.compress_status_label)

        self.compress_progress = QProgressBar()
        self.compress_progress.setTextVisible(True)
        self.compress_progress.setValue(0)
        prog_layout.addWidget(self.compress_progress)

        self.compress_progress_widget.setVisible(False)
        layout.addWidget(self.compress_progress_widget)

        # 執行按鈕
        action_layout = QHBoxLayout()
        self.btn_start_compress_video = QPushButton("🎬 開始壓縮影片")
        self.btn_start_compress_video.setProperty("primary", True)
        self.btn_start_compress_video.setMinimumHeight(50)
        self.btn_start_compress_video.clicked.connect(self._start_video_compression)
        action_layout.addWidget(self.btn_start_compress_video)
        layout.addLayout(action_layout)

        layout.addStretch()
        self.media_tabs.addTab(tab, "📉 影片壓縮")

    def _start_video_compression(self):
        """開始執行影片壓縮"""
        files = self.compress_video_list.get_all_files()
        if not files:
            QMessageBox.warning(self, Config.UI_TEXT['warning'], Config.MESSAGES['no_videos_selected'])
            return

        resolution = self.compress_res_combo.currentText()
        crf = self.crf_spin.value()
        output_folder = self.compress_out_path.text().strip()

        # 禁用 UI
        self._set_ui_enabled(False)
        self.btn_start_compress_video.setText("正在壓縮... (請觀察終端機輸出)")
        self.btn_start_compress_video.setEnabled(False)

        # 顯示進度
        if hasattr(self, 'compress_progress_widget'):
            self.compress_progress_widget.setVisible(True)
            self.compress_progress.setValue(0)
            self.compress_status_label.setText("準備中...")

        # 啟動 Worker
        self.video_compress_worker = VideoCompressionWorker(files, resolution, crf, output_folder)
        self.video_compress_worker.progress.connect(self._update_progress)
        self.video_compress_worker.status.connect(self._update_status)
        self.video_compress_worker.stats.connect(lambda s: self.statusBar().showMessage(s)) # 顯示統計
        self.video_compress_worker.finished.connect(self._on_video_compression_finished)
        
        self.task_manager.add_task(self.video_compress_worker, "影片壓縮")
        self.video_compress_worker.start()

    def _on_video_compression_finished(self, success, message):
        """影片壓縮完成回調"""
        self._set_ui_enabled(True)
        self.btn_start_compress_video.setText("🎬 開始壓縮影片")
        self.btn_start_compress_video.setEnabled(True)
        
        if hasattr(self, 'compress_progress_widget'):
            self.compress_progress_widget.setVisible(False)
            
        self._on_worker_finished(success, message)
        self.statusBar().showMessage(Config.UI_TEXT['completed'])
    
    def _create_image_editor_tab(self):

        """建立圖片編輯分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 檔案選擇區域
        group = self._create_group_box("🖼️ 圖片編輯")
        content_layout = QVBoxLayout()
        
        # 工具列
        toolbar = QHBoxLayout()
        
        btn_rotate_left = QPushButton("↺ 向左旋轉")
        btn_rotate_left.clicked.connect(lambda: self._add_edit_operation('rotate', 90))
        
        btn_rotate_right = QPushButton("↻ 向右旋轉")
        btn_rotate_right.clicked.connect(lambda: self._add_edit_operation('rotate', -90))
        
        btn_flip_h = QPushButton("↔ 水平翻轉")
        btn_flip_h.clicked.connect(lambda: self._add_edit_operation('flip', 'horizontal'))
        
        btn_flip_v = QPushButton("↕ 垂直翻轉")
        btn_flip_v.clicked.connect(lambda: self._add_edit_operation('flip', 'vertical'))
        
        toolbar.addWidget(btn_rotate_left)
        toolbar.addWidget(btn_rotate_right)
        toolbar.addWidget(btn_flip_h)
        toolbar.addWidget(btn_flip_v)
        toolbar.addStretch()
        
        content_layout.addLayout(toolbar)
        
        # 圖片列表與預覽
        self.edit_list = ImagePreviewGrid()
        self.edit_list.file_clicked.connect(self._show_image_viewer)
        content_layout.addWidget(self.edit_list)
        
        # 底部按鈕
        bottom_layout = QHBoxLayout()
        btn_add = QPushButton("📂 加入圖片")
        btn_add.clicked.connect(self._browse_edit_files)
        
        self.btn_apply_edit = QPushButton("💾 應用並儲存")
        self.btn_apply_edit.clicked.connect(self._start_image_edit)
        self.btn_apply_edit.setMinimumHeight(40)
        
        bottom_layout.addWidget(btn_add)
        bottom_layout.addWidget(self.btn_apply_edit)
        content_layout.addLayout(bottom_layout)
        
        group.setLayout(content_layout)
        layout.addWidget(group)
        
        self.media_tabs.addTab(tab, "✏️ 圖片編輯")

    # === 事件處理與邏輯 ===
    
    def _on_rename_files_dropped(self, files):
        """批次命名：檔案拖放處理"""
        self.rename_list.add_files(files)
        
    def _browse_rename_files(self):
        """批次命名：瀏覽檔案"""
        files, _ = QFileDialog.getOpenFileNames(self, "選擇檔案", "", "All Files (*.*)")
        if files:
            self.rename_list.add_files(files)
            self._remember_folder('image.last_folder', files[0])
            
    def _preview_rename(self):
        """預覽重新命名結果"""
        if self.rename_list.count() == 0:
            return
            
        # 簡單預覽視窗
        preview_text = "預覽前 10 個檔案的變更:\n\n"
        
        files = self.rename_list.get_all_files()
        
        # 模擬規則應用 (複製自 Worker 邏輯)
        prefix = self.edit_prefix.text()
        suffix = self.edit_suffix.text()
        replace_old = self.edit_replace_old.text()
        replace_new = self.edit_replace_new.text()
        use_num = self.chk_numbering.isChecked()
        start_num = self.spin_start_num.value()
        num_digits = self.spin_num_digits.value()
        
        for i, file_path in enumerate(files[:10]):
            filename = os.path.basename(file_path)
            name, ext = os.path.splitext(filename)
            
            if replace_old:
                name = name.replace(replace_old, replace_new)
            
            new_name = f"{prefix}{name}{suffix}"
            
            if use_num:
                num_str = str(start_num + i).zfill(num_digits)
                new_name = f"{new_name}_{num_str}"
                
            final_name = f"{new_name}{ext}"
            preview_text += f"{filename}  →  {final_name}\n"
            
        if len(files) > 10:
            preview_text += f"\n... 以及其他 {len(files)-10} 個檔案"
            
        QMessageBox.information(self, "預覽重新命名", preview_text)

    def _start_batch_rename(self):
        """開始批次重新命名"""
        files = self.rename_list.get_all_files()
        if not files:
            QMessageBox.warning(self, "提示", "請先加入檔案！")
            return
            
        rules = {
            'prefix': self.edit_prefix.text(),
            'suffix': self.edit_suffix.text(),
            'replace_old': self.edit_replace_old.text(),
            'replace_new': self.edit_replace_new.text(),
            'use_num': self.chk_numbering.isChecked(),
            'start_num': self.spin_start_num.value(),
            'num_digits': self.spin_num_digits.value()
        }
        
        self.btn_start_rename.setEnabled(False)
        self.batch_rename_worker = BatchRenameWorker(files, rules)
        self.batch_rename_worker.finished.connect(self._on_rename_finished)
        self.batch_rename_worker.start()
        
    def _on_rename_finished(self, success, message):
        self.btn_start_rename.setEnabled(True)
        if success:
            QMessageBox.information(self, "完成", message)
            self.rename_list.clear() # 成功後清空列表
        else:
            QMessageBox.warning(self, "錯誤", message)

    # 圖片編輯邏輯
    def _browse_edit_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇圖片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if files:
            self.edit_list.add_files(files)
            self._remember_folder('image.last_folder', files[0])

    def _add_edit_operation(self, op_type, value):
        """暫存編輯操作（目前簡化為直接應用到列表中的所有圖片）"""
        # 注意：這個版本的實作是「點擊即處理」還是「累積操作後處理」？
        # 為了簡化 UI，我們這裡採用：用戶點擊按鈕 -> 加入待執行操作列表 -> 點擊儲存 -> 執行
        # 但 UI 上需要顯示待執行的操作，這裡先簡化為：點擊儲存時，彈出對話框詢問要執行什麼操作
        
        # 修正：更好的方式是維護一個 operations 列表
        if not hasattr(self, '_pending_edits'):
            self._pending_edits = []
            
        op_desc = ""
        if op_type == 'rotate':
            op_desc = f"旋轉 {value}°"
        else:
            op_desc = f"{value} 翻轉"
            
        # 簡單提示已加入操作
        # 簡單提示已加入操作
        self.statusBar().showMessage(f"已加入操作: {op_desc} (點擊儲存以應用)")
        self._pending_edits.append({'type': op_type, 'value': value if op_type == 'rotate' else 0, 'mode': value if op_type == 'flip' else ''})
        
        # 即時預覽變更
        self.edit_list.apply_transformation(op_type, value)

    def _start_image_edit(self):
        files = self.edit_list.get_files()
        if not files:
            QMessageBox.warning(self, "提示", "請先加入圖片！")
            return
            
        if not hasattr(self, '_pending_edits') or not self._pending_edits:
            QMessageBox.information(self, "提示", "請先點擊上方工具列按鈕選擇要進行的編輯操作")
            return
            
        # 確認
        reply = QMessageBox.question(self, "確認編輯", f"將對 {len(files)} 張圖片執行 {len(self._pending_edits)} 個操作，確定嗎？\n(將會覆蓋原始檔案或另存新檔)",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.btn_apply_edit.setEnabled(False)
            self.image_edit_worker = ImageEditWorker(files, self._pending_edits)
            self.image_edit_worker.finished.connect(self._on_image_edit_finished)
            self.image_edit_worker.progress.connect(lambda v: self.statusBar().showMessage(f"處理中... {v}%"))
            self.image_edit_worker.start()

    def _on_image_edit_finished(self, success, message):
        self.btn_apply_edit.setEnabled(True)
        self.statusBar().showMessage(message)
        if success:
            QMessageBox.information(self, "完成", message)
            self._pending_edits = [] # 清空操作
        else:
            QMessageBox.warning(self, "錯誤", message)

    def _apply_theme(self, theme=None):
        """應用主題 (強制淺色模式)"""
        # 強制使用淺色模式
        self.setStyleSheet(ModernStyle.get_light_stylesheet())
                
    def _toggle_theme(self):
        """切換主題 (已停用)"""
        pass
        
    def _update_recent_menu(self):
        """更新最近使用檔案清單"""
        if not hasattr(self, 'recent_menu'):
            return
            
        self.recent_menu.clear()
        recent_files = self.config.get_recent_files()
        
        if not recent_files:
            no_action = QAction("無最近記錄", self)
            no_action.setEnabled(False)
            self.recent_menu.addAction(no_action)
            return
            
        for item in recent_files:
            path = item["path"]
            name = item.get("name", os.path.basename(path))
            action = QAction(f"{name}", self)
            action.setToolTip(path)
            # Use default value for lambda to capture current path variable
            action.triggered.connect(lambda checked, p=path: self._open_recent_file(p))
            self.recent_menu.addAction(action)
            
        self.recent_menu.addSeparator()
        clear_action = QAction("清除記錄", self)
        clear_action.triggered.connect(self._clear_recent)
        self.recent_menu.addAction(clear_action)
        
    def _open_recent_file(self, path):
        """開啟最近使用的檔案"""
        if not os.path.exists(path):
            QMessageBox.warning(self, "檔案不存在", f"找不到檔案：\n{path}")
            return
            
        # Determine likely tab based on extension
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.md']:
            # Switch to Markdown tab and load
            self.category_tabs.setCurrentIndex(1) # Document tab
            self.doc_tabs.setCurrentIndex(1) # Markdown tab
            if hasattr(self, 'md_input'):
                 self.md_input.setText(path)
                 self._suggest_docx_output(path)
        elif ext in ['.docx']:
            self.category_tabs.setCurrentIndex(1) 
            self.doc_tabs.setCurrentIndex(0) # Word/PDF
            if hasattr(self, 'word_input'):
                self.word_input.setText(path)
        elif ext in ['.pdf']:
            self.category_tabs.setCurrentIndex(1)
            # Default to Word/PDF tab
            self.doc_tabs.setCurrentIndex(0)
            if hasattr(self, 'pdf_input'):
                 self.pdf_input.setText(path)
        
    def _clear_recent(self):
        self.config.clear_recent()
        self._update_recent_menu()

    def _show_task_manager(self):
        """顯示任務管理器"""
        dialog = TaskQueueDialog(self)
        dialog.exec_()
        
    def _add_task_tracking(self, worker, name):
        """加入任務追蹤"""
        self.task_manager.add_task(worker, name)
        
    def _suggest_docx_output(self, md_path):
        """根據 Markdown 路徑建議 Docx 輸出路徑"""
        if not md_path:
            return
        
        # 預設輸出到同目錄
        base_name = os.path.splitext(md_path)[0]
        docx_path = f"{base_name}.docx"
        
        if hasattr(self, 'docx_output'):
            self.docx_output.setText(docx_path)

    def show_error(self, msg):
        QMessageBox.critical(self, "❌ 錯誤", msg)

    def show_info(self, msg):
        QMessageBox.information(self, "✅ 完成", msg)



    def _create_pdf_tools_tab(self):
        """PDF 進階工具分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)

        # === 區塊 1: 拆分與擷取 ===
        split_group = self._create_group_box("✂️ 拆分與擷取 PDF")
        split_layout = QVBoxLayout()
        
        # 檔案選擇
        file_layout = QHBoxLayout()
        self.pdf_split_input = QLineEdit()
        self.pdf_split_input.setPlaceholderText("請選擇 PDF 文件...")
        btn_browse = QPushButton("📂 瀏覽")
        btn_browse.clicked.connect(lambda: self._browse_pdf_generic(self.pdf_split_input, 'pdf_split'))
        file_layout.addWidget(self.pdf_split_input)
        file_layout.addWidget(btn_browse)
        split_layout.addLayout(file_layout)
        
        # 參數設定
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("頁碼範圍 (例如: 1-3, 5, 8):"))
        self.pdf_split_range = QLineEdit()
        self.pdf_split_range.setPlaceholderText("1-3, 5")
        params_layout.addWidget(self.pdf_split_range)
        split_layout.addLayout(params_layout)
        
        # 操作按鈕
        btn_layout = QHBoxLayout()
        
        btn_split = QPushButton("✂️ 拆分為單一檔案")
        btn_split.clicked.connect(lambda: self._start_pdf_tool('split'))
        btn_layout.addWidget(btn_split)
        
        btn_extract = QPushButton("📑 擷取為個別檔案")
        btn_extract.clicked.connect(lambda: self._start_pdf_tool('extract'))
        btn_layout.addWidget(btn_extract)
        
        split_layout.addLayout(btn_layout)
        split_group.setLayout(split_layout)
        layout.addWidget(split_group)

        # === 區塊 2: PDF 轉圖片 ===
        img_group = self._create_group_box("🖼️ PDF 轉圖片")
        img_layout = QVBoxLayout()
        
        # 檔案選擇
        file_layout2 = QHBoxLayout()
        self.pdf_img_input = QLineEdit()
        self.pdf_img_input.setPlaceholderText("請選擇 PDF 文件...")
        btn_browse2 = QPushButton("📂 瀏覽")
        btn_browse2.clicked.connect(lambda: self._browse_pdf_generic(self.pdf_img_input, 'pdf_img'))
        file_layout2.addWidget(self.pdf_img_input)
        file_layout2.addWidget(btn_browse2)
        img_layout.addLayout(file_layout2)
        
        # 轉換參數
        grid_layout = QHBoxLayout()
        
        grid_layout.addWidget(QLabel("格式:"))
        self.pdf_img_format = QComboBox()
        self.pdf_img_format.addItems(["png", "jpg", "jpeg"])
        grid_layout.addWidget(self.pdf_img_format)
        
        grid_layout.addWidget(QLabel("DPI (解析度):"))
        self.pdf_img_dpi = QComboBox()
        self.pdf_img_dpi.addItems(["72 (螢幕)", "150 (一般)", "300 (列印)"])
        self.pdf_img_dpi.setCurrentIndex(1)
        grid_layout.addWidget(self.pdf_img_dpi)
        
        img_layout.addLayout(grid_layout)
        
        # 執行按鈕
        btn_convert = QPushButton("🖼️ 轉為圖片")
        btn_convert.clicked.connect(lambda: self._start_pdf_tool('to_image'))
        img_layout.addWidget(btn_convert)
        
        img_group.setLayout(img_layout)
        layout.addWidget(img_group)
        
        # === 區塊 3: PDF 壓縮（瘦身）===
        compress_group = self._create_group_box("📦 PDF 壓縮（瘦身）")
        compress_layout = QVBoxLayout()
        
        # 檔案選擇
        file_layout3 = QHBoxLayout()
        self.pdf_compress_input = QLineEdit()
        self.pdf_compress_input.setPlaceholderText("請選擇要壓縮的 PDF 文件...")
        btn_browse3 = QPushButton("📂 瀏覽")
        btn_browse3.clicked.connect(lambda: self._browse_pdf_generic(self.pdf_compress_input, 'pdf_compress'))
        file_layout3.addWidget(self.pdf_compress_input)
        file_layout3.addWidget(btn_browse3)
        compress_layout.addLayout(file_layout3)
        
        # 壓縮模式選擇
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("壓縮模式:"))
        
        from PyQt5.QtWidgets import QButtonGroup, QRadioButton
        
        self.compress_mode_group = QButtonGroup(self)
        
        self.radio_basic = QRadioButton("基礎壓縮")
        self.radio_basic.setToolTip("壓縮內容串流 + 移除重複物件（無損）")
        self.radio_basic.setChecked(True)
        self.compress_mode_group.addButton(self.radio_basic, 0)
        mode_layout.addWidget(self.radio_basic)
        
        self.radio_image = QRadioButton("圖片壓縮")
        self.radio_image.setToolTip("降低 PDF 中圖片的品質")
        self.compress_mode_group.addButton(self.radio_image, 1)
        mode_layout.addWidget(self.radio_image)
        
        self.radio_deep = QRadioButton("深度壓縮")
        self.radio_deep.setToolTip("將每頁轉為JPEG重新組裝（最大壓縮，可能損失品質）")
        self.compress_mode_group.addButton(self.radio_deep, 2)
        mode_layout.addWidget(self.radio_deep)
        
        mode_layout.addStretch()
        compress_layout.addLayout(mode_layout)
        
        # 品質滑桿
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("品質 (僅圖片/深度壓縮):"))
        
        self.pdf_compress_quality = QSlider(Qt.Horizontal)
        self.pdf_compress_quality.setRange(10, 100)
        self.pdf_compress_quality.setValue(70)
        self.pdf_compress_quality.setTickPosition(QSlider.TicksBelow)
        self.pdf_compress_quality.setTickInterval(10)
        quality_layout.addWidget(self.pdf_compress_quality)
        
        self.pdf_compress_quality_label = QLabel("70")
        self.pdf_compress_quality_label.setMinimumWidth(30)
        self.pdf_compress_quality.valueChanged.connect(
            lambda v: self.pdf_compress_quality_label.setText(str(v))
        )
        quality_layout.addWidget(self.pdf_compress_quality_label)
        
        compress_layout.addLayout(quality_layout)
        
        # 壓縮按鈕
        btn_compress = QPushButton("📦 開始壓縮")
        btn_compress.clicked.connect(lambda: self._start_pdf_tool('compress'))
        btn_compress.setMinimumHeight(40)
        compress_layout.addWidget(btn_compress)
        
        compress_group.setLayout(compress_layout)
        layout.addWidget(compress_group)
        
        # 狀態標籤
        self.pdf_tool_status = QLabel("就緒")
        self.pdf_tool_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.pdf_tool_status)

        layout.addStretch()
        self.doc_tabs.addTab(tab, "🛠️ PDF 進階工具")

    def _browse_pdf_generic(self, input_widget, key_prefix):
        """選擇 PDF 文件 (通用)"""
        start_dir = self.config.get(f'document.last_{key_prefix}_folder', '')
        file, _ = QFileDialog.getOpenFileName(
            self, "選擇 PDF 文件", start_dir or "", "PDF 文件 (*.pdf)"
        )
        if file:
            input_widget.setText(file)
            self._remember_folder(f'document.last_{key_prefix}_folder', file)

    def _start_pdf_tool(self, mode):
        """開始 PDF 工具任務"""
        # 取得參數
        if mode in ['split', 'extract']:
            input_path = self.pdf_split_input.text()
            range_str = self.pdf_split_range.text()
            if not input_path:
                self.show_warning("請選擇 PDF 文件")
                return
            if not range_str:
                self.show_warning("請輸入頁碼範圍")
                return
            
            # 使用相同目錄
            output_dir = os.path.dirname(input_path)
            
            self.pdf_tool_worker = PDFToolsWorker(
                mode, input_path=input_path, range_str=range_str, output_dir=output_dir
            )
            
        elif mode == 'to_image':
            input_path = self.pdf_img_input.text()
            if not input_path:
                self.show_warning("請選擇 PDF 文件")
                return
                
            fmt = self.pdf_img_format.currentText()
            dpi_str = self.pdf_img_dpi.currentText().split(' ')[0]
            dpi = int(dpi_str)
            
            # 建立子資料夾
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_dir = os.path.join(os.path.dirname(input_path), f"{base_name}_images")
            
            self.pdf_tool_worker = PDFToolsWorker(
                mode, input_path=input_path, output_dir=output_dir, format=fmt, dpi=dpi
            )

        elif mode == 'compress':
            input_path = self.pdf_compress_input.text()
            if not input_path:
                self.show_warning("請選擇要壓縮的 PDF 文件")
                return
            
            # 取得壓縮模式
            mode_id = self.compress_mode_group.checkedId()
            compress_mode = ['basic', 'image', 'deep'][mode_id]
            quality = self.pdf_compress_quality.value()
            
            # 輸出檔名
            base_name = os.path.splitext(input_path)[0]
            output_path = f"{base_name}_compressed.pdf"
            
            self.pdf_tool_worker = PDFToolsWorker(
                mode, 
                input_path=input_path, 
                output_path=output_path,
                compress_mode=compress_mode,
                quality=quality,
                dpi=150
            )

        # 啟動 Worker
        self.pdf_tool_worker.status.connect(self.pdf_tool_status.setText)
        self.pdf_tool_worker.finished.connect(self._on_pdf_tool_finished)
        
        task_name = {
            'split': 'PDF 拆分',
            'extract': 'PDF 擷取',
            'to_image': 'PDF 轉圖片',
            'compress': 'PDF 壓縮'
        }.get(mode, 'PDF 任務')
        
        self._add_task_tracking(self.pdf_tool_worker, task_name)
        self.pdf_tool_worker.start()
        
        self.pdf_tool_status.setText("處理中...")

    def _on_pdf_tool_finished(self, success, message):
        """PDF 工具任務完成"""
        self.pdf_tool_status.setText("就緒" if success else "失敗")
        if success:
            self.show_info(message)
        else:
            self.show_error(message)



def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MediaToolkit")
    app.setApplicationVersion("6.0")
    window = MediaToolkit()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
