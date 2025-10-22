"""
浮水印功能模組
提供文字和圖片浮水印功能，支援批次處理
"""
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QSpinBox, QSlider, QGroupBox,
    QRadioButton, QButtonGroup, QFileDialog, QProgressDialog,
    QColorDialog, QMessageBox, QTabWidget, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PIL import Image, ImageDraw, ImageFont


class WatermarkDialog(QDialog):
    """浮水印設定對話框"""

    def __init__(self, files, parent=None):
        super().__init__(parent)
        self.files = files
        self.watermark_type = "text"  # "text" or "image"
        self.text_color = QColor(255, 255, 255)  # 預設白色

        self.setWindowTitle("🏷️ 添加浮水印")
        self.resize(600, 500)
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 標題
        title = QLabel(f"為 {len(self.files)} 個圖片添加浮水印")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #3B82F6;")
        layout.addWidget(title)

        # 分頁視窗（文字浮水印 / 圖片浮水印）
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._create_text_tab(), "📝 文字浮水印")
        self.tab_widget.addTab(self._create_image_tab(), "🖼️ 圖片浮水印")
        layout.addWidget(self.tab_widget)

        # 通用設定
        common_group = QGroupBox("⚙️ 通用設定")
        common_layout = QVBoxLayout()

        # 位置選擇
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("浮水印位置:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "左上角", "上方中央", "右上角",
            "左側中央", "正中央", "右側中央",
            "左下角", "下方中央", "右下角"
        ])
        self.position_combo.setCurrentText("右下角")
        position_layout.addWidget(self.position_combo)
        position_layout.addStretch()
        common_layout.addLayout(position_layout)

        # 透明度
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("透明度:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(70)
        self.opacity_slider.valueChanged.connect(self._update_opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("70%")
        self.opacity_label.setFixedWidth(50)
        opacity_layout.addWidget(self.opacity_label)
        common_layout.addLayout(opacity_layout)

        # 邊距
        margin_layout = QHBoxLayout()
        margin_layout.addWidget(QLabel("邊距 (px):"))
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 200)
        self.margin_spin.setValue(20)
        self.margin_spin.setMaximumWidth(100)
        margin_layout.addWidget(self.margin_spin)
        margin_layout.addStretch()
        common_layout.addLayout(margin_layout)

        common_group.setLayout(common_layout)
        layout.addWidget(common_group)

        # 輸出設定
        output_group = QGroupBox("💾 輸出設定")
        output_layout = QVBoxLayout()

        # 儲存選項
        save_layout = QHBoxLayout()
        self.overwrite_radio = QRadioButton("覆蓋原檔案")
        self.new_folder_radio = QRadioButton("儲存到新資料夾")
        self.new_folder_radio.setChecked(True)

        self.save_group = QButtonGroup()
        self.save_group.addButton(self.overwrite_radio)
        self.save_group.addButton(self.new_folder_radio)

        save_layout.addWidget(self.overwrite_radio)
        save_layout.addWidget(self.new_folder_radio)
        save_layout.addStretch()
        output_layout.addLayout(save_layout)

        # 輸出資料夾
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("輸出資料夾:"))
        self.output_folder_edit = QLineEdit("watermarked_images")
        folder_layout.addWidget(self.output_folder_edit)

        browse_btn = QPushButton("📂 瀏覽")
        browse_btn.setProperty("secondary", True)
        browse_btn.clicked.connect(self._browse_output_folder)
        folder_layout.addWidget(browse_btn)
        output_layout.addLayout(folder_layout)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # 按鈕列
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("✨ 套用浮水印")
        apply_btn.clicked.connect(self._apply_watermark)
        button_layout.addWidget(apply_btn)

        layout.addLayout(button_layout)

    def _create_text_tab(self):
        """建立文字浮水印分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 文字內容
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("浮水印文字:"))
        self.text_edit = QLineEdit("© 2025 My Watermark")
        self.text_edit.setPlaceholderText("輸入浮水印文字...")
        text_layout.addWidget(self.text_edit)
        layout.addLayout(text_layout)

        # 字體大小
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("字體大小:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 200)
        self.font_size_spin.setValue(36)
        self.font_size_spin.setMaximumWidth(100)
        size_layout.addWidget(self.font_size_spin)
        size_layout.addStretch()
        layout.addLayout(size_layout)

        # 文字顏色
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("文字顏色:"))
        self.color_btn = QPushButton("選擇顏色")
        self.color_btn.setProperty("secondary", True)
        self.color_btn.clicked.connect(self._choose_color)
        self.color_btn.setStyleSheet(f"background-color: {self.text_color.name()}; color: black;")
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        layout.addLayout(color_layout)

        layout.addStretch()
        return tab

    def _create_image_tab(self):
        """建立圖片浮水印分頁"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 選擇浮水印圖片
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("浮水印圖片:"))
        self.watermark_image_edit = QLineEdit()
        self.watermark_image_edit.setPlaceholderText("選擇浮水印圖片（PNG 格式，支援透明背景）")
        file_layout.addWidget(self.watermark_image_edit)

        browse_img_btn = QPushButton("📂 選擇")
        browse_img_btn.setProperty("secondary", True)
        browse_img_btn.clicked.connect(self._browse_watermark_image)
        file_layout.addWidget(browse_img_btn)
        layout.addLayout(file_layout)

        # 縮放比例
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("縮放比例:"))
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(5, 100)
        self.scale_slider.setValue(20)
        self.scale_slider.valueChanged.connect(self._update_scale_label)
        scale_layout.addWidget(self.scale_slider)
        self.scale_label = QLabel("20%")
        self.scale_label.setFixedWidth(50)
        scale_layout.addWidget(self.scale_label)
        layout.addLayout(scale_layout)

        layout.addStretch()
        return tab

    def _browse_output_folder(self):
        """瀏覽輸出資料夾"""
        folder = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if folder:
            self.output_folder_edit.setText(folder)

    def _browse_watermark_image(self):
        """選擇浮水印圖片"""
        file, _ = QFileDialog.getOpenFileName(
            self, "選擇浮水印圖片", "",
            "圖片檔案 (*.png *.jpg *.jpeg *.bmp)"
        )
        if file:
            self.watermark_image_edit.setText(file)

    def _choose_color(self):
        """選擇文字顏色"""
        color = QColorDialog.getColor(self.text_color, self, "選擇文字顏色")
        if color.isValid():
            self.text_color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; color: black;")

    def _update_opacity_label(self, value):
        """更新透明度標籤"""
        self.opacity_label.setText(f"{value}%")

    def _update_scale_label(self, value):
        """更新縮放比例標籤"""
        self.scale_label.setText(f"{value}%")

    def _get_position_offset(self, img_width, img_height, wm_width, wm_height):
        """根據位置選擇計算偏移量"""
        margin = self.margin_spin.value()
        position = self.position_combo.currentText()

        # 計算 x 座標
        if "左" in position:
            x = margin
        elif "右" in position:
            x = img_width - wm_width - margin
        else:  # 中央
            x = (img_width - wm_width) // 2

        # 計算 y 座標
        if "上" in position:
            y = margin
        elif "下" in position:
            y = img_height - wm_height - margin
        else:  # 中央
            y = (img_height - wm_height) // 2

        return (x, y)

    def _apply_text_watermark(self, img):
        """套用文字浮水印"""
        # 建立透明圖層
        watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)

        # 載入字體
        text = self.text_edit.text()
        font_size = self.font_size_spin.value()

        try:
            # 嘗試使用系統字體
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                # Windows 中文字體
                font = ImageFont.truetype("msyh.ttc", font_size)
            except:
                # 使用預設字體
                font = ImageFont.load_default()

        # 計算文字大小
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 計算位置
        position = self._get_position_offset(img.width, img.height, text_width, text_height)

        # 計算顏色和透明度
        opacity = int(255 * self.opacity_slider.value() / 100)
        color = (
            self.text_color.red(),
            self.text_color.green(),
            self.text_color.blue(),
            opacity
        )

        # 繪製文字
        draw.text(position, text, font=font, fill=color)

        # 合併圖層
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        result = Image.alpha_composite(img, watermark)

        # 轉回 RGB（如果需要）
        if result.mode == 'RGBA':
            rgb_img = Image.new('RGB', result.size, (255, 255, 255))
            rgb_img.paste(result, mask=result.split()[3])
            return rgb_img

        return result

    def _apply_image_watermark(self, img):
        """套用圖片浮水印"""
        watermark_path = self.watermark_image_edit.text()

        if not watermark_path or not os.path.exists(watermark_path):
            raise ValueError("請選擇有效的浮水印圖片")

        # 載入浮水印圖片
        watermark = Image.open(watermark_path)

        # 確保浮水印有透明通道
        if watermark.mode != 'RGBA':
            watermark = watermark.convert('RGBA')

        # 計算縮放大小
        scale = self.scale_slider.value() / 100
        wm_width = int(img.width * scale)
        wm_height = int(watermark.height * wm_width / watermark.width)
        watermark = watermark.resize((wm_width, wm_height), Image.Resampling.LANCZOS)

        # 調整透明度
        opacity = self.opacity_slider.value() / 100
        if opacity < 1.0:
            alpha = watermark.split()[3]
            alpha = alpha.point(lambda p: int(p * opacity))
            watermark.putalpha(alpha)

        # 計算位置
        position = self._get_position_offset(img.width, img.height, wm_width, wm_height)

        # 貼上浮水印
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        img.paste(watermark, position, watermark)

        # 轉回 RGB
        if img.mode == 'RGBA':
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])
            return rgb_img

        return img

    def _apply_watermark(self):
        """套用浮水印到所有圖片"""
        # 決定使用哪種浮水印
        is_text_tab = self.tab_widget.currentIndex() == 0

        # 驗證輸入
        if is_text_tab:
            if not self.text_edit.text().strip():
                QMessageBox.warning(self, "警告", "請輸入浮水印文字")
                return
        else:
            if not self.watermark_image_edit.text():
                QMessageBox.warning(self, "警告", "請選擇浮水印圖片")
                return

        # 確定輸出路徑
        if self.new_folder_radio.isChecked():
            output_folder = self.output_folder_edit.text()
            if not output_folder:
                QMessageBox.warning(self, "警告", "請指定輸出資料夾")
                return
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

        # 建立進度對話框
        progress = QProgressDialog("正在處理浮水印...", "取消", 0, len(self.files), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("處理中")

        success_count = 0

        for i, file_path in enumerate(self.files):
            if progress.wasCanceled():
                break

            progress.setValue(i)
            progress.setLabelText(f"正在處理: {os.path.basename(file_path)}")

            try:
                # 載入圖片
                img = Image.open(file_path)

                # 套用浮水印
                if is_text_tab:
                    result = self._apply_text_watermark(img)
                else:
                    result = self._apply_image_watermark(img)

                # 儲存結果
                if self.overwrite_radio.isChecked():
                    save_path = file_path
                else:
                    filename = os.path.basename(file_path)
                    save_path = os.path.join(self.output_folder_edit.text(), filename)

                result.save(save_path)
                success_count += 1

            except Exception as e:
                print(f"處理 {file_path} 時發生錯誤: {e}")

        progress.setValue(len(self.files))

        # 顯示結果
        if success_count > 0:
            QMessageBox.information(
                self,
                "完成",
                f"成功處理 {success_count}/{len(self.files)} 個圖片"
            )
            self.accept()
        else:
            QMessageBox.warning(self, "警告", "沒有成功處理任何圖片")


def add_watermark(files, parent=None):
    """
    為圖片添加浮水印（入口函數）

    Args:
        files: 圖片檔案路徑列表
        parent: 父視窗

    Returns:
        bool: 是否成功添加浮水印
    """
    if not files:
        return False

    dialog = WatermarkDialog(files, parent)
    return dialog.exec_() == QDialog.Accepted
