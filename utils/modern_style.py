"""
現代化 UI 樣式管理模組 (Redesigned)
提供專業、現代感的深色和淺色主題 (類似 VS Code / Modern Web 風格)
"""

class ModernStyle:
    """現代化樣式管理類別"""

    # 現代深色主題 (類 VS Code Dark Modern)
    DARK_THEME = {
        'primary': '#3794FF',       # 鮮明的藍色
        'primary_hover': '#1F6FEB',
        'primary_text': '#FFFFFF',
        
        'background': '#181818',    # 極致深灰背景
        'surface': '#202020',       # 卡片/容器背景
        'surface_hover': '#2D2D2D',
        
        'border': '#333333',        # 微妙的邊框
        'text': '#E8E8E8',          # 主要文字
        'text_secondary': '#AAAAAA',# 次要文字
        
        'input_bg': '#2B2B2B',      # 輸入框背景
        'selection': '#264F78',     # 選取顏色
        'success': '#4CC38A',
        'warning': '#D29922',
        'danger': '#F85149',
    }

    # 現代淺色主題 (類 Modern Windows / Clean Web)
    LIGHT_THEME = {
        'primary': '#0078D4',       # 專業藍
        'primary_hover': '#106EBE',
        'primary_text': '#FFFFFF',
        
        'background': '#F3F3F3',    # 柔和灰白背景
        'surface': '#FFFFFF',       # 純白卡片
        'surface_hover': '#F7F7F7',
        
        'border': '#E5E5E5',        # 極淡邊框
        'text': '#242424',          # 深灰文字 (非純黑)
        'text_secondary': '#666666',
        
        'input_bg': '#FFFFFF',
        'selection': '#B3D7FF',
        'success': '#0F7B0F',
        'warning': '#9D5D00',
        'danger': '#C50F1F',
    }

    @classmethod
    def get_stylesheet(cls, theme_name="light"):
        colors = cls.DARK_THEME if theme_name == "dark" else cls.LIGHT_THEME
        
        is_dark = theme_name == "dark"
        shadow_alpha = "0.3" if is_dark else "0.05"
        
        return f"""
            /* 全域設定 */
            QMainWindow, QDialog {{
                background-color: {colors['background']};
            }}

            QWidget {{
                color: {colors['text']};
                font-family: "Segoe UI", "Microsoft JhengHei", sans-serif;
                font-size: 10pt;
            }}

            /* 分頁 (Tabs) - Modern Pill Style */
            QTabWidget::pane {{
                border: 1px solid {colors['border']};
                background-color: {colors['surface']};
                border-radius: 8px;
                top: -1px; /* 連接 Tab */
            }}

            QTabWidget::tab-bar {{
                alignment: left;
            }}

            QTabBar ::tab {{
                background: transparent;
                color: {colors['text_secondary']};
                padding: 8px 16px;
                margin: 4px 2px;
                border-radius: 6px;
                font-weight: 500;
            }}

            QTabBar::tab:selected {{
                background-color: {colors['surface']};
                color: {colors['primary']};
                font-weight: bold;
                border-bottom: 2px solid {colors['primary']};
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {colors['surface_hover']};
                color: {colors['text']};
            }}

            /* 按鈕 (Buttons) */
            QPushButton {{
                background-color: {colors['primary']};
                color: {colors['primary_text']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                min-height: 24px;
            }}

            QPushButton:hover {{
                background-color: {colors['primary_hover']};
            }}

            QPushButton:pressed {{
                background-color: {colors['primary']};
                padding-top: 9px; /* 按下效果 */
                padding-bottom: 7px;
            }}

            QPushButton:disabled {{
                background-color: {colors['border']};
                color: {colors['text_secondary']};
            }}

            /* 次要按鈕 / Outline Button */
            QPushButton[secondary="true"] {{
                background-color: transparent;
                border: 1px solid {colors['border']};
                color: {colors['text']};
            }}

            QPushButton[secondary="true"]:hover {{
                background-color: {colors['surface_hover']};
                border-color: {colors['text_secondary']};
            }}

            /* 輸入框 (Inputs) */
            QLineEdit, QPlainTextEdit, QTextEdit {{
                background-color: {colors['input_bg']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 8px;
                selection-background-color: {colors['selection']};
            }}

            QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
                border: 1px solid {colors['primary']};
            }}
            
            QLineEdit:disabled {{
                background-color: {colors['background']};
                color: {colors['text_secondary']};
            }}

            /* 下拉選單 (Combobox) */
            QComboBox {{
                background-color: {colors['input_bg']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 80px;
            }}

            QComboBox:hover {{
                background-color: {colors['surface_hover']};
            }}

            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}

            QComboBox::down-arrow {{
                image: none; /* 如果有自定義箭頭圖片可加 */
                border-top: 5px solid {colors['text_secondary']};
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                width: 0;
                height: 0;
                margin-right: 8px;
            }}

            /* 列表 (List Widget) */
            QListWidget {{
                background-color: {colors['input_bg']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 4px;
                outline: none;
            }}

            QListWidget::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin-bottom: 2px;
            }}

            QListWidget::item:selected {{
                background-color: {colors['selection']};
                color: {colors['text']}; /* 保持文字顏色或變白視 selection 色而定 */
            }}
            
            QListWidget::item:selected:!active {{
                background-color: {colors['surface_hover']};
            }}

            QListWidget::item:hover:!selected {{
                background-color: {colors['surface_hover']};
            }}

            /* 群組框 (GroupBox) - 乾淨風格 */
            QGroupBox {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                margin-top: 1.5em; /* 預留標題空間 */
                padding-top: 15px;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                color: {colors['primary']};
                font-weight: bold;
                background-color: transparent; 
            }}
            
            /* 若需要更像卡片的樣式，可透過 setProperty("card", True) */
            
            /* 滾動條 (Scrollbar) */
            QScrollBar:vertical {{
                background: {colors['background']};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {colors['border']};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {colors['text_secondary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            /* 選單列 (MenuBar) */
            QMenuBar {{
                background-color: {colors['surface']};
                border-bottom: 1px solid {colors['border']};
            }}
            QMenuBar::item:selected {{
                background-color: {colors['surface_hover']};
            }}
            
            QMenu {{
                background-color: {colors['surface']};
                border: 1px solid {colors['border']};
                padding: 5px;
                border-radius: 6px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {colors['primary']};
                color: white;
            }}

            /* 狀態列 */
            QStatusBar {{
                background-color: {colors['primary']};
                color: white;
            }}
        """

    @classmethod
    def get_dark_stylesheet(cls):
        return cls.get_stylesheet("dark")

    @classmethod
    def get_light_stylesheet(cls):
        return cls.get_stylesheet("light")

    @classmethod
    def get_card_style(cls, theme="light"):
        """Return the card-like group box stylesheet for the given theme."""
        colors = cls.DARK_THEME if theme == "dark" else cls.LIGHT_THEME
        
        # Determine specific colors for the card style
        if theme == "dark":
            border_color = colors['border']
            title_bg = "rgba(55, 148, 255, 0.15)" # Primary with opacity
            title_color = colors['primary']
        else:
            border_color = colors['border']
            title_bg = "rgba(0, 120, 212, 0.1)"  # Primary with opacity
            title_color = colors['primary']

        return f"""
            QGroupBox {{
                background-color: {colors['surface']};
                border: 1px solid {border_color};
                border-radius: 8px;
                margin-top: 24px;
                padding-top: 24px;
                padding-bottom: 12px;
                padding-left: 12px;
                padding-right: 12px;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 4px 12px;
                background-color: {title_bg};
                color: {title_color};
                border-radius: 4px;
                font-weight: bold;
                border: 1px solid {border_color};
            }}
        """
