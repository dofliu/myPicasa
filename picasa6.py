#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MediaToolkit - 多媒體與文檔處理工具套件 v6.0
整合圖片影像處理 + 文件轉換功能
"""
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QComboBox, QFileDialog,
    QMessageBox, QTabWidget, QProgressBar, QGroupBox, QAction
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PIL import Image
from moviepy.editor import VideoFileClip, concatenate_videoclips
from natsort import natsorted

from utils import (
    resize_with_padding, resize_image, Config,
    DragDropListWidget, ImagePreviewGrid, ImageViewerDialog,
    add_watermark, convert_word_to_pdf, convert_pdf_to_word,
    merge_pdfs, get_pdf_info, check_dependencies
)
from utils.modern_style import ModernStyle


class MediaToolkit(QMainWindow):
    """多媒體與文檔處理工具套件"""

    def __init__(self):
        super().__init__()
        self.current_theme = "light"
        self._group_boxes = []
        self.setWindowTitle("📦 MediaToolkit v6.0 - 多媒體與文檔處理工具套件")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 700)
        self.doc_deps = check_dependencies()
        self._init_ui()
        self._create_menus()
        self._apply_theme(self.current_theme)

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
        
        self.statusBar().showMessage('🎉 MediaToolkit 已就緒！')

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

        # 操作按鈕
        action_layout = QHBoxLayout()
        btn_merge = QPushButton("🖼️ 拼接圖片")
        btn_merge.clicked.connect(self.merge_images)
        btn_merge.setMinimumHeight(44)
        action_layout.addWidget(btn_merge)
        
        btn_gif = QPushButton("🎞️ 生成 GIF")
        btn_gif.clicked.connect(self.create_gif)
        btn_gif.setMinimumHeight(44)
        action_layout.addWidget(btn_gif)
        
        btn_watermark = QPushButton("🏷️ 添加浮水印")
        btn_watermark.clicked.connect(self._add_watermark)
        btn_watermark.setMinimumHeight(44)
        action_layout.addWidget(btn_watermark)
        
        layout.addLayout(action_layout)
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
        
        self.video_progress = QProgressBar()
        self.video_progress.setVisible(False)
        layout.addWidget(self.video_progress)
        
        btn_merge = QPushButton("🎬 合併影片")
        btn_merge.clicked.connect(self.merge_videos)
        btn_merge.setMinimumHeight(44)
        layout.addWidget(btn_merge)
        
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
        
        btn = QPushButton("✨ 開始轉換")
        btn.clicked.connect(self.convert_images)
        btn.setMinimumHeight(44)
        layout.addWidget(btn)
        
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
        file_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        btn = QPushButton("📂 選擇 PDF")
        btn.clicked.connect(self._select_pdfs)
        btn.setMinimumHeight(40)
        btn_layout.addWidget(btn)
        btn_layout.addStretch()
        file_layout.addLayout(btn_layout)
        
        self.pdf_list = DragDropListWidget(file_extensions=['.pdf'])
        self.pdf_list.files_dropped.connect(self._on_pdf_dropped)
        file_layout.addWidget(self.pdf_list)
        group.setLayout(file_layout)
        layout.addWidget(group)
        
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

    def _apply_theme(self, theme):
        """套用主題"""
        stylesheet = ModernStyle.get_dark_stylesheet() if theme == "dark" else ModernStyle.get_light_stylesheet()
        self.setStyleSheet(stylesheet)
        card_style = ModernStyle.get_card_style(theme)
        for group in self._group_boxes:
            group.setStyleSheet(card_style)

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
        files = self.image_preview.get_files()
        if not files:
            self.show_warning("請先選擇圖片")
            return
        try:
            duration = int(self.edit_duration.text())
        except:
            duration = Config.DEFAULT_GIF_DURATION
        
        images = [Image.open(p) for p in files]
        min_w = min(img.width for img in images)
        min_h = min(img.height for img in images)
        strategy = self.combo_strategy.currentText()
        frames = [resize_image(img, (min_w, min_h), strategy) for img in images]
        
        path, _ = QFileDialog.getSaveFileName(self, "儲存 GIF", "", Config.get_save_gif_filter())
        if path:
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=duration, loop=0)
            self.show_info(f"GIF 建立完成！\n{path}")

    def merge_videos(self):
        files = self.video_files_list.get_all_files()
        if not files:
            self.show_warning("請先選擇影片")
            return
        output = self.edit_output_video.text()
        if not output:
            self.show_warning("請輸入輸出檔名")
            return
        
        files = natsorted(files)
        clips = [VideoFileClip(f) for f in files]
        
        self.video_progress.setVisible(True)
        self.video_progress.setRange(0, 0)
        
        try:
            final = concatenate_videoclips(clips, method="compose")
            final.write_videofile(output, codec=Config.VIDEO_CODEC, audio_codec=Config.AUDIO_CODEC)
            self.show_info(f"影片合併完成！\n{output}")
        except Exception as e:
            self.show_error(f"合併失敗：{e}")
        finally:
            for clip in clips:
                clip.close()
            self.video_progress.setVisible(False)

    def convert_images(self):
        files = self.convert_list.get_all_files()
        if not files:
            self.show_warning("請先選擇圖片")
            return
        
        fmt = self.combo_output_format.currentText().lower()
        folder = self.edit_output_folder.text()
        if folder and not os.path.exists(folder):
            os.makedirs(folder)
        
        count = 0
        for file in files:
            try:
                img = Image.open(file)
                base = os.path.splitext(os.path.basename(file))[0]
                if folder:
                    save_path = os.path.join(folder, f"{base}.{fmt}")
                else:
                    save_path = os.path.join(os.path.dirname(file), f"{base}.{fmt}")
                img.save(save_path, format=fmt.upper())
                count += 1
            except Exception as e:
                print(f"轉換失敗：{file} - {e}")
        
        if count > 0:
            self.show_info(f"成功轉換 {count} 個檔案！")

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

    def _merge_pdfs(self):
        files = self.pdf_list.get_all_files()
        if not files:
            self.show_warning("請先選擇 PDF 文件")
            return
        output, _ = QFileDialog.getSaveFileName(self, "儲存 PDF", "", "PDF (*.pdf)")
        if output:
            if merge_pdfs(files, output):
                self.show_info(f"合併成功！\n{output}")
            else:
                self.show_error("PDF 合併失敗")

    def show_about(self):
        QMessageBox.about(self, "關於 MediaToolkit",
            "<h2>📦 MediaToolkit v6.0</h2>"
            "<p>多媒體與文檔處理工具套件</p>"
            "<p>整合圖片、影片與文檔處理功能</p>"
            "<p style='color:#64748B;'>© 2025</p>")

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
