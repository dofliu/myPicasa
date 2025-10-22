"""
拖放功能支援模組
提供拖放檔案和資料夾的功能
"""
import os
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QListWidget
from PyQt5.QtGui import QDragEnterEvent, QDropEvent


class DragDropListWidget(QListWidget):
    """支援拖放的清單小工具"""

    # 自訂信號：檔案被拖放時發出
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None, file_extensions=None):
        """
        初始化拖放清單小工具

        Args:
            parent: 父視窗
            file_extensions: 允許的副檔名列表，例如 ['.jpg', '.png']
        """
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.file_extensions = file_extensions or []

        # 設定樣式提示
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #CBD5E1;
                border-radius: 8px;
                background-color: transparent;
            }
            QListWidget:hover {
                border-color: #3B82F6;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖曳進入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # 視覺回饋：改變邊框顏色
            self.setStyleSheet("""
                QListWidget {
                    border: 3px dashed #3B82F6;
                    border-radius: 8px;
                    background-color: rgba(59, 130, 246, 0.05);
                }
            """)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """拖曳離開事件"""
        # 恢復原始樣式
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #CBD5E1;
                border-radius: 8px;
                background-color: transparent;
            }
            QListWidget:hover {
                border-color: #3B82F6;
            }
        """)

    def dragMoveEvent(self, event):
        """??????"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """放下事件"""
        files = []

        # 處理所有拖放的 URL
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()

            # 如果是資料夾，掃描其中的檔案
            if os.path.isdir(file_path):
                files.extend(self._scan_directory(file_path))
            # 如果是檔案，檢查副檔名
            elif os.path.isfile(file_path):
                if self._is_valid_file(file_path):
                    files.append(file_path)

        # 發出信號
        if files:
            self.files_dropped.emit(files)

        # 恢復原始樣式
        self.dragLeaveEvent(event)
        event.acceptProposedAction()

    def _scan_directory(self, directory):
        """
        掃描資料夾中的有效檔案

        Args:
            directory: 資料夾路徑

        Returns:
            符合條件的檔案路徑列表
        """
        valid_files = []

        try:
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    if self._is_valid_file(file_path):
                        valid_files.append(file_path)
        except Exception as e:
            print(f"掃描資料夾時發生錯誤：{e}")

        return valid_files

    def _is_valid_file(self, file_path):
        """
        檢查檔案是否有效

        Args:
            file_path: 檔案路徑

        Returns:
            是否為有效檔案
        """
        if not self.file_extensions:
            return True

        # 檢查副檔名
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.file_extensions

    def add_files(self, files):
        """
        新增檔案到清單

        Args:
            files: 檔案路徑列表
        """
        for file_path in files:
            # 避免重複
            if not self._is_file_in_list(file_path):
                self.addItem(file_path)

    def _is_file_in_list(self, file_path):
        """檢查檔案是否已在清單中"""
        for i in range(self.count()):
            if self.item(i).text() == file_path:
                return True
        return False

    def get_all_files(self):
        """取得清單中的所有檔案路徑"""
        return [self.item(i).text() for i in range(self.count())]

    def clear_all(self):
        """清空清單"""
        self.clear()


class DropZoneWidget(QListWidget):
    """
    拖放區域小工具（帶有提示文字）
    用於沒有檔案時顯示提示
    """

    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None, file_extensions=None, placeholder_text=""):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.file_extensions = file_extensions or []
        self.placeholder_text = placeholder_text or "拖放檔案到這裡"

        # 建立內部的拖放清單
        self._drag_drop_list = DragDropListWidget(self, file_extensions)
        self._drag_drop_list.files_dropped.connect(self._on_files_dropped)

    def _on_files_dropped(self, files):
        """檔案被拖放時的處理"""
        self.files_dropped.emit(files)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """委派給內部清單"""
        self._drag_drop_list.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        """委派給內部清單"""
        self._drag_drop_list.dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent):
        """委派給內部清單"""
        self._drag_drop_list.dropEvent(event)

    def add_files(self, files):
        """新增檔案"""
        self._drag_drop_list.add_files(files)

    def get_all_files(self):
        """取得所有檔案"""
        return self._drag_drop_list.get_all_files()

    def clear_all(self):
        """清空清單"""
        self._drag_drop_list.clear_all()
