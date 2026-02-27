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
from PIL import ImageQt  # ?臬 ImageQt 璅∠?
from moviepy.editor import VideoFileClip, concatenate_videoclips # type: ignore
from natsort import natsorted # For natural sorting of filenames

# ?斗 Pillow ?嚗??函?蝮格?
try:
    resample_filter = Image.Resampling.LANCZOS
except AttributeError:
    resample_filter = Image.ANTIALIAS

def resize_with_padding(img, target_size, bg_color=(255, 255, 255)):
    """
    隞乩???憪?靘葬?曉???銝血?蝮格敺???蝵桐葉鋆雲?格?撠箏站
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
    ?寞?蝮格蝑嚗?    - 靽?瘥?鋆嚗???瘥?蝮格銝西???    - ?湔蝮格嚗?亦葬?曇?格?撠箏站嚗?質?敶ｇ?
    """
    if strategy == "靽?瘥?鋆":
        return resize_with_padding(img, target_size)
    else:
        return img.resize(target_size, resample=resample_filter)

class ImageTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dof????極?愷2025??)
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
            "?? Windows 撣貉???蝥敞蝛??怠?鞈?憭橘?靘? Temp?翰???嗆▲嚗?\n"
            "?暸敺銝?菜????Ⅱ隤??冗?批捆??
        )
        cleanup_desc.setWordWrap(True)
        cleanup_layout.addWidget(cleanup_desc)

        drive_layout = QHBoxLayout()
        drive_layout.addWidget(QLabel("?格?蝤?:"))
        self.comboCleanupDrive = QComboBox()
        self.comboCleanupDrive.addItems(self.get_available_drives())
        drive_layout.addWidget(self.comboCleanupDrive)

        btn_scan_cleanup = QPushButton("??皜?撱箄降")
        btn_scan_cleanup.clicked.connect(self.scanCleanupCandidates)
        drive_layout.addWidget(btn_scan_cleanup)
        drive_layout.addStretch()
        cleanup_layout.addLayout(drive_layout)

        self.cleanupList = QListWidget()
        cleanup_layout.addWidget(self.cleanupList)

        self.lblCleanupSummary = QLabel("撠??")
        cleanup_layout.addWidget(self.lblCleanupSummary)

        btn_delete_selected = QPushButton("?芷?暸?")
        btn_delete_selected.clicked.connect(self.deleteSelectedCleanupItems)
        cleanup_layout.addWidget(btn_delete_selected)

        self.tab_widget.addTab(cleanup_tab, "蝖祉?皜?撱箄降")

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
                {"label": "蝟餌絞?怠?鞈?憭?, "path": "/tmp"},
                {"label": "雿輻?翰???冗", "path": os.path.expanduser("~/.cache")},
            ]

        drive = drive_root.rstrip("\\/")
        home_dir = os.path.expanduser("~")
        user_profile = home_dir if home_dir.startswith(drive) else None

        candidates.extend([
            {"label": "Windows ?怠?鞈?憭?, "path": f"{drive}\\Windows\\Temp"},
            {"label": "Windows ?湔銝?敹怠?", "path": f"{drive}\\Windows\\SoftwareDistribution\\Download"},
            {"label": "蝟餌絞?獢?, "path": f"{drive}\\$Recycle.Bin"},
        ])

        if user_profile:
            candidates.extend([
                {"label": "雿輻??Temp", "path": os.path.join(user_profile, "AppData", "Local", "Temp")},
                {"label": "IE/Edge 敹怠?", "path": os.path.join(user_profile, "AppData", "Local", "Microsoft", "Windows", "INetCache")},
                {"label": "蝮桀?敹怠?", "path": os.path.join(user_profile, "AppData", "Local", "Microsoft", "Windows", "Explorer")},
                {"label": "蝔?撏拇蔑閮?", "path": os.path.join(user_profile, "AppData", "Local", "CrashDumps")},
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
            item_text = f"[{candidate['label']}] {path}嚗? {self.format_size(size)}嚗?
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, path)
            self.cleanupList.addItem(item)

        if shown_count == 0:
            self.lblCleanupSummary.setText("?芣?啣撱箄降皜????殷?????冗憭批???0")
            QMessageBox.information(self, "??摰?", "瘝??曉?舀??遣霅啜?)
        else:
            self.lblCleanupSummary.setText(
                f"?望??{shown_count} ?遣霅圈??殷??摯?舫???{self.format_size(total_size)}"
            )

    def deleteSelectedCleanupItems(self):
        selected_paths = []
        for index in range(self.cleanupList.count()):
            item = self.cleanupList.item(index)
            if item.checkState() == Qt.Checked:
                selected_paths.append(item.data(Qt.UserRole))

        if not selected_paths:
            QMessageBox.warning(self, "霅血?", "隢??暸閬?斤??")
            return

        confirm = QMessageBox.question(
            self,
            "蝣箄??芷",
            f"?喳??芷 {len(selected_paths)} ???殷???雿瘜儔??衣匱蝥?",
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
                    error_messages.append(f"{path}: 銝?桀???撱箄降皜銝哨?撌脩??)
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

        message = f"撌脰???{deleted_count} ???柴?
        if error_messages:
            message += "\n\n隞乩???芷憭望?嚗n" + "\n".join(error_messages[:5])
        QMessageBox.information(self, "皜?摰?", message)

    def _createImageTab(self):
        image_tab = QWidget()
        image_layout = QVBoxLayout(image_tab)

        # ?豢???瑼???
        btn_select = QPushButton("?豢???瑼?")
        btn_select.clicked.connect(self.selectFiles)
        image_layout.addWidget(btn_select)

        # 憿舐內?詨?瑼?????        self.filesList = QListWidget()
        image_layout.addWidget(self.filesList)

        # 蝬脫?閮剖?嚗??貉?銵嚗?        grid_layout = QHBoxLayout()
        lbl_cols = QLabel("? (grid cols):")
        self.editCols = QLineEdit("2")
        self.editCols.setMaximumWidth(50)
        lbl_rows = QLabel("銵 (grid rows):")
        self.editRows = QLineEdit("2")
        self.editRows.setMaximumWidth(50)
        grid_layout.addWidget(lbl_cols)
        grid_layout.addWidget(self.editCols)
        grid_layout.addWidget(lbl_rows)
        grid_layout.addWidget(self.editRows)
        grid_layout.addStretch()
        image_layout.addLayout(grid_layout)

        # 蝮格蝑?豢?
        strategy_layout = QHBoxLayout()
        lbl_strategy = QLabel("蝮格蝑:")
        self.comboStrategy = QComboBox()
        self.comboStrategy.addItems(["?湔蝮格", "靽?瘥?鋆"])
        strategy_layout.addWidget(lbl_strategy)
        strategy_layout.addWidget(self.comboStrategy)
        strategy_layout.addStretch()
        image_layout.addLayout(strategy_layout)

        # ?潭??閬賣???        action_layout = QHBoxLayout()
        btn_merge = QPushButton("?潭??")
        btn_merge.clicked.connect(self.mergeImages)
        action_layout.addWidget(btn_merge)
        action_layout.addStretch()
        image_layout.addLayout(action_layout)

        # GIF ????????        gif_layout = QHBoxLayout()
        lbl_duration = QLabel("????? (ms):")
        self.editDuration = QLineEdit("500")
        self.editDuration.setMaximumWidth(80)
        btn_gif = QPushButton("?? GIF ?")
        btn_gif.clicked.connect(self.createGIF)
        gif_layout.addWidget(lbl_duration)
        gif_layout.addWidget(self.editDuration)
        gif_layout.addWidget(btn_gif)
        gif_layout.addStretch()
        image_layout.addLayout(gif_layout)

        self.image_label = QLabel(image_tab)
        image_layout.addWidget(self.image_label)

        self.tab_widget.addTab(image_tab, "????")

    def _createVideoTab(self):
        video_tab = QWidget()
        video_layout = QVBoxLayout(video_tab)

        # 敶梁??蔥???????        video_controls_layout = QHBoxLayout()
        btn_select_videos = QPushButton("?豢?敶梁?瑼?")
        btn_select_videos.clicked.connect(self.selectVideoFiles)
        self.editOutputVideoName = QLineEdit("merged_video.mp4")
        self.editOutputVideoName.setPlaceholderText("頛詨敶梁?瑼? (e.g., merged_video.mp4)")
        btn_merge_videos = QPushButton("?蔥敶梁?")
        btn_merge_videos.clicked.connect(self.mergeVideos)
        video_controls_layout.addWidget(btn_select_videos)
        video_controls_layout.addWidget(self.editOutputVideoName)
        video_controls_layout.addWidget(btn_merge_videos)
        video_controls_layout.addStretch()
        video_layout.addLayout(video_controls_layout)

        self.videoFilesList = QListWidget()
        video_layout.addWidget(self.videoFilesList)

        self.tab_widget.addTab(video_tab, "敶梁???")

    def _createConvertImageTab(self):
        convert_image_tab = QWidget()
        convert_image_layout = QVBoxLayout(convert_image_tab)

        # ?豢???瑼???
        btn_select_convert_images = QPushButton("?豢?閬?????瑼?")
        btn_select_convert_images.clicked.connect(self.selectConvertImages)
        convert_image_layout.addWidget(btn_select_convert_images)

        # 憿舐內?詨?瑼?????        self.convertFilesList = QListWidget()
        convert_image_layout.addWidget(self.convertFilesList)

        # 頛詨?澆??豢?
        output_format_layout = QHBoxLayout()
        lbl_output_format = QLabel("頛詨?澆?:")
        self.comboOutputFormat = QComboBox()
        self.comboOutputFormat.addItems(["JPG", "PNG", "WEBP", "BMP", "GIF"])
        output_format_layout.addWidget(lbl_output_format)
        output_format_layout.addWidget(self.comboOutputFormat)
        output_format_layout.addStretch()
        convert_image_layout.addLayout(output_format_layout)

        # 頛詨鞈?憭?        output_folder_layout = QHBoxLayout()
        lbl_output_folder = QLabel("頛詨鞈?憭?")
        self.editOutputFolder = QLineEdit("converted_images")
        self.editOutputFolder.setPlaceholderText("頛詨鞈?憭?(?征?摮???冗)")
        btn_browse_output_folder = QPushButton("?汗")
        btn_browse_output_folder.clicked.connect(self.browseOutputFolder)
        output_folder_layout.addWidget(lbl_output_folder)
        output_folder_layout.addWidget(self.editOutputFolder)
        output_folder_layout.addWidget(btn_browse_output_folder)
        output_folder_layout.addStretch()
        convert_image_layout.addLayout(output_folder_layout)

        # ??頧???
        btn_convert_images = QPushButton("??頧?")
        btn_convert_images.clicked.connect(self.convertImages)
        convert_image_layout.addWidget(btn_convert_images)

        self.tab_widget.addTab(convert_image_tab, "???澆?頧?")

    def create_actions(self):
        self.open_action = QAction("??", self)
        self.open_action.triggered.connect(self.open_image)

    def create_menus(self):
        menu = self.menuBar().addMenu("?辣")
        menu.addAction(self.open_action)
    
    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "????", "", "Images (*.png *.xpm *.jpg)")
        if file_path:
            self.image = Image.open(file_path)
            self.show_image()

    def show_image(self):
        qimage = ImageQt.ImageQt(self.image)
        pixmap = QPixmap.fromImage(qimage)
        self.image_label.setPixmap(pixmap)

    def selectFiles(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "?豢???瑼?", "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.gif)"
        )
        if files:
            self.filesList.clear()
            for file in files:
                self.filesList.addItem(file)

    def selectVideoFiles(self):
        videos, _ = QFileDialog.getOpenFileNames(
            self, "?豢?敶梁?瑼?", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm *.flv)"
        )
        if videos:
            self.videoFilesList.clear()
            for video in videos:
                self.videoFilesList.addItem(video)

    def selectConvertImages(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "?豢?閬?????瑼?", "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.gif *.webp)"
        )
        if files:
            self.convertFilesList.clear()
            for file in files:
                self.convertFilesList.addItem(file)

    def browseOutputFolder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "?豢?頛詨鞈?憭?)
        if folder_path:
            self.editOutputFolder.setText(folder_path)

    def generateMergedImage(self):
        count = self.filesList.count()
        if count == 0:
            QMessageBox.warning(self, "霅血?", "隢??豢???瑼?")
            return None

        try:
            grid_cols = int(self.editCols.text())
            grid_rows = int(self.editRows.text())
        except ValueError:
            QMessageBox.critical(self, "?航炊", "隢撓?交迤蝣箇??詨??澆?")
            return None

        # 霈??????        paths = [self.filesList.item(i).text() for i in range(count)]
        try:
            images = [Image.open(p) for p in paths]
        except Exception as e:
            QMessageBox.critical(self, "?航炊", f"??霈?仃??{e}")
            return None

        # 雿輻????葉?撠?撠箏站雿?格?撠箏站
        min_width = min(img.width for img in images)
        min_height = min(img.height for img in images)
        cell_width, cell_height = min_width, min_height

        # 閮剖?????獢?gap = 5px嚗?        gap = 15
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
            self, "?脣??潭敺???, "", "JPEG (*.jpg);;PNG (*.png)", options=options
        )
        if save_path:
            try:
                merged_image.save(save_path)
                QMessageBox.information(self, "摰?", f"?潭??撌脣摮\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "?航炊", f"?脣?憭望?嚗e}")
    def createGIF(self):
        count = self.filesList.count()
        if count == 0:
            QMessageBox.warning(self, "霅血?", "隢??豢???瑼?")
            return

        try:
            duration = int(self.editDuration.text())
        except ValueError:
            QMessageBox.critical(self, "?航炊", "隢撓?交迤蝣箇??????嚗神蝘?")
            return

        paths = [self.filesList.item(i).text() for i in range(count)]
        try:
            images = [Image.open(p) for p in paths]
        except Exception as e:
            QMessageBox.critical(self, "?航炊", f"??霈?仃??{e}")
            return

        min_width = min(img.width for img in images)
        min_height = min(img.height for img in images)
        target_size = (min_width, min_height)
        strategy = self.comboStrategy.currentText()
        frames = [resize_image(img, target_size, strategy) for img in images]

        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "?脣? GIF ?", "", "GIF (*.gif)", options=options
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
                QMessageBox.information(self, "摰?", f"GIF ?撌脣摮\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "?航炊", f"?脣? GIF 憭望?嚗e}")

    def mergeVideos(self):
        count = self.videoFilesList.count()
        if count == 0:
            QMessageBox.warning(self, "霅血?", "隢??豢?敶梁?瑼?")
            return

        video_files = [self.videoFilesList.item(i).text() for i in range(count)]
        output_filename = self.editOutputVideoName.text()

        if not output_filename:
            QMessageBox.warning(self, "霅血?", "隢撓?亥撓?箏蔣????)
            return

        # 雿輻 natsorted ?脰??芰??嚗Ⅱ靽?獢?摨泵????        video_files = natsorted(video_files)

        clips = []
        try:
            for video_file in video_files:
                clip = VideoFileClip(video_file)
                clips.append(clip)
        except Exception as e:
            QMessageBox.critical(self, "?航炊", f"霈?蔣???潛??航炊嚗e}")
            for loaded_clip in clips:
                loaded_clip.close()
            return

        if not clips:
            QMessageBox.warning(self, "霅血?", "瘝?隞颱?敶梁??臭誑??頛銝血?雿萸?)
            return

        try:
            QMessageBox.information(self, "?脣漲", "???蔥敶梁?嚗?賡?閬?鈭???..")
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac")
            QMessageBox.information(self, "摰?", f"敶梁????蔥銝血摮\n{output_filename}")
        except Exception as e:
            QMessageBox.critical(self, "?航炊", f"?蔥敶梁??神?交?獢??潛??航炊嚗e}")
        finally:
            for clip in clips:
                clip.close()
            if 'final_clip' in locals() and final_clip:
                final_clip.close()

    def convertImages(self):
        count = self.convertFilesList.count()
        if count == 0:
            QMessageBox.warning(self, "霅血?", "隢??豢?閬?????瑼?")
            return

        output_format = self.comboOutputFormat.currentText().lower()
        output_folder = self.editOutputFolder.text()

        if not output_folder:
            # 憒?瘝???頛詨鞈?憭橘??摮??瑼????冗
            output_folder = None
        else:
            # 蝣箔?頛詨鞈?憭曉???            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

        success_count = 0
        for i in range(count):
            file_path = self.convertFilesList.item(i).text()
            try:
                img = Image.open(file_path)
                
                # 瑽遣頛詨瑼?頝臬?
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                if output_folder:
                    save_path = os.path.join(output_folder, f"{base_name}.{output_format}")
                else:
                    save_path = os.path.join(os.path.dirname(file_path), f"{base_name}.{output_format}")

                img.save(save_path, format=output_format.upper())
                success_count += 1
            except Exception as e:
                QMessageBox.warning(self, "頧?憭望?", f"瑼? {os.path.basename(file_path)} 頧?憭望?嚗e}")
        
        if success_count > 0:
            QMessageBox.information(self, "摰?", f"??頧? {success_count} ??獢 {output_folder if output_folder else '??鞈?憭?}")
        else:
            QMessageBox.critical(self, "?航炊", "瘝?瑼???頧?")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageTool()
    window.show()
    sys.exit(app.exec_())
