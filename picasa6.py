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
        self.video_files_list.files_dropped.connect(self._on_video_dropped)
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
        self.convert_list.files_dropped.connect(self._on_convert_dropped)
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
        self.pdf_list.files_dropped.connect(self._on_pdf_dropped)
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
        self.statusBar().showMessage(f'📊 目前有 {count} 個圖片')

    def _on_video_dropped(self, files):
        self.video_files_list.add_files(files)

    def _on_convert_dropped(self, files):
        self.convert_list.add_files(files)

    def _on_pdf_dropped(self, files):
        self.pdf_list.add_files(files)

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
            self.image_preview.add_files(files)

    def select_video_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇影片", "", Config.VIDEO_FILE_FILTER)
        if files:
            self.video_files_list.add_files(files)

    def select_convert_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "選擇圖片", "", Config.IMAGE_FILE_FILTER)
        if files:
            self.convert_list.add_files(files)

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
            self.pdf_list.add_files(files)

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
