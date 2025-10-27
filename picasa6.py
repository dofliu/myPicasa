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
    QMessageBox, QTabWidget, QProgressBar, QGroupBox, QAction
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import time
from PIL import Image
from moviepy.editor import VideoFileClip, concatenate_videoclips
from natsort import natsorted

from utils import (
    resize_with_padding, resize_image, Config,
    DragDropListWidget, ImagePreviewGrid, ImageViewerDialog,
    add_watermark, convert_word_to_pdf, convert_pdf_to_word,
    merge_pdfs, get_pdf_info, check_dependencies, get_config_manager
)
from utils.modern_style import ModernStyle


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


class MediaToolkit(QMainWindow):
    """多媒體與文檔處理工具套件"""

    def __init__(self):
        super().__init__()

        # 載入配置管理器
        self.config = get_config_manager()

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
        
        self.theme_btn = QPushButton("🌙 深色模式")
        self.theme_btn.setProperty("secondary", True)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.theme_btn.setFixedWidth(120)
        header_layout.addWidget(self.theme_btn)
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
        media_layout.addWidget(self.media_tabs)
        
        # 文件轉換類別
        doc_widget = QWidget()
        doc_layout = QVBoxLayout(doc_widget)
        doc_layout.setContentsMargins(0, 10, 0, 0)
        self.doc_tabs = QTabWidget()
        self.doc_tabs.setDocumentMode(True)
        self._create_word_pdf_tab()
        self._create_pdf_merge_tab()
        doc_layout.addWidget(self.doc_tabs)
        
        self.category_tabs.addTab(media_widget, "🎨 圖片影像處理")
        self.category_tabs.addTab(doc_widget, "📄 文件轉換工具")
        main_layout.addWidget(self.category_tabs)
        
        self.statusBar().showMessage('🎉 MediaToolkit 已就緒！  |  © 2025 Dof Liu AI工作室')

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
        grid_layout.addWidget(self.edit_cols)
        grid_layout.addWidget(QLabel("行數:"))
        self.edit_rows = QLineEdit(str(Config.DEFAULT_GRID_ROWS))
        self.edit_rows.setMaximumWidth(80)
        grid_layout.addWidget(self.edit_rows)
        grid_layout.addStretch()
        p_layout.addLayout(grid_layout)
        
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("縮放策略:"))
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(Config.RESIZE_STRATEGIES)
        strategy_layout.addWidget(self.combo_strategy)
        strategy_layout.addStretch()
        p_layout.addLayout(strategy_layout)
        
        gif_layout = QHBoxLayout()
        gif_layout.addWidget(QLabel("GIF 持續時間 (ms):"))
        self.edit_duration = QLineEdit(str(Config.DEFAULT_GIF_DURATION))
        self.edit_duration.setMaximumWidth(100)
        gif_layout.addWidget(self.edit_duration)
        gif_layout.addStretch()
        p_layout.addLayout(gif_layout)
        
        params.setLayout(p_layout)
        layout.addWidget(params)

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
        fmt_layout.addWidget(self.combo_output_format)
        fmt_layout.addStretch()
        s_layout.addLayout(fmt_layout)
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("輸出資料夾:"))
        self.edit_output_folder = QLineEdit("converted_images")
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
        fmt_layout.addWidget(self.compress_format)
        fmt_layout.addStretch()
        s_layout.addLayout(fmt_layout)

        # 輸出資料夾
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("輸出資料夾:"))
        self.compress_output_folder = QLineEdit("compressed_images")
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

        self.pdf_list = DragDropListWidget(file_extensions=['.pdf'])
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

    def _create_group_box(self, title):
        """創建群組框"""
        group = QGroupBox(title)
        self._group_boxes.append(group)
        group.setStyleSheet(ModernStyle.get_card_style(self.current_theme))
        return group

    def _create_menus(self):
        """創建選單"""
        file_menu = self.menuBar().addMenu("📁 檔案")
        about_action = QAction("ℹ️ 關於", self)
        about_action.triggered.connect(self.show_about)
        file_menu.addAction(about_action)
        
        exit_action = QAction("🚪 退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

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
        """保存視窗大小和位置"""
        self.config.set('window.width', self.width(), auto_save=False)
        self.config.set('window.height', self.height(), auto_save=False)
        self.config.set('window.x', self.x(), auto_save=False)
        self.config.set('window.y', self.y(), auto_save=False)
        self.config.set('window.maximized', self.isMaximized(), auto_save=False)

    def _load_parameters(self):
        """從配置載入參數"""
        # 圖片處理參數
        self.edit_cols.setText(str(self.config.get('image.grid_cols', 3)))
        self.edit_rows.setText(str(self.config.get('image.grid_rows', 3)))
        self.edit_duration.setText(str(self.config.get('image.gif_duration', 500)))

        strategy = self.config.get('image.resize_strategy', '直接縮放')
        index = self.combo_strategy.findText(strategy)
        if index >= 0:
            self.combo_strategy.setCurrentIndex(index)

        # 影片處理參數
        self.edit_output_video.setText(self.config.get('video.output_name', 'merged_video.mp4'))

        # 格式轉換參數
        self.edit_output_folder.setText(self.config.get('convert.output_folder', 'converted_images'))

        fmt = self.config.get('convert.output_format', 'PNG')
        index = self.combo_output_format.findText(fmt)
        if index >= 0:
            self.combo_output_format.setCurrentIndex(index)

    def _save_parameters(self):
        """保存參數到配置"""
        try:
            # 圖片處理參數
            self.config.set('image.grid_cols', int(self.edit_cols.text()), auto_save=False)
            self.config.set('image.grid_rows', int(self.edit_rows.text()), auto_save=False)
            self.config.set('image.gif_duration', int(self.edit_duration.text()), auto_save=False)
            self.config.set('image.resize_strategy', self.combo_strategy.currentText(), auto_save=False)

            # 影片處理參數
            self.config.set('video.output_name', self.edit_output_video.text(), auto_save=False)

            # 格式轉換參數
            self.config.set('convert.output_folder', self.edit_output_folder.text(), auto_save=False)
            self.config.set('convert.output_format', self.combo_output_format.currentText(), auto_save=False)
        except:
            pass  # 忽略轉換錯誤

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

    def _handle_list_drop(self, widget, label, files, skipped):
        added = []
        duplicates = []
        skipped_all = list(skipped or [])
        if files:
            added, duplicates, skipped_extra = widget.add_files(files)
            skipped_all.extend(skipped_extra)
        self._show_ingest_feedback(label, 'Drag', len(added), len(duplicates), skipped_all)

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

    def _add_watermark(self):
        files = self.image_preview.get_files()
        if not files:
            self.show_warning("請先選擇圖片")
            return
        if add_watermark(files, self):
            self.show_info("浮水印添加完成！")

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇圖片", "", Config.IMAGE_FILE_FILTER)
        if files:
            self.image_preview.add_files(files, source="manual")

    def select_video_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇影片", "", Config.VIDEO_FILE_FILTER)
        if files:
            added, duplicates, skipped = self.video_files_list.add_files(files)
            self._show_ingest_feedback("Video queue", "Select", len(added), len(duplicates), skipped)

    def select_convert_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇圖片", "", Config.IMAGE_FILE_FILTER)
        if files:
            added, duplicates, skipped = self.convert_list.add_files(files)
            self._show_ingest_feedback("Convert queue", "Select", len(added), len(duplicates), skipped)

    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if folder:
            self.edit_output_folder.setText(folder)

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
        file, _ = QFileDialog.getOpenFileName(self, "選擇 Word", "", "Word (*.docx *.doc)")
        if file:
            self.word_input.setText(file)

    def _browse_pdf(self):
        file, _ = QFileDialog.getOpenFileName(self, "選擇 PDF", "", "PDF (*.pdf)")
        if file:
            self.pdf_input.setText(file)

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
        if word:
            if convert_pdf_to_word(pdf, word):
                self.show_info(f"轉換成功！\n{word}")
            else:
                self.show_error("PDF 轉 Word 失敗")

    def _select_pdfs(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇 PDF", "", "PDF (*.pdf)")
        if files:
            added, duplicates, skipped = self.pdf_list.add_files(files)
            self._show_ingest_feedback("PDF queue", "Select", len(added), len(duplicates), skipped)

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
            self.show_warning("請先選擇 PDF 文件")
            return
        output, _ = QFileDialog.getSaveFileName(self, "儲存 PDF", "", "PDF (*.pdf)")
        if output:
            add_toc = self.pdf_add_toc.isChecked()
            add_page_numbers = self.pdf_add_page_numbers.isChecked()

            if merge_pdfs(files, output, add_toc=add_toc, add_page_numbers=add_page_numbers):
                self.show_info(f"合併成功！\n{output}")
            else:
                self.show_error("PDF 合併失敗")

    # === 影片轉 GIF 方法 ===
    def _select_video_for_gif(self):
        """選擇影片檔案"""
        file, _ = QFileDialog.getOpenFileName(self, "選擇影片", "", Config.VIDEO_FILE_FILTER)
        if file:
            self.video_to_gif_path.setText(file)

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
        files, _ = QFileDialog.getOpenFileNames(self, "選擇圖片", "", Config.IMAGE_FILE_FILTER)
        if files:
            added, duplicates, skipped = self.compress_list.add_files(files)
            self._show_ingest_feedback("Compress queue", "Select", len(added), len(duplicates), skipped)

    def _on_compress_dropped(self, files, skipped):
        """Handle drag-and-drop for compression queue."""
        self._handle_list_drop(self.compress_list, 'Compress queue', files, skipped)


    def _update_quality_label(self, value):
        """更新品質標籤"""
        self.compress_quality_label.setText(str(value))

    def _browse_compress_folder(self):
        """瀏覽輸出資料夾"""
        folder = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if folder:
            self.compress_output_folder.setText(folder)

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

    def show_error(self, msg):
        QMessageBox.critical(self, "❌ 錯誤", msg)

    def show_info(self, msg):
        QMessageBox.information(self, "✅ 完成", msg)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MediaToolkit")
    app.setApplicationVersion("6.0")
    window = MediaToolkit()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
