"""
文檔轉換核心模組
支援 Word ↔ PDF 雙向轉換和 PDF 合併
"""
import os
import platform
import subprocess
import shutil
import tempfile

# PDF 處理庫
try:
    import pypdf
    from pypdf.errors import FileNotDecryptedError, WrongPasswordError
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
    print("警告: pypdf 未安裝，PDF 功能將受限")

# Word 轉 PDF
try:
    import docx2pdf
    HAS_DOCX2PDF = True
except ImportError:
    HAS_DOCX2PDF = False
    print("警告: docx2pdf 未安裝，Word 轉 PDF 功能將受限")

# PDF 轉 Word
try:
    from pdf2docx import Converter
    HAS_PDF2DOCX = True
except ImportError:
    HAS_PDF2DOCX = False
    print("警告: pdf2docx 未安裝，PDF 轉 Word 功能將受限")

# ReportLab (PDF 生成)
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("警告: reportlab 未安裝，PDF 目錄和頁碼功能將受限")


def check_dependencies():
    """檢查依賴項是否已安裝"""
    return {
        'pypdf': HAS_PYPDF,
        'docx2pdf': HAS_DOCX2PDF,
        'pdf2docx': HAS_PDF2DOCX,
        'reportlab': HAS_REPORTLAB
    }


def setup_fonts():
    """設定繁體中文字型，根據不同作業系統選擇適當的字型"""
    if not HAS_REPORTLAB:
        return 'Helvetica'

    system = platform.system()

    if system == 'Windows':
        try:
            font_paths = [
                "C:/Windows/Fonts/msjh.ttc",      # 微軟正黑體
                "C:/Windows/Fonts/simsun.ttc",    # 新細明體
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    return 'ChineseFont'
        except Exception as e:
            print(f"字型載入錯誤: {str(e)}")

    elif system == 'Linux':
        try:
            font_paths = [
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
                '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    return 'ChineseFont'
        except Exception as e:
            print(f"字型載入錯誤: {str(e)}")

    elif system == 'Darwin':  # macOS
        try:
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',
                '/System/Library/Fonts/STHeiti Light.ttc'
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    return 'ChineseFont'
        except Exception as e:
            print(f"字型載入錯誤: {str(e)}")

    return 'Helvetica'


# 初始化字型
CHINESE_FONT = setup_fonts()


def convert_word_to_pdf(word_path, pdf_path):
    """
    將 Word 文件轉換為 PDF

    Args:
        word_path: Word 文件路徑
        pdf_path: 輸出 PDF 路徑

    Returns:
        bool: 是否轉換成功
    """
    if not HAS_DOCX2PDF:
        print("錯誤: 缺少 docx2pdf 套件")
        return False

    word_path = os.path.abspath(word_path)
    pdf_path = os.path.abspath(pdf_path)

    print(f"開始轉換: {word_path} -> {pdf_path}")

    # 方法1: 使用 docx2pdf
    try:
        print("使用 docx2pdf 轉換...")
        docx2pdf.convert(word_path, pdf_path)
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            print("轉換成功!")
            return True
    except Exception as e:
        print(f"docx2pdf 轉換失敗: {str(e)}")

    # 方法2: 使用 LibreOffice (如果安裝了)
    try:
        print("嘗試使用 LibreOffice 轉換...")
        system = platform.system()

        soffice_path = None
        if system == 'Windows':
            soffice_paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
            ]
            for path in soffice_paths:
                if os.path.exists(path):
                    soffice_path = path
                    break
        else:
            # Linux/Mac
            try:
                process = subprocess.Popen(['which', 'soffice'], stdout=subprocess.PIPE)
                result = process.communicate()[0].strip()
                if result:
                    soffice_path = result.decode('utf-8')
            except:
                pass

        if soffice_path:
            cmd = [soffice_path, '--headless', '--convert-to', 'pdf', '--outdir',
                   os.path.dirname(pdf_path), word_path]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            base_name = os.path.splitext(os.path.basename(word_path))[0]
            temp_pdf = os.path.join(os.path.dirname(pdf_path), f"{base_name}.pdf")

            if os.path.exists(temp_pdf):
                if temp_pdf != pdf_path:
                    shutil.move(temp_pdf, pdf_path)
                print("LibreOffice 轉換成功!")
                return True
    except Exception as e:
        print(f"LibreOffice 轉換失敗: {str(e)}")

    print("所有轉換方法都失敗了")
    return False


def convert_pdf_to_word(pdf_path, word_path):
    """
    將 PDF 轉換為 Word 文件

    Args:
        pdf_path: PDF 文件路徑
        word_path: 輸出 Word 路徑

    Returns:
        bool: 是否轉換成功
    """
    if not HAS_PDF2DOCX:
        print("錯誤: 缺少 pdf2docx 套件")
        return False

    try:
        print(f"開始轉換: {pdf_path} -> {word_path}")

        cv = Converter(pdf_path)
        cv.convert(word_path, start=0, end=None)
        cv.close()

        if os.path.exists(word_path) and os.path.getsize(word_path) > 0:
            print("PDF 轉 Word 成功!")
            return True
        else:
            print("PDF 轉 Word 失敗: 輸出檔案為空")
            return False
    except Exception as e:
        print(f"PDF 轉 Word 失敗: {str(e)}")
        return False


def merge_pdfs(pdf_files, output_path, add_toc=False, add_page_numbers=False):
    """
    合併多個 PDF 文件

    Args:
        pdf_files: PDF 文件路徑列表
        output_path: 輸出 PDF 路徑
        add_toc: 是否添加目錄
        add_page_numbers: 是否添加頁碼

    Returns:
        bool: 是否合併成功
    """
    if not HAS_PYPDF:
        print("錯誤: 缺少 pypdf 套件")
        return False

    try:
        print(f"開始合併 {len(pdf_files)} 個 PDF 文件...")

        merger = pypdf.PdfWriter()

        for pdf_file in pdf_files:
            if not os.path.exists(pdf_file):
                print(f"警告: 文件不存在: {pdf_file}")
                continue

            try:
                reader = pypdf.PdfReader(pdf_file)
                for page in reader.pages:
                    merger.add_page(page)
                print(f"✓ 已添加: {os.path.basename(pdf_file)}")
            except Exception as e:
                print(f"✗ 無法處理: {os.path.basename(pdf_file)} - {e}")

        with open(output_path, 'wb') as output_file:
            merger.write(output_file)

        print(f"合併完成: {output_path}")
        return True

    except Exception as e:
        print(f"PDF 合併失敗: {str(e)}")
        return False


def to_roman(num):
    """將數字轉換為羅馬數字"""
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syms[i]
            num -= val[i]
        i += 1
    return roman_num


def get_pdf_info(pdf_path):
    """
    取得 PDF 文件資訊

    Args:
        pdf_path: PDF 文件路徑

    Returns:
        dict: 包含頁數、檔案大小等資訊
    """
    if not HAS_PYPDF:
        return {'pages': 0, 'size_mb': 0}

    try:
        reader = pypdf.PdfReader(pdf_path)
        file_size = os.path.getsize(pdf_path) / (1024 * 1024)

        return {
            'pages': len(reader.pages),
            'size_mb': round(file_size, 2),
            'encrypted': reader.is_encrypted
        }
    except Exception as e:
        print(f"無法讀取 PDF 資訊: {e}")
        return {'pages': 0, 'size_mb': 0, 'encrypted': False}
