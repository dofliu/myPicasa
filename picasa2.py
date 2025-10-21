import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QComboBox, QFileDialog,
    QMessageBox, QDialog, QScrollArea, QAction
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PIL import Image
from PIL import ImageQt  # 匯入 ImageQt 模組

# 判斷 Pillow 版本，選擇適用的縮放參數
try:
    resample_filter = Image.Resampling.LANCZOS
except AttributeError:
    resample_filter = Image.ANTIALIAS

def resize_with_padding(img, target_size, bg_color=(255, 255, 255)):
    """
    以保持原始比例縮放圖片，並將縮放後的圖片置中補足目標尺寸
    """
    target_width, target_height = target_size
    ratio = min(target_width / img.width, target_height / img.height)
    new_width = int(img.width * ratio)
    new_height = int(img.height * ratio)
    resized_img = img.resize((new_width, new_height), resample=resample_filter)
    new_img = Image.new("RGB", (target_width, target_height), bg_color)
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    new_img.paste(resized_img, (paste_x, paste_y))
    return new_img

def resize_image(img, target_size, strategy):
    """
    根據縮放策略：
    - 保持比例補白：保持原比例縮放並補白
    - 直接縮放：直接縮放至目標尺寸（可能變形）
    """
    if strategy == "保持比例補白":
        return resize_with_padding(img, target_size)
    else:
        return img.resize(target_size, resample=resample_filter)

class ImageTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dof的圖片整理工具_2025版")
        self.resize(800, 600)
        self._initUI()
        self.create_actions()
        self.create_menus()

    def _initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # 選擇圖片檔案按鈕
        btn_select = QPushButton("選擇圖片檔案")
        btn_select.clicked.connect(self.selectFiles)
        main_layout.addWidget(btn_select)

        # 顯示選取檔案的清單
        self.filesList = QListWidget()
        main_layout.addWidget(self.filesList)

        # 網格參數設定（列數與行數）
        grid_layout = QHBoxLayout()
        lbl_cols = QLabel("列數 (grid cols):")
        self.editCols = QLineEdit("2")
        self.editCols.setMaximumWidth(50)
        lbl_rows = QLabel("行數 (grid rows):")
        self.editRows = QLineEdit("2")
        self.editRows.setMaximumWidth(50)
        grid_layout.addWidget(lbl_cols)
        grid_layout.addWidget(self.editCols)
        grid_layout.addWidget(lbl_rows)
        grid_layout.addWidget(self.editRows)
        grid_layout.addStretch()
        main_layout.addLayout(grid_layout)

        # 縮放策略選擇
        strategy_layout = QHBoxLayout()
        lbl_strategy = QLabel("縮放策略:")
        self.comboStrategy = QComboBox()
        self.comboStrategy.addItems(["直接縮放", "保持比例補白"])
        strategy_layout.addWidget(lbl_strategy)
        strategy_layout.addWidget(self.comboStrategy)
        strategy_layout.addStretch()
        main_layout.addLayout(strategy_layout)

        # 拼接與預覽按鈕
        action_layout = QHBoxLayout()
        btn_merge = QPushButton("拼接圖片")
        btn_merge.clicked.connect(self.mergeImages)
        action_layout.addWidget(btn_merge)
        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        # GIF 動畫參數與生成按鈕
        gif_layout = QHBoxLayout()
        lbl_duration = QLabel("動畫持續時間 (ms):")
        self.editDuration = QLineEdit("500")
        self.editDuration.setMaximumWidth(80)
        btn_gif = QPushButton("生成 GIF 動畫")
        btn_gif.clicked.connect(self.createGIF)
        gif_layout.addWidget(lbl_duration)
        gif_layout.addWidget(self.editDuration)
        gif_layout.addWidget(btn_gif)
        gif_layout.addStretch()
        main_layout.addLayout(gif_layout)

        self.image_label = QLabel(self)
        main_layout.addWidget(self.image_label)

    def create_actions(self):
        self.open_action = QAction("打開", self)
        self.open_action.triggered.connect(self.open_image)

    def create_menus(self):
        menu = self.menuBar().addMenu("文件")
        menu.addAction(self.open_action)
    
    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "打開圖片", "", "Images (*.png *.xpm *.jpg)")
        if file_path:
            self.image = Image.open(file_path)
            self.show_image()

    def show_image(self):
        qimage = ImageQt.ImageQt(self.image)
        pixmap = QPixmap.fromImage(qimage)
        self.image_label.setPixmap(pixmap)

    def selectFiles(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "選擇圖片檔案", "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.gif)"
        )
        if files:
            self.filesList.clear()
            for file in files:
                self.filesList.addItem(file)

    def generateMergedImage(self):
        count = self.filesList.count()
        if count == 0:
            QMessageBox.warning(self, "警告", "請先選擇圖片檔案")
            return None

        try:
            grid_cols = int(self.editCols.text())
            grid_rows = int(self.editRows.text())
        except ValueError:
            QMessageBox.critical(self, "錯誤", "請輸入正確的數字格式")
            return None

        # 讀取所有圖片
        paths = [self.filesList.item(i).text() for i in range(count)]
        try:
            images = [Image.open(p) for p in paths]
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"圖片讀取失敗：{e}")
            return None

        # 使用所有圖片中最小的尺寸作為目標尺寸
        min_width = min(img.width for img in images)
        min_height = min(img.height for img in images)
        cell_width, cell_height = min_width, min_height

        # 設定間隔與邊框（gap = 5px）
        gap = 15
        merged_width = grid_cols * cell_width + (grid_cols + 1) * gap
        merged_height = grid_rows * cell_height + (grid_rows + 1) * gap
        merged_image = Image.new("RGB", (merged_width, merged_height), color=(255, 255, 255))

        strategy = self.comboStrategy.currentText()
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

    def mergeImages(self):
        merged_image = self.generateMergedImage()
        if merged_image is None:
            return
        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "儲存拼接後圖片", "", "JPEG (*.jpg);;PNG (*.png)", options=options
        )
        if save_path:
            try:
                merged_image.save(save_path)
                QMessageBox.information(self, "完成", f"拼接圖片已儲存至\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"儲存失敗：{e}")
    def createGIF(self):
        count = self.filesList.count()
        if count == 0:
            QMessageBox.warning(self, "警告", "請先選擇圖片檔案")
            return

        try:
            duration = int(self.editDuration.text())
        except ValueError:
            QMessageBox.critical(self, "錯誤", "請輸入正確的動畫持續時間（毫秒）")
            return

        paths = [self.filesList.item(i).text() for i in range(count)]
        try:
            images = [Image.open(p) for p in paths]
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"圖片讀取失敗：{e}")
            return

        min_width = min(img.width for img in images)
        min_height = min(img.height for img in images)
        target_size = (min_width, min_height)
        strategy = self.comboStrategy.currentText()
        frames = [resize_image(img, target_size, strategy) for img in images]

        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "儲存 GIF 動畫", "", "GIF (*.gif)", options=options
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
                QMessageBox.information(self, "完成", f"GIF 動畫已儲存至\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"儲存 GIF 失敗：{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageTool()
    window.show()
    sys.exit(app.exec_())
