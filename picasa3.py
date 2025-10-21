#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
myPicasa - 圖片與影片整理工具 (改進版)

這是 picasa2.py 的重構版本，具有以下改進：
- 使用獨立的工具模組
- 使用配置管理
- 改善的錯誤處理
- 更好的程式碼組織
"""
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QComboBox, QFileDialog,
    QMessageBox, QTabWidget, QProgressBar
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PIL import Image
from PIL import ImageQt
from moviepy.editor import VideoFileClip, concatenate_videoclips
from natsort import natsorted

# 導入自訂工具模組
from utils import resize_with_padding, resize_image, Config
from utils.image_utils import get_image_info


class ImageTool(QMainWindow):
    """圖片與影片整理工具主視窗"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(Config.get_window_title())
        self.resize(800, 600)
        self._init_ui()
        self._create_actions()
        self._create_menus()

    def _init_ui(self):
        """初始化使用者介面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # 建立分頁視窗
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 建立各個功能分頁
        self._create_image_tab()
        self._create_video_tab()
        self._create_convert_image_tab()

        # 新增狀態列
        self.statusBar().showMessage('準備就緒')

    def _create_image_tab(self):
        """建立圖片處理分頁"""
        image_tab = QWidget()
        image_layout = QVBoxLayout(image_tab)

        # 選擇圖片檔案按鈕
        btn_select = QPushButton(Config.UI_TEXT['select_images'])
        btn_select.clicked.connect(self.select_files)
        image_layout.addWidget(btn_select)

        # 顯示選取檔案的清單
        self.files_list = QListWidget()
        image_layout.addWidget(self.files_list)

        # 網格參數設定
        grid_layout = QHBoxLayout()
        lbl_cols = QLabel("列數 (grid cols):")
        self.edit_cols = QLineEdit(str(Config.DEFAULT_GRID_COLS))
        self.edit_cols.setMaximumWidth(50)
        lbl_rows = QLabel("行數 (grid rows):")
        self.edit_rows = QLineEdit(str(Config.DEFAULT_GRID_ROWS))
        self.edit_rows.setMaximumWidth(50)
        grid_layout.addWidget(lbl_cols)
        grid_layout.addWidget(self.edit_cols)
        grid_layout.addWidget(lbl_rows)
        grid_layout.addWidget(self.edit_rows)
        grid_layout.addStretch()
        image_layout.addLayout(grid_layout)

        # 縮放策略選擇
        strategy_layout = QHBoxLayout()
        lbl_strategy = QLabel("縮放策略:")
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(Config.RESIZE_STRATEGIES)
        strategy_layout.addWidget(lbl_strategy)
        strategy_layout.addWidget(self.combo_strategy)
        strategy_layout.addStretch()
        image_layout.addLayout(strategy_layout)

        # 拼接與預覽按鈕
        action_layout = QHBoxLayout()
        btn_merge = QPushButton(Config.UI_TEXT['merge_images'])
        btn_merge.clicked.connect(self.merge_images)
        action_layout.addWidget(btn_merge)
        action_layout.addStretch()
        image_layout.addLayout(action_layout)

        # GIF 動畫參數與生成按鈕
        gif_layout = QHBoxLayout()
        lbl_duration = QLabel("動畫持續時間 (ms):")
        self.edit_duration = QLineEdit(str(Config.DEFAULT_GIF_DURATION))
        self.edit_duration.setMaximumWidth(80)
        btn_gif = QPushButton(Config.UI_TEXT['create_gif'])
        btn_gif.clicked.connect(self.create_gif)
        gif_layout.addWidget(lbl_duration)
        gif_layout.addWidget(self.edit_duration)
        gif_layout.addWidget(btn_gif)
        gif_layout.addStretch()
        image_layout.addLayout(gif_layout)

        # 圖片預覽區域
        self.image_label = QLabel(image_tab)
        image_layout.addWidget(self.image_label)

        self.tab_widget.addTab(image_tab, "圖片處理")

    def _create_video_tab(self):
        """建立影片處理分頁"""
        video_tab = QWidget()
        video_layout = QVBoxLayout(video_tab)

        # 影片合併控制區
        video_controls_layout = QHBoxLayout()
        btn_select_videos = QPushButton(Config.UI_TEXT['select_videos'])
        btn_select_videos.clicked.connect(self.select_video_files)
        self.edit_output_video_name = QLineEdit("merged_video.mp4")
        self.edit_output_video_name.setPlaceholderText("輸出影片檔名 (e.g., merged_video.mp4)")
        btn_merge_videos = QPushButton(Config.UI_TEXT['merge_videos'])
        btn_merge_videos.clicked.connect(self.merge_videos)
        video_controls_layout.addWidget(btn_select_videos)
        video_controls_layout.addWidget(self.edit_output_video_name)
        video_controls_layout.addWidget(btn_merge_videos)
        video_controls_layout.addStretch()
        video_layout.addLayout(video_controls_layout)

        # 影片檔案清單
        self.video_files_list = QListWidget()
        video_layout.addWidget(self.video_files_list)

        # 進度條
        self.video_progress_bar = QProgressBar()
        self.video_progress_bar.setVisible(False)
        video_layout.addWidget(self.video_progress_bar)

        self.tab_widget.addTab(video_tab, "影片處理")

    def _create_convert_image_tab(self):
        """建立圖片格式轉換分頁"""
        convert_image_tab = QWidget()
        convert_image_layout = QVBoxLayout(convert_image_tab)

        # 選擇圖片檔案按鈕
        btn_select_convert_images = QPushButton(Config.UI_TEXT['select_convert_images'])
        btn_select_convert_images.clicked.connect(self.select_convert_images)
        convert_image_layout.addWidget(btn_select_convert_images)

        # 顯示選取檔案的清單
        self.convert_files_list = QListWidget()
        convert_image_layout.addWidget(self.convert_files_list)

        # 輸出格式選擇
        output_format_layout = QHBoxLayout()
        lbl_output_format = QLabel("輸出格式:")
        self.combo_output_format = QComboBox()
        self.combo_output_format.addItems(Config.SUPPORTED_IMAGE_FORMATS)
        output_format_layout.addWidget(lbl_output_format)
        output_format_layout.addWidget(self.combo_output_format)
        output_format_layout.addStretch()
        convert_image_layout.addLayout(output_format_layout)

        # 輸出資料夾
        output_folder_layout = QHBoxLayout()
        lbl_output_folder = QLabel("輸出資料夾:")
        self.edit_output_folder = QLineEdit("converted_images")
        self.edit_output_folder.setPlaceholderText("輸出資料夾 (留空則儲存至原資料夾)")
        btn_browse_output_folder = QPushButton(Config.UI_TEXT['browse'])
        btn_browse_output_folder.clicked.connect(self.browse_output_folder)
        output_folder_layout.addWidget(lbl_output_folder)
        output_folder_layout.addWidget(self.edit_output_folder)
        output_folder_layout.addWidget(btn_browse_output_folder)
        output_folder_layout.addStretch()
        convert_image_layout.addLayout(output_folder_layout)

        # 開始轉換按鈕
        btn_convert_images = QPushButton(Config.UI_TEXT['convert_images'])
        btn_convert_images.clicked.connect(self.convert_images)
        convert_image_layout.addWidget(btn_convert_images)

        self.tab_widget.addTab(convert_image_tab, "圖片格式轉換")

    def _create_actions(self):
        """建立選單動作"""
        from PyQt5.QtWidgets import QAction
        self.open_action = QAction("打開", self)
        self.open_action.triggered.connect(self.open_image)

    def _create_menus(self):
        """建立選單"""
        menu = self.menuBar().addMenu("文件")
        menu.addAction(self.open_action)

    def open_image(self):
        """開啟單一圖片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打開圖片", "", Config.IMAGE_FILE_FILTER
        )
        if file_path:
            try:
                self.image = Image.open(file_path)
                self.show_image()
                self.statusBar().showMessage(f'已開啟: {os.path.basename(file_path)}')
            except Exception as e:
                self.show_error(Config.MESSAGES['image_read_failed'].format(e))

    def show_image(self):
        """顯示圖片"""
        qimage = ImageQt.ImageQt(self.image)
        pixmap = QPixmap.fromImage(qimage)
        self.image_label.setPixmap(pixmap)

    def select_files(self):
        """選擇圖片檔案"""
        files, _ = QFileDialog.getOpenFileNames(
            self, Config.UI_TEXT['select_images'], "",
            Config.IMAGE_FILE_FILTER
        )
        if files:
            self.files_list.clear()
            for file in files:
                self.files_list.addItem(file)
            self.statusBar().showMessage(f'已選擇 {len(files)} 個圖片檔案')

    def select_video_files(self):
        """選擇影片檔案"""
        videos, _ = QFileDialog.getOpenFileNames(
            self, Config.UI_TEXT['select_videos'], "",
            Config.VIDEO_FILE_FILTER
        )
        if videos:
            self.video_files_list.clear()
            for video in videos:
                self.video_files_list.addItem(video)
            self.statusBar().showMessage(f'已選擇 {len(videos)} 個影片檔案')

    def select_convert_images(self):
        """選擇要轉換的圖片檔案"""
        files, _ = QFileDialog.getOpenFileNames(
            self, Config.UI_TEXT['select_convert_images'], "",
            Config.IMAGE_FILE_FILTER
        )
        if files:
            self.convert_files_list.clear()
            for file in files:
                self.convert_files_list.addItem(file)
            self.statusBar().showMessage(f'已選擇 {len(files)} 個圖片檔案待轉換')

    def browse_output_folder(self):
        """瀏覽輸出資料夾"""
        folder_path = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if folder_path:
            self.edit_output_folder.setText(folder_path)

    def generate_merged_image(self):
        """產生拼接圖片"""
        count = self.files_list.count()
        if count == 0:
            self.show_warning(Config.MESSAGES['no_images_selected'])
            return None

        try:
            grid_cols = int(self.edit_cols.text())
            grid_rows = int(self.edit_rows.text())
        except ValueError:
            self.show_error(Config.MESSAGES['invalid_number_format'])
            return None

        # 讀取所有圖片
        paths = [self.files_list.item(i).text() for i in range(count)]
        try:
            images = [Image.open(p) for p in paths]
        except Exception as e:
            self.show_error(Config.MESSAGES['image_read_failed'].format(e))
            return None

        # 使用所有圖片中最小的尺寸作為目標尺寸
        min_width = min(img.width for img in images)
        min_height = min(img.height for img in images)
        cell_width, cell_height = min_width, min_height

        # 設定間隔與邊框
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
                self.statusBar().showMessage('圖片拼接完成')
            except Exception as e:
                self.show_error(Config.MESSAGES['save_failed'].format(e))

    def create_gif(self):
        """建立 GIF 動畫"""
        count = self.files_list.count()
        if count == 0:
            self.show_warning(Config.MESSAGES['no_images_selected'])
            return

        try:
            duration = int(self.edit_duration.text())
        except ValueError:
            self.show_error(Config.MESSAGES['invalid_duration'])
            return

        paths = [self.files_list.item(i).text() for i in range(count)]
        try:
            images = [Image.open(p) for p in paths]
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
                self.statusBar().showMessage('GIF 動畫建立完成')
            except Exception as e:
                self.show_error(Config.MESSAGES['save_failed'].format(e))

    def merge_videos(self):
        """合併影片"""
        count = self.video_files_list.count()
        if count == 0:
            self.show_warning(Config.MESSAGES['no_videos_selected'])
            return

        video_files = [self.video_files_list.item(i).text() for i in range(count)]
        output_filename = self.edit_output_video_name.text()

        if not output_filename:
            self.show_warning(Config.MESSAGES['no_output_filename'])
            return

        # 使用自然排序
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
            self.show_info(Config.MESSAGES['video_merge_start'])
            self.video_progress_bar.setVisible(True)
            self.video_progress_bar.setRange(0, 0)  # 不確定進度

            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(
                output_filename,
                codec=Config.VIDEO_CODEC,
                audio_codec=Config.AUDIO_CODEC
            )
            self.show_info(Config.MESSAGES['video_merge_success'].format(output_filename))
            self.statusBar().showMessage('影片合併完成')
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
        count = self.convert_files_list.count()
        if count == 0:
            self.show_warning(Config.MESSAGES['no_images_selected'])
            return

        output_format = self.combo_output_format.currentText().lower()
        output_folder = self.edit_output_folder.text()

        if output_folder and not os.path.exists(output_folder):
            os.makedirs(output_folder)

        success_count = 0
        for i in range(count):
            file_path = self.convert_files_list.item(i).text()
            try:
                img = Image.open(file_path)

                # 構建輸出檔案路徑
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
            self.statusBar().showMessage(f'已轉換 {success_count} 個檔案')
        else:
            self.show_error(Config.MESSAGES['convert_failed'])

    def show_warning(self, message):
        """顯示警告訊息"""
        QMessageBox.warning(self, Config.UI_TEXT['warning'], message)

    def show_error(self, message):
        """顯示錯誤訊息"""
        QMessageBox.critical(self, Config.UI_TEXT['error'], message)

    def show_info(self, message):
        """顯示資訊訊息"""
        QMessageBox.information(self, Config.UI_TEXT['completed'], message)


def main():
    """主程式進入點"""
    app = QApplication(sys.argv)
    window = ImageTool()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
