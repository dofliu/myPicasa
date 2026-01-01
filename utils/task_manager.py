
import time
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QPushButton, QListWidget, QListWidgetItem, QWidget
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal

class TaskManager(QObject):
    """
    Central manager for background tasks.
    Singleton pattern.
    """
    task_added = pyqtSignal(str, str)     # task_id, name
    task_removed = pyqtSignal(str)        # task_id
    task_updated = pyqtSignal(str, int, str) # task_id, progress, status

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self.active_tasks = {}  # id -> worker
        self.task_info = {}     # id -> {name, progress, status}
        self._initialized = True

    def add_task(self, worker, name):
        """Register and track a worker task."""
        task_id = str(id(worker))
        self.active_tasks[task_id] = worker
        self.task_info[task_id] = {
            "name": name,
            "progress": 0,
            "status": "Starting..."
        }
        
        # Connect signals
        worker.progress.connect(lambda p: self._on_progress(task_id, p))
        worker.status.connect(lambda s: self._on_status(task_id, s))
        worker.finished.connect(lambda s, m: self._on_finished(task_id))
        
        self.task_added.emit(task_id, name)
        return task_id

    def cancel_task(self, task_id):
        """Cancel a specific task."""
        if task_id in self.active_tasks:
            worker = self.active_tasks[task_id]
            if hasattr(worker, 'cancel'):
                worker.cancel()
            elif hasattr(worker, 'terminate'):
                # Force terminate if no graceful cancel, but prefer cancel flag
                worker.terminate()
                self._on_finished(task_id)

    def _on_progress(self, task_id, progress):
        if task_id in self.task_info:
            self.task_info[task_id]["progress"] = progress
            self.task_updated.emit(task_id, progress, self.task_info[task_id]["status"])

    def _on_status(self, task_id, status):
        if task_id in self.task_info:
            self.task_info[task_id]["status"] = status
            self.task_updated.emit(task_id, self.task_info[task_id]["progress"], status)

    def _on_finished(self, task_id):
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            if task_id in self.task_info:
                del self.task_info[task_id]
            self.task_removed.emit(task_id)

class TaskItemWidget(QWidget):
    """Widget representing a single task in the list."""
    def __init__(self, task_id, name, manager):
        super().__init__()
        self.task_id = task_id
        self.manager = manager
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QHBoxLayout()
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet("font-weight: bold;")
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFixedSize(60, 24)
        self.cancel_btn.clicked.connect(self._cancel)
        
        header.addWidget(self.name_label)
        header.addStretch()
        header.addWidget(self.cancel_btn)
        layout.addLayout(header)
        
        # Status & Progress
        self.status_label = QLabel("Waiting...")
        self.status_label.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        layout.addWidget(self.progress_bar)
        
    def update_state(self, progress, status):
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
        
    def _cancel(self):
        self.manager.cancel_task(self.task_id)

class TaskQueueDialog(QDialog):
    """Dialog showing active tasks."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("任務管理器")
        self.resize(400, 500)
        self.manager = TaskManager()
        
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # Populate initial
        for task_id, info in self.manager.task_info.items():
            self._add_item(task_id, info['name'])
            # Update state
            item_widget = self._get_widget(task_id)
            if item_widget:
                item_widget.update_state(info['progress'], info['status'])
        
        # Connect signals
        self.manager.task_added.connect(self._add_item)
        self.manager.task_removed.connect(self._remove_item)
        self.manager.task_updated.connect(self._update_item)
        
    def _add_item(self, task_id, name):
        item = QListWidgetItem(self.list_widget)
        item.setSizeHint(item.sizeHint()) # Update size
        widget = TaskItemWidget(task_id, name, self.manager)
        item.setSizeHint(widget.sizeHint())
        
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)
        widget.setProperty("taskId", task_id) # Tag for lookup
        
    def _remove_item(self, task_id):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and widget.task_id == task_id:
                self.list_widget.takeItem(i)
                break
                
    def _update_item(self, task_id, progress, status):
        widget = self._get_widget(task_id)
        if widget:
            widget.update_state(progress, status)
            
    def _get_widget(self, task_id):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget and widget.task_id == task_id:
                return widget
        return None
