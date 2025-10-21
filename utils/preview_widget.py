"""
圖片預覽網格小工具
提供縮圖預覽、拖放排序、詳細資訊顯示等功能
"""
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QGridLayout, QDialog, QFrame, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage, QPainter
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PIL import Image


class ImageThumbnail(QFrame):
    """單個圖片縮圖小工具"""

    clicked = pyqtSignal(str)  # 點擊時發出檔案路徑
    remove_requested = pyqtSignal(str)  # 請求移除時發出檔案路徑

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.thumbnail_size = 150

        self._init_ui()
        self._load_thumbnail()

    def _init_ui(self):
        """初始化 UI"""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(2)
        self.setCursor(Qt.PointingHandCursor)

        # 主佈局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # 圖片標籤
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedSize(self.thumbnail_size, self.thumbnail_size)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #F1F5F9;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.image_label)

        # 檔案名稱
        filename = os.path.basename(self.file_path)
        if len(filename) > 18:
            filename = filename[:15] + "..."

        self.name_label = QLabel(filename)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("font-size: 9pt; color: #64748B;")
        layout.addWidget(self.name_label)

        # 檔案資訊
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 8pt; color: #94A3B8;")
        layout.addWidget(self.info_label)

        # 刪除按鈕
        self.remove_btn = QPushButton("✕")
        self.remove_btn.setFixedSize(24, 24)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF4444;
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #DC2626;
            }
        """)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.file_path))
        self.remove_btn.hide()  # 預設隱藏

        # 設定樣式
        self.setStyleSheet("""
            ImageThumbnail {
                border: 2px solid #E2E8F0;
                border-radius: 8px;
                background-color: white;
            }
            ImageThumbnail:hover {
                border-color: #3B82F6;
                background-color: #F0F9FF;
            }
        """)

    def _load_thumbnail(self):
        """載入縮圖"""
        try:
            # 使用 PIL 載入圖片
            img = Image.open(self.file_path)

            # 取得圖片資訊
            width, height = img.size
            file_size = os.path.getsize(self.file_path)
            file_size_kb = file_size / 1024

            # 顯示資訊
            info_text = f"{width}×{height} · {file_size_kb:.1f}KB"
            self.info_label.setText(info_text)

            # 建立縮圖
            img.thumbnail((self.thumbnail_size, self.thumbnail_size), Image.Resampling.LANCZOS)

            # 轉換為 QPixmap
            if img.mode == "RGB":
                qimage = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGB888)
            elif img.mode == "RGBA":
                qimage = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGBA8888)
            else:
                img = img.convert("RGB")
                qimage = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGB888)

            pixmap = QPixmap.fromImage(qimage)
            self.image_label.setPixmap(pixmap)

        except Exception as e:
            print(f"載入縮圖失敗：{e}")
            self.image_label.setText("⚠️\n無法載入")
            self.info_label.setText("載入失敗")

    def mousePressEvent(self, event):
        """滑鼠點擊事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_path)

    def enterEvent(self, event):
        """滑鼠進入事件"""
        self.remove_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """滑鼠離開事件"""
        self.remove_btn.hide()
        super().leaveEvent(event)


class ImagePreviewGrid(QWidget):
    """圖片預覽網格"""

    file_clicked = pyqtSignal(str)  # 檔案被點擊
    file_removed = pyqtSignal(str)  # 檔案被移除
    files_changed = pyqtSignal()  # 檔案列表變更

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thumbnails = []  # 儲存縮圖小工具
        self.files = []  # 儲存檔案路徑
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 工具列
        toolbar = QHBoxLayout()

        self.count_label = QLabel("已選擇 0 個檔案")
        self.count_label.setStyleSheet("font-size: 10pt; color: #64748B;")
        toolbar.addWidget(self.count_label)

        toolbar.addStretch()

        self.clear_btn = QPushButton("🗑️ 清空全部")
        self.clear_btn.setProperty("secondary", True)
        self.clear_btn.clicked.connect(self.clear_all)
        toolbar.addWidget(self.clear_btn)

        main_layout.addLayout(toolbar)

        # 捲動區域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 網格容器
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(self.grid_container)
        main_layout.addWidget(scroll)

        # 初始提示
        self.placeholder = QLabel("📂 尚未選擇任何檔案\n\n點擊上方按鈕或拖放檔案到這裡")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                font-size: 12pt;
                padding: 40px;
            }
        """)
        self.grid_layout.addWidget(self.placeholder, 0, 0, Qt.AlignCenter)

    def add_files(self, file_paths):
        """
        新增檔案到預覽網格

        Args:
            file_paths: 檔案路徑列表
        """
        for file_path in file_paths:
            if file_path not in self.files:
                self.files.append(file_path)
                self._add_thumbnail(file_path)

        self._update_ui()

    def _add_thumbnail(self, file_path):
        """新增縮圖"""
        thumbnail = ImageThumbnail(file_path)
        thumbnail.clicked.connect(self.file_clicked.emit)
        thumbnail.remove_requested.connect(self._remove_file)

        self.thumbnails.append(thumbnail)

    def _remove_file(self, file_path):
        """移除檔案"""
        if file_path in self.files:
            index = self.files.index(file_path)
            self.files.pop(index)

            # 移除對應的縮圖
            thumbnail = self.thumbnails.pop(index)
            thumbnail.deleteLater()

            self._update_ui()
            self.file_removed.emit(file_path)
            self.files_changed.emit()

    def _update_ui(self):
        """更新 UI"""
        # 清除舊的網格
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)

        if not self.files:
            # 顯示提示
            self.grid_layout.addWidget(self.placeholder, 0, 0, Qt.AlignCenter)
            self.count_label.setText("已選擇 0 個檔案")
        else:
            # 隱藏提示
            self.placeholder.setParent(None)

            # 重新排列縮圖（每行 4 個）
            cols = 4
            for index, thumbnail in enumerate(self.thumbnails):
                row = index // cols
                col = index % cols
                self.grid_layout.addWidget(thumbnail, row, col)

            # 更新計數
            self.count_label.setText(f"已選擇 {len(self.files)} 個檔案")

    def clear_all(self):
        """清空所有檔案"""
        self.files.clear()
        for thumbnail in self.thumbnails:
            thumbnail.deleteLater()
        self.thumbnails.clear()
        self._update_ui()
        self.files_changed.emit()

    def get_files(self):
        """取得所有檔案路徑"""
        return self.files.copy()


class ImageViewerDialog(QDialog):
    """圖片檢視器對話框（點擊縮圖時放大顯示）"""

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle(os.path.basename(file_path))
        self.resize(800, 600)
        self._init_ui()

    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)

        # 圖片標籤
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)

        # 載入圖片
        pixmap = QPixmap(self.file_path)
        if not pixmap.isNull():
            # 縮放到合適大小
            scaled_pixmap = pixmap.scaled(
                780, 580,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

        layout.addWidget(self.image_label)

        # 關閉按鈕
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
