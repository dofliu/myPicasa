"""
圖片編輯工具模組
提供旋轉、翻轉、調整大小等基礎編輯功能
"""
import os
from PIL import Image
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QGroupBox,
    QMessageBox, QButtonGroup, QRadioButton
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt


class ImageEditorDialog(QDialog):
    """圖片編輯對話框"""

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.original_image = Image.open(file_path)
        self.edited_image = self.original_image.copy()

        self.setWindowTitle(f"編輯圖片 - {os.path.basename(file_path)}")
        self.resize(800, 700)
        self._init_ui()
        self._update_preview()

    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)

        # 標題
        title = QLabel("🎨 圖片編輯工具")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #3B82F6;")
        main_layout.addWidget(title)

        # 預覽區
        preview_group = QGroupBox("預覽")
        preview_layout = QVBoxLayout()

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(700, 400)
        self.preview_label.setStyleSheet("border: 2px solid #E2E8F0; background: white;")
        preview_layout.addWidget(self.preview_label)

        # 圖片資訊
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #64748B; font-size: 9pt;")
        preview_layout.addWidget(self.info_label)

        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)

        # 編輯工具區
        tools_group = QGroupBox("編輯工具")
        tools_layout = QVBoxLayout()

        # 旋轉工具
        rotate_layout = QHBoxLayout()
        rotate_layout.addWidget(QLabel("🔄 旋轉:"))

        btn_rotate_90_cw = QPushButton("順時針 90°")
        btn_rotate_90_cw.clicked.connect(lambda: self._rotate(90))
        rotate_layout.addWidget(btn_rotate_90_cw)

        btn_rotate_90_ccw = QPushButton("逆時針 90°")
        btn_rotate_90_ccw.clicked.connect(lambda: self._rotate(-90))
        rotate_layout.addWidget(btn_rotate_90_ccw)

        btn_rotate_180 = QPushButton("180°")
        btn_rotate_180.clicked.connect(lambda: self._rotate(180))
        rotate_layout.addWidget(btn_rotate_180)

        rotate_layout.addStretch()
        tools_layout.addLayout(rotate_layout)

        # 翻轉工具
        flip_layout = QHBoxLayout()
        flip_layout.addWidget(QLabel("↔️ 翻轉:"))

        btn_flip_h = QPushButton("水平翻轉")
        btn_flip_h.clicked.connect(lambda: self._flip('horizontal'))
        flip_layout.addWidget(btn_flip_h)

        btn_flip_v = QPushButton("垂直翻轉")
        btn_flip_v.clicked.connect(lambda: self._flip('vertical'))
        flip_layout.addWidget(btn_flip_v)

        flip_layout.addStretch()
        tools_layout.addLayout(flip_layout)

        # 重置按鈕
        reset_layout = QHBoxLayout()
        btn_reset = QPushButton("🔙 重置為原始圖片")
        btn_reset.setProperty("secondary", True)
        btn_reset.clicked.connect(self._reset)
        reset_layout.addWidget(btn_reset)
        reset_layout.addStretch()
        tools_layout.addLayout(reset_layout)

        tools_group.setLayout(tools_layout)
        main_layout.addWidget(tools_group)

        # 按鈕區
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("✅ 儲存變更")
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)

        main_layout.addLayout(button_layout)

    def _rotate(self, angle):
        """旋轉圖片"""
        # PIL的rotate是逆時針，所以要取負值
        self.edited_image = self.edited_image.rotate(-angle, expand=True)
        self._update_preview()

    def _flip(self, direction):
        """翻轉圖片"""
        if direction == 'horizontal':
            self.edited_image = self.edited_image.transpose(Image.FLIP_LEFT_RIGHT)
        elif direction == 'vertical':
            self.edited_image = self.edited_image.transpose(Image.FLIP_TOP_BOTTOM)
        self._update_preview()

    def _reset(self):
        """重置為原始圖片"""
        self.edited_image = self.original_image.copy()
        self._update_preview()

    def _update_preview(self):
        """更新預覽"""
        # 獲取圖片資訊
        width, height = self.edited_image.size
        mode = self.edited_image.mode
        self.info_label.setText(f"尺寸: {width} × {height} px  |  模式: {mode}")

        # 建立縮圖用於預覽
        preview_image = self.edited_image.copy()
        preview_image.thumbnail((680, 380), Image.Resampling.LANCZOS)

        # 轉換為 QPixmap
        if preview_image.mode == "RGB":
            qimage = QImage(
                preview_image.tobytes(),
                preview_image.width,
                preview_image.height,
                QImage.Format_RGB888
            )
        elif preview_image.mode == "RGBA":
            qimage = QImage(
                preview_image.tobytes(),
                preview_image.width,
                preview_image.height,
                QImage.Format_RGBA8888
            )
        else:
            preview_image = preview_image.convert("RGB")
            qimage = QImage(
                preview_image.tobytes(),
                preview_image.width,
                preview_image.height,
                QImage.Format_RGB888
            )

        pixmap = QPixmap.fromImage(qimage)
        self.preview_label.setPixmap(pixmap)

    def _save(self):
        """儲存變更"""
        try:
            # 儲存到原檔案
            self.edited_image.save(self.file_path)

            QMessageBox.information(
                self,
                "儲存成功",
                f"圖片已成功儲存！\n{os.path.basename(self.file_path)}"
            )
            self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "儲存失敗",
                f"儲存圖片時發生錯誤：\n{str(e)}"
            )

    def get_edited_image(self):
        """取得編輯後的圖片"""
        return self.edited_image


class BatchImageEditorDialog(QDialog):
    """批次圖片編輯對話框"""

    def __init__(self, file_paths, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.setWindowTitle("批次圖片編輯")
        self.resize(500, 400)
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)

        # 標題
        title = QLabel("🎨 批次圖片編輯工具")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #3B82F6;")
        main_layout.addWidget(title)

        info_label = QLabel(f"選擇的檔案數: {len(self.file_paths)}")
        info_label.setStyleSheet("color: #64748B;")
        main_layout.addWidget(info_label)

        # 旋轉選項
        rotate_group = QGroupBox("🔄 旋轉")
        rotate_layout = QVBoxLayout()

        self.rotate_button_group = QButtonGroup()

        self.rotate_none = QRadioButton("不旋轉")
        self.rotate_none.setChecked(True)
        self.rotate_button_group.addButton(self.rotate_none)
        rotate_layout.addWidget(self.rotate_none)

        self.rotate_90_cw = QRadioButton("順時針旋轉 90°")
        self.rotate_button_group.addButton(self.rotate_90_cw)
        rotate_layout.addWidget(self.rotate_90_cw)

        self.rotate_90_ccw = QRadioButton("逆時針旋轉 90°")
        self.rotate_button_group.addButton(self.rotate_90_ccw)
        rotate_layout.addWidget(self.rotate_90_ccw)

        self.rotate_180 = QRadioButton("旋轉 180°")
        self.rotate_button_group.addButton(self.rotate_180)
        rotate_layout.addWidget(self.rotate_180)

        rotate_group.setLayout(rotate_layout)
        main_layout.addWidget(rotate_group)

        # 翻轉選項
        flip_group = QGroupBox("↔️ 翻轉")
        flip_layout = QVBoxLayout()

        self.flip_horizontal = QCheckBox("水平翻轉")
        flip_layout.addWidget(self.flip_horizontal)

        self.flip_vertical = QCheckBox("垂直翻轉")
        flip_layout.addWidget(self.flip_vertical)

        flip_group.setLayout(flip_layout)
        main_layout.addWidget(flip_group)

        main_layout.addStretch()

        # 按鈕區
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("✅ 套用到所有圖片")
        apply_btn.clicked.connect(self._apply_edits)
        button_layout.addWidget(apply_btn)

        main_layout.addLayout(button_layout)

    def _apply_edits(self):
        """套用編輯到所有圖片"""
        # 確認對話框
        reply = QMessageBox.question(
            self,
            "確認批次編輯",
            f"確定要對 {len(self.file_paths)} 個圖片套用編輯嗎？\n此操作將覆蓋原始檔案！",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        success_count = 0
        errors = []

        for file_path in self.file_paths:
            try:
                img = Image.open(file_path)

                # 套用旋轉
                if self.rotate_90_cw.isChecked():
                    img = img.rotate(-90, expand=True)
                elif self.rotate_90_ccw.isChecked():
                    img = img.rotate(90, expand=True)
                elif self.rotate_180.isChecked():
                    img = img.rotate(180, expand=True)

                # 套用翻轉
                if self.flip_horizontal.isChecked():
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                if self.flip_vertical.isChecked():
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)

                # 儲存
                img.save(file_path)
                success_count += 1

            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")

        # 顯示結果
        if errors:
            error_msg = "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n... 還有 {len(errors) - 10} 個錯誤"

            QMessageBox.warning(
                self,
                "批次編輯部分失敗",
                f"成功: {success_count} 個\n失敗: {len(errors)} 個\n\n錯誤:\n{error_msg}"
            )
        else:
            QMessageBox.information(
                self,
                "批次編輯完成",
                f"成功編輯 {success_count} 個圖片！"
            )

        if success_count > 0:
            self.accept()


def edit_image(file_path, parent=None):
    """
    編輯單一圖片

    Args:
        file_path: 圖片檔案路徑
        parent: 父視窗

    Returns:
        是否成功編輯
    """
    dialog = ImageEditorDialog(file_path, parent)
    return dialog.exec_() == QDialog.Accepted


def batch_edit_images(file_paths, parent=None):
    """
    批次編輯圖片

    Args:
        file_paths: 圖片檔案路徑列表
        parent: 父視窗

    Returns:
        是否成功編輯
    """
    if not file_paths:
        QMessageBox.warning(parent, "警告", "沒有選擇任何圖片")
        return False

    dialog = BatchImageEditorDialog(file_paths, parent)
    return dialog.exec_() == QDialog.Accepted
