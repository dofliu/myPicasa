#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
myPicasa - 圖片與影片整理工具 (拖放+預覽增強版)

這是最新的增強版本，新增：
- 拖放檔案支援（檔案和資料夾）
- 圖片預覽網格（縮圖顯示）
- 拖放調整順序
- 點擊放大預覽
- 深色/淺色主題切換
- 現代化 UI 設計
"""
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QComboBox, QFileDialog,
    QMessageBox, QTabWidget, QProgressBar, QGroupBox, QSpacerItem,
    QSizePolicy, QAction
)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PIL import Image
from PIL import ImageQt
from moviepy.editor import VideoFileClip, concatenate_videoclips
from natsort import natsorted

# 導入自訂工具模組
from utils import (
    resize_with_padding, resize_image, Config,
    DragDropListWidget, ImagePreviewGrid, ImageViewerDialog
)
from utils.modern_style import ModernStyle


class ModernImageTool(QMainWindow):
    """現代化圖片與影片整理工具主視窗"""

    def __init__(self):
        super().__init__()
        self.current_theme = "light"  # 預設使用淺色主題
        self._group_boxes = []
        self.setWindowTitle(f"🎨 {Config.APP_NAME} - 拖放+預覽增強版")
        self.resize(1100, 750)  # 更大的預設視窗（支援預覽網格）
        self.setMinimumSize(900, 650)

        self._init_ui()
        self._create_actions()
        self._create_menus()
        self._apply_theme(self.current_theme)

    def _init_ui(self):
        """初始化使用者介面"""
        # 建立中央小工具
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主佈局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        central_widget.setLayout(main_layout)

        # 標題區域
        self._create_header(main_layout)

        # 建立分頁視窗
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setMovable(True)
        main_layout.addWidget(self.tab_widget)

        # 建立各個功能分頁
        self._create_image_tab()
        self._create_video_tab()
        self._create_convert_image_tab()

        # 狀態列
        self.statusBar().showMessage('🎉 準備就緒 - 歡迎使用！')

    def _create_header(self, layout):
        """建立標題區域"""
        header_layout = QHBoxLayout()

        # 標題
        title_label = QLabel(f"🎨 {Config.APP_NAME}")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setProperty("heading", True)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 版本標籤
        version_label = QLabel(f"v{Config.APP_VERSION}")
        version_label.setStyleSheet("color: #64748B; font-size: 9pt;")
        header_layout.addWidget(version_label)

        # 主題切換按鈕
        self.theme_btn = QPushButton("🌙 深色模式")
        self.theme_btn.setProperty("secondary", True)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self.theme_btn.setFixedWidth(120)
        header_layout.addWidget(self.theme_btn)

        layout.addLayout(header_layout)

    def _create_image_tab(self):
        """建立圖片處理分頁（支援拖放和預覽）"""
        image_tab = QWidget()
        image_layout = QVBoxLayout(image_tab)
        image_layout.setSpacing(16)

        # 檔案選擇區（帶拖放和預覽）
        file_group = self._create_group_box("📁 選擇圖片檔案 - 支援拖放")
        file_layout = QVBoxLayout()

        # 按鈕行
        btn_layout = QHBoxLayout()
        btn_select = QPushButton("📂 選擇圖片檔案")
        btn_select.clicked.connect(self.select_files)
        btn_select.setMinimumHeight(40)
        btn_layout.addWidget(btn_select)

        btn_layout.addWidget(QLabel("或直接拖放檔案/資料夾到下方"))
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        # 圖片預覽網格（支援拖放）
        self.image_preview = ImagePreviewGrid()
        self.image_preview.file_clicked.connect(self._show_image_viewer)
        self.image_preview.files_changed.connect(self._update_image_stats)
        self.image_preview.setMinimumHeight(200)

        # 讓預覽網格支援拖放
        self.image_preview.setAcceptDrops(True)
        file_layout.addWidget(self.image_preview)

        file_group.setLayout(file_layout)
        image_layout.addWidget(file_group)

        # 參數設定區
        params_group = self._create_group_box("⚙️ 參數設定")
        params_layout = QVBoxLayout()

        # 網格設定
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
        params_layout.addLayout(grid_layout)

        # 縮放策略
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("縮放策略:"))
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(Config.RESIZE_STRATEGIES)
        self.combo_strategy.setMinimumHeight(36)
        strategy_layout.addWidget(self.combo_strategy)
        strategy_layout.addStretch()
        params_layout.addLayout(strategy_layout)

        # GIF 參數
        gif_layout = QHBoxLayout()
        gif_layout.addWidget(QLabel("GIF 持續時間 (ms):"))
        self.edit_duration = QLineEdit(str(Config.DEFAULT_GIF_DURATION))
        self.edit_duration.setMaximumWidth(100)
        gif_layout.addWidget(self.edit_duration)
        gif_layout.addStretch()
        params_layout.addLayout(gif_layout)

        params_group.setLayout(params_layout)
        image_layout.addWidget(params_group)

        # 操作按鈕區
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)

        btn_merge = QPushButton("🖼️ 拼接圖片")
        btn_merge.clicked.connect(self.merge_images)
        btn_merge.setMinimumHeight(44)
        action_layout.addWidget(btn_merge)

        btn_gif = QPushButton("🎞️ 生成 GIF")
        btn_gif.clicked.connect(self.create_gif)
        btn_gif.setMinimumHeight(44)
        action_layout.addWidget(btn_gif)

        image_layout.addLayout(action_layout)
        image_layout.addStretch()

        self.tab_widget.addTab(image_tab, "🖼️  圖片處理")

    def _create_video_tab(self):
        """建立影片處理分頁（支援拖放）"""
        video_tab = QWidget()
        video_layout = QVBoxLayout(video_tab)
        video_layout.setSpacing(16)

        # 檔案選擇區（帶拖放）
        file_group = self._create_group_box("📹 選擇影片檔案 - 支援拖放")
        file_layout = QVBoxLayout()

        # 按鈕行
        btn_layout = QHBoxLayout()
        btn_select_videos = QPushButton("📂 選擇影片檔案")
        btn_select_videos.clicked.connect(self.select_video_files)
        btn_select_videos.setMinimumHeight(40)
        btn_layout.addWidget(btn_select_videos)

        btn_layout.addWidget(QLabel("或直接拖放影片檔案/資料夾到下方"))
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        # 使用拖放清單（支援影片格式）
        self.video_files_list = DragDropListWidget(
            file_extensions=Config.SUPPORTED_VIDEO_FORMATS
        )
        self.video_files_list.files_dropped.connect(self._on_video_files_dropped)
        self.video_files_list.setMinimumHeight(200)
        file_layout.addWidget(self.video_files_list)

        file_group.setLayout(file_layout)
        video_layout.addWidget(file_group)

        # 輸出設定區
        output_group = self._create_group_box("💾 輸出設定")
        output_layout = QVBoxLayout()

        output_name_layout = QHBoxLayout()
        output_name_layout.addWidget(QLabel("輸出檔名:"))
        self.edit_output_video_name = QLineEdit("merged_video.mp4")
        self.edit_output_video_name.setPlaceholderText("例如: merged_video.mp4")
        self.edit_output_video_name.setMinimumHeight(36)
        output_name_layout.addWidget(self.edit_output_video_name)
        output_layout.addLayout(output_name_layout)

        output_group.setLayout(output_layout)
        video_layout.addWidget(output_group)

        # 進度條
        self.video_progress_bar = QProgressBar()
        self.video_progress_bar.setVisible(False)
        self.video_progress_bar.setMinimumHeight(28)
        video_layout.addWidget(self.video_progress_bar)

        # 合併按鈕
        btn_merge_videos = QPushButton("🎬 合併影片")
        btn_merge_videos.clicked.connect(self.merge_videos)
        btn_merge_videos.setMinimumHeight(44)
        video_layout.addWidget(btn_merge_videos)

        video_layout.addStretch()

        self.tab_widget.addTab(video_tab, "🎬  影片處理")

    def _create_convert_image_tab(self):
        """建立圖片格式轉換分頁（支援拖放）"""
        convert_tab = QWidget()
        convert_layout = QVBoxLayout(convert_tab)
        convert_layout.setSpacing(16)

        # 檔案選擇區（帶拖放）
        file_group = self._create_group_box("📁 選擇要轉換的圖片 - 支援拖放")
        file_layout = QVBoxLayout()

        # 按鈕行
        btn_layout = QHBoxLayout()
        btn_select = QPushButton("📂 選擇圖片檔案")
        btn_select.clicked.connect(self.select_convert_images)
        btn_select.setMinimumHeight(40)
        btn_layout.addWidget(btn_select)

        btn_layout.addWidget(QLabel("或直接拖放圖片檔案/資料夾到下方"))
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)

        # 使用拖放清單（支援圖片格式）
        image_exts = [ext.lower() for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp']]
        self.convert_files_list = DragDropListWidget(file_extensions=image_exts)
        self.convert_files_list.files_dropped.connect(self._on_convert_files_dropped)
        self.convert_files_list.setMinimumHeight(150)
        file_layout.addWidget(self.convert_files_list)

        file_group.setLayout(file_layout)
        convert_layout.addWidget(file_group)

        # 轉換設定區
        settings_group = self._create_group_box("🔄 轉換設定")
        settings_layout = QVBoxLayout()

        # 輸出格式
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("輸出格式:"))
        self.combo_output_format = QComboBox()
        self.combo_output_format.addItems(Config.SUPPORTED_IMAGE_FORMATS)
        self.combo_output_format.setMinimumHeight(36)
        format_layout.addWidget(self.combo_output_format)
        format_layout.addStretch()
        settings_layout.addLayout(format_layout)

        # 輸出資料夾
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("輸出資料夾:"))
        self.edit_output_folder = QLineEdit("converted_images")
        self.edit_output_folder.setPlaceholderText("留空則儲存至原資料夾")
        self.edit_output_folder.setMinimumHeight(36)
        folder_layout.addWidget(self.edit_output_folder)

        btn_browse = QPushButton("📂 瀏覽")
        btn_browse.setProperty("secondary", True)
        btn_browse.clicked.connect(self.browse_output_folder)
        btn_browse.setFixedWidth(100)
        folder_layout.addWidget(btn_browse)
        settings_layout.addLayout(folder_layout)

        settings_group.setLayout(settings_layout)
        convert_layout.addWidget(settings_group)

        # 轉換按鈕
        btn_convert = QPushButton("✨ 開始轉換")
        btn_convert.clicked.connect(self.convert_images)
        btn_convert.setMinimumHeight(44)
        convert_layout.addWidget(btn_convert)

        convert_layout.addStretch()

        self.tab_widget.addTab(convert_tab, "🔄  格式轉換")

    def _create_group_box(self, title):
        """建立群組框"""
        group = QGroupBox(title)
        self._group_boxes.append(group)
        group.setStyleSheet(ModernStyle.get_card_style(self.current_theme))
        return group

    def _create_actions(self):
        """建立選單動作"""
        self.open_action = QAction("📂 打開圖片", self)
        self.open_action.triggered.connect(self.open_image)

        self.exit_action = QAction("🚪 退出", self)
        self.exit_action.triggered.connect(self.close)

        self.about_action = QAction("ℹ️ 關於", self)
        self.about_action.triggered.connect(self.show_about)

    def _create_menus(self):
        """建立選單"""
        file_menu = self.menuBar().addMenu("📁 檔案")
        file_menu.addAction(self.open_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        help_menu = self.menuBar().addMenu("❓ 說明")
        help_menu.addAction(self.about_action)

    def _toggle_theme(self):
        """切換主題"""
        if self.current_theme == "light":
            self.current_theme = "dark"
            self.theme_btn.setText("☀️ 淺色模式")
        else:
            self.current_theme = "light"
            self.theme_btn.setText("🌙 深色模式")

        self._apply_theme(self.current_theme)
        self.statusBar().showMessage(f'🎨 已切換至{"深色" if self.current_theme == "dark" else "淺色"}主題')

    def _apply_theme(self, theme):
        """套用主題"""
        if theme == "dark":
            self.setStyleSheet(ModernStyle.get_dark_stylesheet())
        else:
            self.setStyleSheet(ModernStyle.get_light_stylesheet())
        self._refresh_group_box_styles()

    def _refresh_group_box_styles(self):
        """Refresh group box styling to match the active theme."""
        card_style = ModernStyle.get_card_style(self.current_theme)
        for group in self._group_boxes:
            group.setStyleSheet(card_style)

    def _show_image_viewer(self, file_path):
        """顯示圖片檢視器"""
        dialog = ImageViewerDialog(file_path, self)
        dialog.exec_()

    def _update_image_stats(self):
        """更新圖片統計資訊"""
        count = len(self.image_preview.get_files())
        self.statusBar().showMessage(f'📊 目前有 {count} 個圖片檔案')

    def _on_video_files_dropped(self, files):
        """處理影片檔案拖放"""
        self.video_files_list.add_files(files)
        self.statusBar().showMessage(f'✅ 已新增 {len(files)} 個影片檔案')

    def _on_convert_files_dropped(self, files):
        """處理轉換檔案拖放"""
        self.convert_files_list.add_files(files)
        self.statusBar().showMessage(f'✅ 已新增 {len(files)} 個圖片檔案待轉換')

    def show_about(self):
        """顯示關於對話框"""
        about_text = f"""
        <h2>🎨 {Config.APP_NAME}</h2>
        <p><b>版本:</b> {Config.APP_VERSION}</p>
        <p><b>作者:</b> {Config.APP_AUTHOR}</p>
        <br>
        <p>一個現代化、美觀的圖片與影片整理工具</p>
        <p>支援圖片拼接、GIF 製作、影片合併和格式轉換</p>
        <br>
        <p style="color: #64748B;">© 2025 myPicasa. All rights reserved.</p>
        """
        QMessageBox.about(self, "關於 myPicasa", about_text)

    # === 以下是業務邏輯方法（與 picasa3.py 相同）===

    def open_image(self):
        """開啟單一圖片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打開圖片", "", Config.IMAGE_FILE_FILTER
        )
        if file_path:
            try:
                self.image = Image.open(file_path)
                self.statusBar().showMessage(f'✅ 已開啟: {os.path.basename(file_path)}')
            except Exception as e:
                self.show_error(Config.MESSAGES['image_read_failed'].format(e))

    def select_files(self):
        """選擇圖片檔案"""
        files, _ = QFileDialog.getOpenFileNames(
            self, Config.UI_TEXT['select_images'], "",
            Config.IMAGE_FILE_FILTER
        )
        if files:
            self.image_preview.add_files(files)
            self.statusBar().showMessage(f'✅ 已選擇 {len(files)} 個圖片檔案')

    def select_video_files(self):
        """選擇影片檔案"""
        videos, _ = QFileDialog.getOpenFileNames(
            self, Config.UI_TEXT['select_videos'], "",
            Config.VIDEO_FILE_FILTER
        )
        if videos:
            self.video_files_list.add_files(videos)
            self.statusBar().showMessage(f'✅ 已選擇 {len(videos)} 個影片檔案')

    def select_convert_images(self):
        """選擇要轉換的圖片檔案"""
        files, _ = QFileDialog.getOpenFileNames(
            self, Config.UI_TEXT['select_convert_images'], "",
            Config.IMAGE_FILE_FILTER
        )
        if files:
            self.convert_files_list.add_files(files)
            self.statusBar().showMessage(f'✅ 已選擇 {len(files)} 個圖片檔案待轉換')

    def browse_output_folder(self):
        """瀏覽輸出資料夾"""
        folder_path = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if folder_path:
            self.edit_output_folder.setText(folder_path)

    def generate_merged_image(self):
        """產生拼接圖片"""
        files = self.image_preview.get_files()
        if not files:
            self.show_warning(Config.MESSAGES['no_images_selected'])
            return None

        try:
            grid_cols = int(self.edit_cols.text())
            grid_rows = int(self.edit_rows.text())
        except ValueError:
            self.show_error(Config.MESSAGES['invalid_number_format'])
            return None

        try:
            images = [Image.open(p) for p in files]
        except Exception as e:
            self.show_error(Config.MESSAGES['image_read_failed'].format(e))
            return None

        min_width = min(img.width for img in images)
        min_height = min(img.height for img in images)
        cell_width, cell_height = min_width, min_height

        gap = Config.DEFAULT_IMAGE_GAP
        merged_width = grid_cols * cell_width + (grid_cols + 1) * gap
        merged_height = grid_rows * cell_height + (grid_rows + 1) * gap
        merged_image = Image.new("RGB", (merged_width, merged_height),
                                color=Config.DEFAULT_BG_COLOR)

        strategy = self.combo_strategy.currentText()
        idx = 0
        for row in range(grid_rows):
            for col in range(grid_cols):
                if idx >= len(images):
                    break
                resized_img = resize_image(images[idx], (cell_width, cell_height), strategy)
                x = gap + col * (cell_width + gap)
                y = gap + row * (cell_height + gap)
                merged_image.paste(resized_img, (x, y))
                idx += 1

        return merged_image

    def merge_images(self):
        """拼接圖片"""
        merged_image = self.generate_merged_image()
        if merged_image is None:
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "儲存拼接後圖片", "",
            Config.get_save_image_filter()
        )
        if save_path:
            try:
                merged_image.save(save_path)
                self.show_info(Config.MESSAGES['merge_success'].format(save_path))
                self.statusBar().showMessage('✅ 圖片拼接完成')
            except Exception as e:
                self.show_error(Config.MESSAGES['save_failed'].format(e))

    def create_gif(self):
        """建立 GIF 動畫"""
        files = self.image_preview.get_files()
        if not files:
            self.show_warning(Config.MESSAGES['no_images_selected'])
            return

        try:
            duration = int(self.edit_duration.text())
        except ValueError:
            self.show_error(Config.MESSAGES['invalid_duration'])
            return

        try:
            images = [Image.open(p) for p in files]
        except Exception as e:
            self.show_error(Config.MESSAGES['image_read_failed'].format(e))
            return

        min_width = min(img.width for img in images)
        min_height = min(img.height for img in images)
        target_size = (min_width, min_height)
        strategy = self.combo_strategy.currentText()
        frames = [resize_image(img, target_size, strategy) for img in images]

        save_path, _ = QFileDialog.getSaveFileName(
            self, "儲存 GIF 動畫", "",
            Config.get_save_gif_filter()
        )
        if save_path:
            try:
                frames[0].save(
                    save_path,
                    save_all=True,
                    append_images=frames[1:],
                    duration=duration,
                    loop=0
                )
                self.show_info(Config.MESSAGES['gif_success'].format(save_path))
                self.statusBar().showMessage('✅ GIF 動畫建立完成')
            except Exception as e:
                self.show_error(Config.MESSAGES['save_failed'].format(e))

    def merge_videos(self):
        """合併影片"""
        video_files = self.video_files_list.get_all_files()
        if not video_files:
            self.show_warning(Config.MESSAGES['no_videos_selected'])
            return

        output_filename = self.edit_output_video_name.text()

        if not output_filename:
            self.show_warning(Config.MESSAGES['no_output_filename'])
            return

        video_files = natsorted(video_files)

        clips = []
        try:
            for video_file in video_files:
                clip = VideoFileClip(video_file)
                clips.append(clip)
        except Exception as e:
            self.show_error(Config.MESSAGES['video_read_error'].format(e))
            for loaded_clip in clips:
                loaded_clip.close()
            return

        if not clips:
            self.show_warning(Config.MESSAGES['no_videos_loaded'])
            return

        try:
            self.video_progress_bar.setVisible(True)
            self.video_progress_bar.setRange(0, 0)
            self.statusBar().showMessage('⏳ 正在合併影片，請稍候...')

            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(
                output_filename,
                codec=Config.VIDEO_CODEC,
                audio_codec=Config.AUDIO_CODEC
            )
            self.show_info(Config.MESSAGES['video_merge_success'].format(output_filename))
            self.statusBar().showMessage('✅ 影片合併完成')
        except Exception as e:
            self.show_error(Config.MESSAGES['video_merge_error'].format(e))
        finally:
            for clip in clips:
                clip.close()
            if 'final_clip' in locals() and final_clip:
                final_clip.close()
            self.video_progress_bar.setVisible(False)

    def convert_images(self):
        """轉換圖片格式"""
        files = self.convert_files_list.get_all_files()
        if not files:
            self.show_warning(Config.MESSAGES['no_images_selected'])
            return

        output_format = self.combo_output_format.currentText().lower()
        output_folder = self.edit_output_folder.text()

        if output_folder and not os.path.exists(output_folder):
            os.makedirs(output_folder)

        success_count = 0
        for file_path in files:
            try:
                img = Image.open(file_path)

                base_name = os.path.splitext(os.path.basename(file_path))[0]
                if output_folder:
                    save_path = os.path.join(output_folder, f"{base_name}.{output_format}")
                else:
                    save_path = os.path.join(
                        os.path.dirname(file_path),
                        f"{base_name}.{output_format}"
                    )

                img.save(save_path, format=output_format.upper())
                success_count += 1
            except Exception as e:
                self.show_warning(
                    Config.MESSAGES['file_convert_failed'].format(
                        os.path.basename(file_path), e
                    )
                )

        if success_count > 0:
            target_folder = output_folder if output_folder else '原始資料夾'
            self.show_info(
                Config.MESSAGES['convert_success'].format(success_count, target_folder)
            )
            self.statusBar().showMessage(f'✅ 已轉換 {success_count} 個檔案')
        else:
            self.show_error(Config.MESSAGES['convert_failed'])

    def show_warning(self, message):
        """顯示警告訊息"""
        QMessageBox.warning(self, "⚠️ " + Config.UI_TEXT['warning'], message)

    def show_error(self, message):
        """顯示錯誤訊息"""
        QMessageBox.critical(self, "❌ " + Config.UI_TEXT['error'], message)

    def show_info(self, message):
        """顯示資訊訊息"""
        QMessageBox.information(self, "✅ " + Config.UI_TEXT['completed'], message)


def main():
    """主程式進入點"""
    app = QApplication(sys.argv)

    # 設定應用程式資訊
    app.setApplicationName(Config.APP_NAME)
    app.setApplicationVersion(Config.APP_VERSION)
    app.setOrganizationName(Config.APP_AUTHOR)

    # 建立並顯示主視窗
    window = ModernImageTool()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
