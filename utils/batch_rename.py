"""
批次重新命名工具模組
提供多種批次重新命名規則
"""
import os
import re
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QListWidget, QGroupBox,
    QCheckBox, QMessageBox
)
from PyQt5.QtCore import Qt


class BatchRenameDialog(QDialog):
    """批次重新命名對話框"""

    def __init__(self, file_paths, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.setWindowTitle("批次重新命名")
        self.resize(700, 600)
        self._init_ui()
        self._update_preview()

    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)

        # 標題
        title = QLabel("🏷️ 批次重新命名工具")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #3B82F6;")
        main_layout.addWidget(title)

        # 規則設定區
        rules_group = QGroupBox("重新命名規則")
        rules_layout = QVBoxLayout()

        # 命名模式選擇
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("命名模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "前綴 + 序號",
            "序號 + 後綴",
            "前綴 + 原檔名",
            "原檔名 + 後綴",
            "日期時間 + 序號",
            "自訂格式"
        ])
        self.mode_combo.currentIndexChanged.connect(self._update_preview)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        rules_layout.addLayout(mode_layout)

        # 前綴設定
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("前綴:"))
        self.prefix_edit = QLineEdit("IMG")
        self.prefix_edit.textChanged.connect(self._update_preview)
        prefix_layout.addWidget(self.prefix_edit)
        prefix_layout.addStretch()
        rules_layout.addLayout(prefix_layout)

        # 後綴設定
        suffix_layout = QHBoxLayout()
        suffix_layout.addWidget(QLabel("後綴:"))
        self.suffix_edit = QLineEdit("")
        self.suffix_edit.textChanged.connect(self._update_preview)
        suffix_layout.addWidget(self.suffix_edit)
        suffix_layout.addStretch()
        rules_layout.addLayout(suffix_layout)

        # 序號設定
        number_layout = QHBoxLayout()
        number_layout.addWidget(QLabel("起始序號:"))
        self.start_number = QSpinBox()
        self.start_number.setRange(0, 99999)
        self.start_number.setValue(1)
        self.start_number.valueChanged.connect(self._update_preview)
        number_layout.addWidget(self.start_number)

        number_layout.addWidget(QLabel("位數:"))
        self.digit_count = QSpinBox()
        self.digit_count.setRange(1, 6)
        self.digit_count.setValue(3)
        self.digit_count.valueChanged.connect(self._update_preview)
        number_layout.addWidget(self.digit_count)
        number_layout.addStretch()
        rules_layout.addLayout(number_layout)

        # 大小寫轉換
        case_layout = QHBoxLayout()
        case_layout.addWidget(QLabel("檔名大小寫:"))
        self.case_combo = QComboBox()
        self.case_combo.addItems(["保持原樣", "全部大寫", "全部小寫", "首字母大寫"])
        self.case_combo.currentIndexChanged.connect(self._update_preview)
        case_layout.addWidget(self.case_combo)
        case_layout.addStretch()
        rules_layout.addLayout(case_layout)

        # 保留副檔名
        self.keep_extension = QCheckBox("保留原始副檔名")
        self.keep_extension.setChecked(True)
        self.keep_extension.stateChanged.connect(self._update_preview)
        rules_layout.addWidget(self.keep_extension)

        rules_group.setLayout(rules_layout)
        main_layout.addWidget(rules_group)

        # 預覽區
        preview_group = QGroupBox("重新命名預覽")
        preview_layout = QVBoxLayout()

        self.preview_list = QListWidget()
        self.preview_list.setMinimumHeight(250)
        preview_layout.addWidget(self.preview_list)

        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)

        # 按鈕區
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setProperty("secondary", True)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("✅ 套用重新命名")
        apply_btn.clicked.connect(self.apply_rename)
        button_layout.addWidget(apply_btn)

        main_layout.addLayout(button_layout)

    def _generate_new_name(self, index, file_path):
        """產生新檔名"""
        original_name = os.path.basename(file_path)
        name_without_ext, ext = os.path.splitext(original_name)

        mode = self.mode_combo.currentText()
        prefix = self.prefix_edit.text()
        suffix = self.suffix_edit.text()
        number = self.start_number.value() + index
        digits = self.digit_count.value()
        number_str = str(number).zfill(digits)

        # 根據模式生成新檔名
        if mode == "前綴 + 序號":
            new_name = f"{prefix}{number_str}"
        elif mode == "序號 + 後綴":
            new_name = f"{number_str}{suffix}"
        elif mode == "前綴 + 原檔名":
            new_name = f"{prefix}{name_without_ext}"
        elif mode == "原檔名 + 後綴":
            new_name = f"{name_without_ext}{suffix}"
        elif mode == "日期時間 + 序號":
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{date_str}_{number_str}"
        else:  # 自訂格式
            new_name = f"{prefix}{number_str}{suffix}"

        # 大小寫轉換
        case_option = self.case_combo.currentText()
        if case_option == "全部大寫":
            new_name = new_name.upper()
        elif case_option == "全部小寫":
            new_name = new_name.lower()
        elif case_option == "首字母大寫":
            new_name = new_name.capitalize()

        # 保留副檔名
        if self.keep_extension.isChecked():
            new_name = new_name + ext

        return new_name

    def _update_preview(self):
        """更新預覽清單"""
        self.preview_list.clear()

        for index, file_path in enumerate(self.file_paths):
            original_name = os.path.basename(file_path)
            new_name = self._generate_new_name(index, file_path)

            preview_text = f"{original_name}  →  {new_name}"
            self.preview_list.addItem(preview_text)

    def apply_rename(self):
        """套用重新命名"""
        # 確認對話框
        reply = QMessageBox.question(
            self,
            "確認重新命名",
            f"確定要重新命名 {len(self.file_paths)} 個檔案嗎？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        # 執行重新命名
        success_count = 0
        errors = []

        for index, file_path in enumerate(self.file_paths):
            try:
                directory = os.path.dirname(file_path)
                new_name = self._generate_new_name(index, file_path)
                new_path = os.path.join(directory, new_name)

                # 檢查新檔名是否已存在
                if os.path.exists(new_path) and new_path != file_path:
                    errors.append(f"{new_name} 已存在")
                    continue

                # 重新命名
                os.rename(file_path, new_path)
                success_count += 1

            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")

        # 顯示結果
        if errors:
            error_msg = "\n".join(errors[:10])  # 只顯示前 10 個錯誤
            if len(errors) > 10:
                error_msg += f"\n... 還有 {len(errors) - 10} 個錯誤"

            QMessageBox.warning(
                self,
                "重新命名部分失敗",
                f"成功: {success_count} 個\n失敗: {len(errors)} 個\n\n錯誤:\n{error_msg}"
            )
        else:
            QMessageBox.information(
                self,
                "重新命名完成",
                f"成功重新命名 {success_count} 個檔案！"
            )

        if success_count > 0:
            self.accept()


def batch_rename_files(file_paths, parent=None):
    """
    批次重新命名檔案

    Args:
        file_paths: 檔案路徑列表
        parent: 父視窗

    Returns:
        是否成功執行重新命名
    """
    if not file_paths:
        QMessageBox.warning(parent, "警告", "沒有選擇任何檔案")
        return False

    dialog = BatchRenameDialog(file_paths, parent)
    return dialog.exec_() == QDialog.Accepted
