"""
現代化 UI 樣式管理模組
提供美觀的深色和淺色主題
"""


class ModernStyle:
    """現代化樣式管理類別"""

    # 深色主題配色
    DARK_THEME = {
        'primary': '#3B82F6',      # 藍色
        'primary_dark': '#2563EB',
        'primary_light': '#60A5FA',
        'secondary': '#8B5CF6',    # 紫色
        'success': '#10B981',      # 綠色
        'warning': '#F59E0B',      # 橙色
        'danger': '#EF4444',       # 紅色
        'background': '#1E293B',   # 深灰背景
        'surface': '#334155',      # 表面色
        'surface_light': '#475569',
        'text': '#F1F5F9',         # 文字色
        'text_secondary': '#CBD5E1',
        'border': '#475569',
        'hover': '#475569',
    }

    # 淺色主題配色
    LIGHT_THEME = {
        'primary': '#3B82F6',
        'primary_dark': '#2563EB',
        'primary_light': '#DBEAFE',
        'secondary': '#8B5CF6',
        'success': '#10B981',
        'warning': '#F59E0B',
        'danger': '#EF4444',
        'background': '#F8FAFC',   # 淺灰背景
        'surface': '#FFFFFF',      # 白色表面
        'surface_light': '#F1F5F9',
        'text': '#1E293B',         # 深色文字
        'text_secondary': '#64748B',
        'border': '#E2E8F0',
        'hover': '#F1F5F9',
    }

    @classmethod
    def get_dark_stylesheet(cls):
        """取得深色主題樣式表"""
        colors = cls.DARK_THEME
        return f"""
            /* 主視窗 */
            QMainWindow {{
                background-color: {colors['background']};
            }}

            /* 中央小工具 */
            QWidget {{
                background-color: {colors['background']};
                color: {colors['text']};
                font-family: "Microsoft JhengHei", "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
            }}

            /* 分頁視窗 */
            QTabWidget::pane {{
                border: 1px solid {colors['border']};
                background-color: {colors['surface']};
                border-radius: 8px;
                padding: 5px;
            }}

            QTabBar::tab {{
                background-color: {colors['surface']};
                color: {colors['text_secondary']};
                border: none;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
            }}

            QTabBar::tab:selected {{
                background-color: {colors['primary']};
                color: white;
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {colors['hover']};
            }}

            /* 按鈕 */
            QPushButton {{
                background-color: {colors['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 10pt;
                min-height: 20px;
            }}

            QPushButton:hover {{
                background-color: {colors['primary_dark']};
            }}

            QPushButton:pressed {{
                background-color: {colors['primary_dark']};
                padding-top: 12px;
                padding-bottom: 8px;
            }}

            QPushButton:disabled {{
                background-color: {colors['surface_light']};
                color: {colors['text_secondary']};
            }}

            /* 次要按鈕 */
            QPushButton[secondary="true"] {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
            }}

            QPushButton[secondary="true"]:hover {{
                background-color: {colors['hover']};
            }}

            /* 輸入框 */
            QLineEdit {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 6px;
                padding: 8px 12px;
                selection-background-color: {colors['primary']};
            }}

            QLineEdit:focus {{
                border: 2px solid {colors['primary']};
            }}

            /* 下拉選單 */
            QComboBox {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 100px;
            }}

            QComboBox:hover {{
                border: 2px solid {colors['primary_light']};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}

            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {colors['text']};
                margin-right: 10px;
            }}

            QComboBox QAbstractItemView {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                selection-background-color: {colors['primary']};
                border-radius: 6px;
                padding: 4px;
            }}

            /* 清單視窗 */
            QListWidget {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 8px;
                padding: 8px;
            }}

            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }}

            QListWidget::item:selected {{
                background-color: {colors['primary']};
                color: white;
            }}

            QListWidget::item:hover:!selected {{
                background-color: {colors['hover']};
            }}

            /* 標籤 */
            QLabel {{
                color: {colors['text']};
                background-color: transparent;
                padding: 2px;
            }}

            QLabel[heading="true"] {{
                font-size: 14pt;
                font-weight: bold;
                color: {colors['primary']};
                padding: 10px 0;
            }}

            /* 選單列 */
            QMenuBar {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border-bottom: 1px solid {colors['border']};
                padding: 4px;
            }}

            QMenuBar::item {{
                padding: 8px 12px;
                border-radius: 4px;
            }}

            QMenuBar::item:selected {{
                background-color: {colors['primary']};
            }}

            QMenu {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 8px;
            }}

            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
            }}

            QMenu::item:selected {{
                background-color: {colors['primary']};
            }}

            /* 狀態列 */
            QStatusBar {{
                background-color: {colors['surface']};
                color: {colors['text_secondary']};
                border-top: 1px solid {colors['border']};
                padding: 4px;
            }}

            /* 進度條 */
            QProgressBar {{
                background-color: {colors['surface']};
                border: 2px solid {colors['border']};
                border-radius: 6px;
                text-align: center;
                color: {colors['text']};
                height: 24px;
            }}

            QProgressBar::chunk {{
                background-color: {colors['primary']};
                border-radius: 4px;
            }}

            /* 捲軸 */
            QScrollBar:vertical {{
                background-color: {colors['surface']};
                width: 12px;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical {{
                background-color: {colors['border']};
                border-radius: 6px;
                min-height: 30px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {colors['primary']};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}

            /* 訊息框 */
            QMessageBox {{
                background-color: {colors['background']};
            }}

            QMessageBox QLabel {{
                color: {colors['text']};
            }}

            QMessageBox QPushButton {{
                min-width: 80px;
            }}
        """

    @classmethod
    def get_light_stylesheet(cls):
        """取得淺色主題樣式表"""
        colors = cls.LIGHT_THEME
        return f"""
            /* 主視窗 */
            QMainWindow {{
                background-color: {colors['background']};
            }}

            /* 中央小工具 */
            QWidget {{
                background-color: {colors['background']};
                color: {colors['text']};
                font-family: "Microsoft JhengHei", "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
            }}

            /* 分頁視窗 */
            QTabWidget::pane {{
                border: 1px solid {colors['border']};
                background-color: {colors['surface']};
                border-radius: 8px;
                padding: 5px;
            }}

            QTabBar::tab {{
                background-color: {colors['surface']};
                color: {colors['text_secondary']};
                border: none;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 500;
            }}

            QTabBar::tab:selected {{
                background-color: {colors['primary']};
                color: white;
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {colors['hover']};
            }}

            /* 按鈕 */
            QPushButton {{
                background-color: {colors['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 10pt;
                min-height: 20px;
            }}

            QPushButton:hover {{
                background-color: {colors['primary_dark']};
            }}

            QPushButton:pressed {{
                background-color: {colors['primary_dark']};
                padding-top: 12px;
                padding-bottom: 8px;
            }}

            QPushButton:disabled {{
                background-color: {colors['surface_light']};
                color: {colors['text_secondary']};
            }}

            /* 次要按鈕 */
            QPushButton[secondary="true"] {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
            }}

            QPushButton[secondary="true"]:hover {{
                background-color: {colors['hover']};
            }}

            /* 輸入框 */
            QLineEdit {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 6px;
                padding: 8px 12px;
                selection-background-color: {colors['primary']};
            }}

            QLineEdit:focus {{
                border: 2px solid {colors['primary']};
            }}

            /* 下拉選單 */
            QComboBox {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 100px;
            }}

            QComboBox:hover {{
                border: 2px solid {colors['primary']};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}

            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {colors['text']};
                margin-right: 10px;
            }}

            QComboBox QAbstractItemView {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                selection-background-color: {colors['primary']};
                border-radius: 6px;
                padding: 4px;
            }}

            /* 清單視窗 */
            QListWidget {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 2px solid {colors['border']};
                border-radius: 8px;
                padding: 8px;
            }}

            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }}

            QListWidget::item:selected {{
                background-color: {colors['primary']};
                color: white;
            }}

            QListWidget::item:hover:!selected {{
                background-color: {colors['hover']};
            }}

            /* 標籤 */
            QLabel {{
                color: {colors['text']};
                background-color: transparent;
                padding: 2px;
            }}

            QLabel[heading="true"] {{
                font-size: 14pt;
                font-weight: bold;
                color: {colors['primary']};
                padding: 10px 0;
            }}

            /* 選單列 */
            QMenuBar {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border-bottom: 1px solid {colors['border']};
                padding: 4px;
            }}

            QMenuBar::item {{
                padding: 8px 12px;
                border-radius: 4px;
            }}

            QMenuBar::item:selected {{
                background-color: {colors['primary']};
                color: white;
            }}

            QMenu {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 8px;
            }}

            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
            }}

            QMenu::item:selected {{
                background-color: {colors['primary']};
                color: white;
            }}

            /* 狀態列 */
            QStatusBar {{
                background-color: {colors['surface']};
                color: {colors['text_secondary']};
                border-top: 1px solid {colors['border']};
                padding: 4px;
            }}

            /* 進度條 */
            QProgressBar {{
                background-color: {colors['surface']};
                border: 2px solid {colors['border']};
                border-radius: 6px;
                text-align: center;
                color: {colors['text']};
                height: 24px;
            }}

            QProgressBar::chunk {{
                background-color: {colors['primary']};
                border-radius: 4px;
            }}

            /* 捲軸 */
            QScrollBar:vertical {{
                background-color: {colors['surface']};
                width: 12px;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical {{
                background-color: {colors['border']};
                border-radius: 6px;
                min-height: 30px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {colors['primary']};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}

            /* 訊息框 */
            QMessageBox {{
                background-color: {colors['background']};
            }}

            QMessageBox QLabel {{
                color: {colors['text']};
            }}

            QMessageBox QPushButton {{
                min-width: 80px;
            }}
        """

    @classmethod
    def get_card_style(cls, theme="light"):
        """Return the card-like group box stylesheet for the given theme."""
        colors = cls.DARK_THEME if theme == "dark" else cls.LIGHT_THEME

        if theme == "dark":
            border_color = "rgba(148, 163, 184, 0.45)"
            title_background = "rgba(96, 165, 250, 0.22)"
            title_color = colors['text']
        else:
            border_color = colors['border']
            title_background = "rgba(59, 130, 246, 0.12)"
            title_color = colors['primary']

        return f"""
            QGroupBox {{
                border: 1px solid {border_color};
                border-radius: 14px;
                margin-top: 18px;
                padding: 22px 18px 18px 18px;
                font-weight: normal;
                background-color: {colors['surface']};
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 14px;
                background-color: {title_background};
                color: {title_color};
                border-radius: 10px;
                font-weight: 600;
                left: 18px;
                border: 1px solid {border_color};
            }}
        """
