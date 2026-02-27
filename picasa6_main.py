import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QListWidget, QComboBox, QFileDialog,
    QMessageBox, QDialog, QScrollArea, QAction, QTabWidget, QListWidgetItem
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PIL import Image
from PIL import ImageQt  # 匯入 ImageQt 模組
from moviepy.editor import VideoFileClip, concatenate_videoclips # type: ignore
from natsort import natsorted # For natural sorting of filenames

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

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self._createImageTab()
        self._createVideoTab()
        self._createConvertImageTab()
        self._createCleanupTab()
        self.cleanup_candidates_map = {}

    def _createCleanupTab(self):
        cleanup_tab = QWidget()
        cleanup_layout = QVBoxLayout(cleanup_tab)

        cleanup_desc = QLabel(
            "掃描 Windows 常見會持續累積的暫存資料夾（例如 Temp、快取、回收桶），\n"
            "勾選後可一鍵清理。請先確認資料夾內容。"
        )
        cleanup_desc.setWordWrap(True)
        cleanup_layout.addWidget(cleanup_desc)

        drive_layout = QHBoxLayout()
        drive_layout.addWidget(QLabel("目標磁碟:"))
        self.comboCleanupDrive = QComboBox()
        self.comboCleanupDrive.addItems(self.get_available_drives())
        drive_layout.addWidget(self.comboCleanupDrive)

        btn_scan_cleanup = QPushButton("掃描清理建議")
        btn_scan_cleanup.clicked.connect(self.scanCleanupCandidates)
        drive_layout.addWidget(btn_scan_cleanup)
        drive_layout.addStretch()
        cleanup_layout.addLayout(drive_layout)

        self.cleanupList = QListWidget()
        cleanup_layout.addWidget(self.cleanupList)

        self.lblCleanupSummary = QLabel("尚未掃描")
        cleanup_layout.addWidget(self.lblCleanupSummary)

        btn_delete_selected = QPushButton("刪除勾選項目")
        btn_delete_selected.clicked.connect(self.deleteSelectedCleanupItems)
        cleanup_layout.addWidget(btn_delete_selected)

        self.tab_widget.addTab(cleanup_tab, "硬碟清理建議")

    def get_available_drives(self):
        if os.name != "nt":
            return ["/"]

        drives = []
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                drives.append(drive_path)
        return drives if drives else ["C:\\"]

    def get_cleanup_candidates(self, drive_root):
        candidates = []
        if os.name != "nt":
            return [
                {"label": "系統暫存資料夾", "path": "/tmp"},
                {"label": "使用者快取資料夾", "path": os.path.expanduser("~/.cache")},
            ]

        drive = drive_root.rstrip("\\/")
        home_dir = os.path.expanduser("~")
        user_profile = home_dir if home_dir.startswith(drive) else None

        candidates.extend([
            {"label": "Windows 暫存資料夾", "path": f"{drive}\\Windows\\Temp"},
            {"label": "Windows 更新下載快取", "path": f"{drive}\\Windows\\SoftwareDistribution\\Download"},
            {"label": "系統回收桶", "path": f"{drive}\\$Recycle.Bin"},
        ])

        if user_profile:
            candidates.extend([
                {"label": "使用者 Temp", "path": os.path.join(user_profile, "AppData", "Local", "Temp")},
                {"label": "IE/Edge 快取", "path": os.path.join(user_profile, "AppData", "Local", "Microsoft", "Windows", "INetCache")},
                {"label": "縮圖快取", "path": os.path.join(user_profile, "AppData", "Local", "Microsoft", "Windows", "Explorer")},
                {"label": "程式崩潰記錄", "path": os.path.join(user_profile, "AppData", "Local", "CrashDumps")},
            ])

        return candidates

    def calculate_folder_size(self, path):
        total_size = 0
        try:
            if os.path.isfile(path):
                return os.path.getsize(path)

            for root, _, files in os.walk(path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        if not os.path.islink(file_path):
                            total_size += os.path.getsize(file_path)
                    except OSError:
                        continue
        except OSError:
            return 0
        return total_size

    def format_size(self, size_bytes):
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        for unit in units:
            if size < 1024 or unit == units[-1]:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size_bytes} B"

    def scanCleanupCandidates(self):
        self.cleanupList.clear()
        self.cleanup_candidates_map = {}
        drive_root = self.comboCleanupDrive.currentText()
        candidates = self.get_cleanup_candidates(drive_root)

        total_size = 0
        shown_count = 0
        for candidate in candidates:
            path = candidate["path"]
            if not os.path.exists(path):
                continue

            size = self.calculate_folder_size(path)
            if size <= 0:
                continue

            shown_count += 1
            total_size += size
            self.cleanup_candidates_map[path] = candidate["label"]
            item_text = f"[{candidate['label']}] {path}（約 {self.format_size(size)}）"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, path)
            self.cleanupList.addItem(item)

        if shown_count == 0:
            self.lblCleanupSummary.setText("未找到可建議清理的項目，或目前資料夾大小為 0")
            QMessageBox.information(self, "掃描完成", "沒有找到可清理建議。")
        else:
            self.lblCleanupSummary.setText(
                f"共找到 {shown_count} 個建議項目，預估可釋放 {self.format_size(total_size)}"
            )

    def deleteSelectedCleanupItems(self):
        selected_paths = []
        for index in range(self.cleanupList.count()):
            item = self.cleanupList.item(index)
            if item.checkState() == Qt.Checked:
                selected_paths.append(item.data(Qt.UserRole))

        if not selected_paths:
            QMessageBox.warning(self, "警告", "請先勾選要刪除的項目")
            return

        confirm = QMessageBox.question(
            self,
            "確認刪除",
            f"即將刪除 {len(selected_paths)} 個項目，這個動作無法復原。是否繼續？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        deleted_count = 0
        error_messages = []

        for path in selected_paths:
            try:
                if path not in self.cleanup_candidates_map:
                    error_messages.append(f"{path}: 不在目前掃描建議清單中，已略過")
                    continue

                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    for name in os.listdir(path):
                        child = os.path.join(path, name)
                        try:
                            if os.path.isdir(child):
                                shutil.rmtree(child)
                            else:
                                os.remove(child)
                        except Exception as child_err:
                            error_messages.append(f"{child}: {child_err}")
                deleted_count += 1
            except Exception as e:
                error_messages.append(f"{path}: {e}")

        self.scanCleanupCandidates()

        message = f"已處理 {deleted_count} 個項目。"
        if error_messages:
            message += "\n\n以下項目刪除失敗：\n" + "\n".join(error_messages[:5])
        QMessageBox.information(self, "清理完成", message)

    def _createImageTab(self):
        image_tab = QWidget()
        image_layout = QVBoxLayout(image_tab)

        # 選擇圖片檔案按鈕
        btn_select = QPushButton("選擇圖片檔案")
        btn_select.clicked.connect(self.selectFiles)
        image_layout.addWidget(btn_select)

        # 顯示選取檔案的清單
        self.filesList = QListWidget()
        image_layout.addWidget(self.filesList)

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
        image_layout.addLayout(grid_layout)

        # 縮放策略選擇
        strategy_layout = QHBoxLayout()
        lbl_strategy = QLabel("縮放策略:")
        self.comboStrategy = QComboBox()
        self.comboStrategy.addItems(["直接縮放", "保持比例補白"])
        strategy_layout.addWidget(lbl_strategy)
        strategy_layout.addWidget(self.comboStrategy)
        strategy_layout.addStretch()
        image_layout.addLayout(strategy_layout)

        # 拼接與預覽按鈕
        action_layout = QHBoxLayout()
        btn_merge = QPushButton("拼接圖片")
        btn_merge.clicked.connect(self.mergeImages)
        action_layout.addWidget(btn_merge)
        action_layout.addStretch()
        image_layout.addLayout(action_layout)

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
        image_layout.addLayout(gif_layout)

        self.image_label = QLabel(image_tab)
        image_layout.addWidget(self.image_label)

        self.tab_widget.addTab(image_tab, "圖片處理")

    def _createVideoTab(self):
        video_tab = QWidget()
        video_layout = QVBoxLayout(video_tab)

        # 影片合併參數與生成按鈕
        video_controls_layout = QHBoxLayout()
        btn_select_videos = QPushButton("選擇影片檔案")
        btn_select_videos.clicked.connect(self.selectVideoFiles)
        self.editOutputVideoName = QLineEdit("merged_video.mp4")
        self.editOutputVideoName.setPlaceholderText("輸出影片檔名 (e.g., merged_video.mp4)")
        btn_merge_videos = QPushButton("合併影片")
        btn_merge_videos.clicked.connect(self.mergeVideos)
        video_controls_layout.addWidget(btn_select_videos)
        video_controls_layout.addWidget(self.editOutputVideoName)
        video_controls_layout.addWidget(btn_merge_videos)
        video_controls_layout.addStretch()
        video_layout.addLayout(video_controls_layout)

        self.videoFilesList = QListWidget()
        video_layout.addWidget(self.videoFilesList)

        self.tab_widget.addTab(video_tab, "影片處理")

    def _createConvertImageTab(self):
        convert_image_tab = QWidget()
        convert_image_layout = QVBoxLayout(convert_image_tab)

        # 選擇圖片檔案按鈕
        btn_select_convert_images = QPushButton("選擇要轉換的圖片檔案")
        btn_select_convert_images.clicked.connect(self.selectConvertImages)
        convert_image_layout.addWidget(btn_select_convert_images)

        # 顯示選取檔案的清單
        self.convertFilesList = QListWidget()
        convert_image_layout.addWidget(self.convertFilesList)

        # 輸出格式選擇
        output_format_layout = QHBoxLayout()
        lbl_output_format = QLabel("輸出格式:")
        self.comboOutputFormat = QComboBox()
        self.comboOutputFormat.addItems(["JPG", "PNG", "WEBP", "BMP", "GIF"])
        output_format_layout.addWidget(lbl_output_format)
        output_format_layout.addWidget(self.comboOutputFormat)
        output_format_layout.addStretch()
        convert_image_layout.addLayout(output_format_layout)

        # 輸出資料夾
        output_folder_layout = QHBoxLayout()
        lbl_output_folder = QLabel("輸出資料夾:")
        self.editOutputFolder = QLineEdit("converted_images")
        self.editOutputFolder.setPlaceholderText("輸出資料夾 (留空則儲存至原資料夾)")
        btn_browse_output_folder = QPushButton("瀏覽")
        btn_browse_output_folder.clicked.connect(self.browseOutputFolder)
        output_folder_layout.addWidget(lbl_output_folder)
        output_folder_layout.addWidget(self.editOutputFolder)
        output_folder_layout.addWidget(btn_browse_output_folder)
        output_folder_layout.addStretch()
        convert_image_layout.addLayout(output_folder_layout)

        # 開始轉換按鈕
        btn_convert_images = QPushButton("開始轉換")
        btn_convert_images.clicked.connect(self.convertImages)
        convert_image_layout.addWidget(btn_convert_images)

        self.tab_widget.addTab(convert_image_tab, "圖片格式轉換")

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

    def selectVideoFiles(self):
        videos, _ = QFileDialog.getOpenFileNames(
            self, "選擇影片檔案", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm *.flv)"
        )
        if videos:
            self.videoFilesList.clear()
            for video in videos:
                self.videoFilesList.addItem(video)

    def selectConvertImages(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "選擇要轉換的圖片檔案", "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.gif *.webp)"
        )
        if files:
            self.convertFilesList.clear()
            for file in files:
                self.convertFilesList.addItem(file)

    def browseOutputFolder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
        if folder_path:
            self.editOutputFolder.setText(folder_path)

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

    def mergeVideos(self):
        count = self.videoFilesList.count()
        if count == 0:
            QMessageBox.warning(self, "警告", "請先選擇影片檔案")
            return

        video_files = [self.videoFilesList.item(i).text() for i in range(count)]
        output_filename = self.editOutputVideoName.text()

        if not output_filename:
            QMessageBox.warning(self, "警告", "請輸入輸出影片檔名")
            return

        # 使用 natsorted 進行自然排序，確保檔案順序符合預期
        video_files = natsorted(video_files)

        clips = []
        try:
            for video_file in video_files:
                clip = VideoFileClip(video_file)
                clips.append(clip)
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"讀取影片時發生錯誤：{e}")
            for loaded_clip in clips:
                loaded_clip.close()
            return

        if not clips:
            QMessageBox.warning(self, "警告", "沒有任何影片可以成功載入並合併。")
            return

        try:
            QMessageBox.information(self, "進度", "開始合併影片，這可能需要一些時間...")
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac")
            QMessageBox.information(self, "完成", f"影片成功合併並儲存至\n{output_filename}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"合併影片或寫入檔案時發生錯誤：{e}")
        finally:
            for clip in clips:
                clip.close()
            if 'final_clip' in locals() and final_clip:
                final_clip.close()

    def convertImages(self):
        count = self.convertFilesList.count()
        if count == 0:
            QMessageBox.warning(self, "警告", "請先選擇要轉換的圖片檔案")
            return

        output_format = self.comboOutputFormat.currentText().lower()
        output_folder = self.editOutputFolder.text()

        if not output_folder:
            # 如果沒有指定輸出資料夾，則儲存到原始檔案的資料夾
            output_folder = None
        else:
            # 確保輸出資料夾存在
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

        success_count = 0
        for i in range(count):
            file_path = self.convertFilesList.item(i).text()
            try:
                img = Image.open(file_path)
                
                # 構建輸出檔案路徑
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                if output_folder:
                    save_path = os.path.join(output_folder, f"{base_name}.{output_format}")
                else:
                    save_path = os.path.join(os.path.dirname(file_path), f"{base_name}.{output_format}")

                img.save(save_path, format=output_format.upper())
                success_count += 1
            except Exception as e:
                QMessageBox.warning(self, "轉換失敗", f"檔案 {os.path.basename(file_path)} 轉換失敗：{e}")
        
        if success_count > 0:
            QMessageBox.information(self, "完成", f"成功轉換 {success_count} 個檔案到 {output_folder if output_folder else '原始資料夾'}")
        else:
            QMessageBox.critical(self, "錯誤", "沒有檔案成功轉換")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageTool()
    window.show()
    sys.exit(app.exec_())
