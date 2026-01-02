"""
文檔轉換核心模組
支援 Word ↔ PDF 雙向轉換和 PDF 合併
"""
import os
import platform
import subprocess
import shutil
import shutil
import tempfile
import logging

# 設定 logger
logger = logging.getLogger(__name__)

# PDF 處理庫
try:
    import pypdf
    from pypdf.errors import FileNotDecryptedError, WrongPasswordError
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
    logger.warning("警告: pypdf 未安裝，PDF 功能將受限")

# Word 轉 PDF
try:
    import docx2pdf
    HAS_DOCX2PDF = True
except ImportError:
    HAS_DOCX2PDF = False
    logger.warning("警告: docx2pdf 未安裝，Word 轉 PDF 功能將受限")

# PDF 轉 Word
try:
    from pdf2docx import Converter
    HAS_PDF2DOCX = True
except ImportError:
    HAS_PDF2DOCX = False
    logger.warning("警告: pdf2docx 未安裝，PDF 轉 Word 功能將受限")

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
    logger.warning("警告: reportlab 未安裝，PDF 目錄和頁碼功能將受限")


try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("警告: Pillow 未安裝，圖片轉 PDF 功能將受到限制。")

def check_dependencies():
    """檢查依賴項是否已安裝"""
    return {
        'pypdf': HAS_PYPDF,
        'docx2pdf': HAS_DOCX2PDF,
        'pdf2docx': HAS_PDF2DOCX,
        'reportlab': HAS_REPORTLAB,
        'Pillow': HAS_PIL
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
            logger.error(f"字型載入錯誤: {str(e)}")

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
            logger.error(f"字型載入錯誤: {str(e)}")

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
            logger.error(f"字型載入錯誤: {str(e)}")

    return 'Helvetica'


# 初始化字型
CHINESE_FONT = setup_fonts()

PDF_EXTENSIONS = {'.pdf'}
WORD_EXTENSIONS = {'.doc', '.docx'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}


class PasswordRequiredError(Exception):
    """Raised when an encrypted PDF requires a password but no password was provided."""


class WrongPasswordProvided(Exception):
    """Raised when the provided PDF password is incorrect."""


def detect_file_type(file_path):
    """Return file category: pdf/word/image/unknown."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in PDF_EXTENSIONS:
        return 'pdf'
    if ext in WORD_EXTENSIONS:
        return 'word'
    if ext in IMAGE_EXTENSIONS:
        return 'image'
    return 'unknown'


def convert_image_to_pdf(image_path, pdf_path):
    """Convert a single image to PDF."""
    if not HAS_PIL:
        logger.error("Error: Pillow is not installed, cannot convert image to PDF.")
        return False
    try:
        with Image.open(image_path) as img:
            if img.mode not in ("RGB", "CMYK"):
                img = img.convert("RGB")
            img.save(pdf_path, "PDF")
        return os.path.exists(pdf_path)
    except Exception as exc:
        logger.error(f"Image to PDF failed: {exc}")
        return False


def _write_reader_to_temp(reader):
    fd, temp_path = tempfile.mkstemp(suffix='.pdf')
    os.close(fd)
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with open(temp_path, 'wb') as output_file:
        writer.write(output_file)
    return temp_path


def ensure_unlocked_pdf(pdf_path, password=None):
    """Ensure a PDF can be read; returns (path_to_use, temp_path_or_None)."""
    if not HAS_PYPDF:
        raise RuntimeError("pypdf is required to handle encrypted PDFs")
    reader = pypdf.PdfReader(pdf_path)
    if not reader.is_encrypted:
        return pdf_path, None
    try:
        if reader.decrypt('') == 1:
            temp_pdf = _write_reader_to_temp(reader)
            return temp_pdf, temp_pdf
    except WrongPasswordError:
        pass
    if password is None:
        raise PasswordRequiredError(pdf_path)
    if reader.decrypt(password) != 1:
        raise WrongPasswordProvided(pdf_path)
    temp_pdf = _write_reader_to_temp(reader)
    return temp_pdf, temp_pdf


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
        logger.error("錯誤: 缺少 docx2pdf 套件")
        return False

    word_path = os.path.abspath(word_path)
    pdf_path = os.path.abspath(pdf_path)

    logger.info(f"開始轉換: {word_path} -> {pdf_path}")

    # 方法1: 使用 docx2pdf
    try:
        logger.info("使用 docx2pdf 轉換...")
        docx2pdf.convert(word_path, pdf_path)
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            logger.info("轉換成功!")
            return True
    except Exception as e:
        logger.warning(f"docx2pdf 轉換失敗: {str(e)}")

    # 方法2: 使用 LibreOffice (如果安裝了)
    try:
        logger.info("嘗試使用 LibreOffice 轉換...")
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
                logger.info("LibreOffice 轉換成功!")
                return True
    except Exception as e:
        logger.warning(f"LibreOffice 轉換失敗: {str(e)}")

    logger.error("所有轉換方法都失敗了")
    return False


def convert_pdf_to_word(pdf_path, word_path, password=None):
    """
    將 PDF 轉換為 Word 檔案。
    """
    if not HAS_PDF2DOCX:
        logger.error("錯誤: 缺少 pdf2docx 套件")
        return False

    temp_pdf = None
    try:
        source_pdf, temp_pdf = ensure_unlocked_pdf(pdf_path, password=password)
        logger.info(f"開始轉換: {pdf_path} -> {word_path}")

        cv = Converter(source_pdf)
        cv.convert(word_path, start=0, end=None)
        cv.close()

        if os.path.exists(word_path) and os.path.getsize(word_path) > 0:
            logger.info("PDF 轉 Word 完成!")
            return True
        else:
            logger.error("PDF 轉 Word 失敗: 輸出檔案為空")
            return False
    except PasswordRequiredError:
        raise
    except WrongPasswordProvided:
        raise
    except Exception as e:
        logger.error(f"PDF 轉 Word 失敗: {str(e)}")
        return False
    finally:
        if temp_pdf and os.path.exists(temp_pdf):
            try:
                os.remove(temp_pdf)
            except Exception:
                pass

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
        logger.error("錯誤: 缺少 pypdf 套件")
        return False

    if not HAS_REPORTLAB:
        if add_toc or add_page_numbers:
            logger.warning("警告: 缺少 reportlab 套件，無法添加目錄或頁碼")
            add_toc = False
            add_page_numbers = False

    try:
        logger.info(f"開始合併 {len(pdf_files)} 個 PDF 文件...")

        # 如果需要添加目錄或頁碼，使用更複雜的流程
        if add_toc or add_page_numbers:
            return _merge_pdfs_with_extras(pdf_files, output_path, add_toc, add_page_numbers)

        # 簡單合併
        merger = pypdf.PdfWriter()

        for pdf_file in pdf_files:
            if not os.path.exists(pdf_file):
                logger.warning(f"警告: 文件不存在: {pdf_file}")
                continue

            try:
                reader = pypdf.PdfReader(pdf_file)
                for page in reader.pages:
                    merger.add_page(page)
                logger.info(f"✓ 已添加: {os.path.basename(pdf_file)}")
            except Exception as e:
                logger.error(f"✗ 無法處理: {os.path.basename(pdf_file)} - {e}")

        with open(output_path, 'wb') as output_file:
            merger.write(output_file)

        logger.info(f"合併完成: {output_path}")
        return True

    except Exception as e:
        logger.error(f"PDF 合併失敗: {str(e)}")
        return False


def _merge_pdfs_with_extras(pdf_files, output_path, add_toc, add_page_numbers):
    """
    合併 PDF 並添加目錄和/或頁碼

    Args:
        pdf_files: PDF 文件路徑列表
        output_path: 輸出路徑
        add_toc: 是否添加目錄
        add_page_numbers: 是否添加頁碼

    Returns:
        bool: 是否成功
    """
    import tempfile
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    try:
        # 設定中文字型
        font_name = setup_fonts()

        # 收集所有 PDF 資訊
        pdf_info_list = []
        total_pages = 0

        for pdf_file in pdf_files:
            if not os.path.exists(pdf_file):
                logger.warning(f"警告: 文件不存在: {pdf_file}")
                continue

            try:
                reader = pypdf.PdfReader(pdf_file)
                page_count = len(reader.pages)
                pdf_info_list.append({
                    'path': pdf_file,
                    'name': os.path.basename(pdf_file),
                    'reader': reader,
                    'page_count': page_count,
                    'start_page': total_pages + 1  # 如果有目錄，這個會調整
                })
                total_pages += page_count
                logger.info(f"✓ 已讀取: {os.path.basename(pdf_file)} ({page_count} 頁)")
            except Exception as e:
                logger.error(f"✗ 無法讀取: {os.path.basename(pdf_file)} - {e}")

        if not pdf_info_list:
            logger.error("錯誤: 沒有有效的 PDF 文件")
            return False

        # 創建臨時文件
        temp_files = []

        # 1. 如果需要，生成目錄頁面
        toc_path = None
        if add_toc:
            toc_path = tempfile.mktemp(suffix='.pdf')
            temp_files.append(toc_path)
            _create_toc_page(toc_path, pdf_info_list, font_name)

            # 調整頁碼（目錄佔 1 頁）
            for info in pdf_info_list:
                info['start_page'] += 1

        # 2. 如果需要添加頁碼，為每個 PDF 添加頁碼
        if add_page_numbers:
            processed_pdfs = []
            current_page = 1 if not add_toc else 2  # 目錄是第 1 頁

            for info in pdf_info_list:
                temp_pdf = tempfile.mktemp(suffix='.pdf')
                temp_files.append(temp_pdf)
                _add_page_numbers_to_pdf(
                    info['path'],
                    temp_pdf,
                    start_number=current_page,
                    font_name=font_name
                )
                processed_pdfs.append(temp_pdf)
                current_page += info['page_count']

            # 使用添加了頁碼的 PDF
            pdf_paths_to_merge = processed_pdfs
        else:
            pdf_paths_to_merge = [info['path'] for info in pdf_info_list]

        # 3. 合併所有 PDF
        merger = pypdf.PdfWriter()

        # 先添加目錄
        if toc_path:
            toc_reader = pypdf.PdfReader(toc_path)
            for page in toc_reader.pages:
                merger.add_page(page)

        # 添加所有 PDF
        for pdf_path in pdf_paths_to_merge:
            reader = pypdf.PdfReader(pdf_path)
            for page in reader.pages:
                merger.add_page(page)

        # 寫入輸出文件
        with open(output_path, 'wb') as output_file:
            merger.write(output_file)

        # 清理臨時文件
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass

        logger.info(f"合併完成: {output_path}")
        return True

    except Exception as e:
        logger.error(f"合併失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def _create_toc_page(output_path, pdf_info_list, font_name):
    """
    創建目錄頁面

    Args:
        output_path: 輸出路徑
        pdf_info_list: PDF 資訊列表
        font_name: 字型名稱
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # 標題
    c.setFont(font_name, 24)
    c.drawCentredString(width / 2, height - 80, "目錄 Table of Contents")

    # 分隔線
    c.setLineWidth(2)
    c.line(50, height - 100, width - 50, height - 100)

    # 列出所有 PDF
    c.setFont(font_name, 12)
    y = height - 140

    for i, info in enumerate(pdf_info_list, 1):
        if y < 100:  # 頁面空間不足時換頁
            c.showPage()
            c.setFont(font_name, 12)
            y = height - 60

        # 檔案名稱
        text = f"{i}. {info['name']}"
        c.drawString(80, y, text)

        # 頁數資訊
        page_info = f"{info['page_count']} 頁，第 {info['start_page']} 頁起"
        c.drawRightString(width - 80, y, page_info)

        y -= 25

    c.save()


def _add_page_numbers_to_pdf(input_path, output_path, start_number=1, font_name="Helvetica"):
    """
    為 PDF 添加頁碼

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        start_number: 起始頁碼
        font_name: 字型名稱
    """
    import tempfile
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    reader = pypdf.PdfReader(input_path)
    writer = pypdf.PdfWriter()

    for i, page in enumerate(reader.pages):
        # 創建頁碼水印
        temp_pdf = tempfile.mktemp(suffix='.pdf')

        # 獲取頁面尺寸
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        c = canvas.Canvas(temp_pdf, pagesize=(page_width, page_height))
        c.setFont(font_name, 10)

        # 底部居中頁碼
        page_number = start_number + i
        c.drawCentredString(page_width / 2, 30, str(page_number))

        c.save()

        # 合併頁碼到原始頁面
        overlay_reader = pypdf.PdfReader(temp_pdf)
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

        # 清理臨時文件
        try:
            os.remove(temp_pdf)
        except:
            pass

    with open(output_path, 'wb') as output_file:
        writer.write(output_file)


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
        logger.error(f"無法讀取 PDF 資訊: {e}")
        return {'pages': 0, 'size_mb': 0, 'encrypted': False}


def add_text_watermark_to_pdf(input_path, output_path, watermark_text,
                               position='center', opacity=0.3, font_size=40,
                               color=(128, 128, 128), rotation=45, margin=10):
    """
    為 PDF 文件添加文字浮水印

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        watermark_text: 浮水印文字
        position: 位置 ('center', 'top-left', 'top-right', 'bottom-left', 'bottom-right')
        opacity: 透明度 (0.0-1.0)
        font_size: 字體大小
        color: 顏色 (R, G, B) tuple
        rotation: 旋轉角度
        margin: 邊距（像素）

    Returns:
        bool: 是否成功
    """
    if not HAS_PYPDF or not HAS_REPORTLAB:
        logger.error("錯誤: 需要 pypdf 和 reportlab 套件")
        return False

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import Color

        # 設定中文字型
        font_name = setup_fonts()

        reader = pypdf.PdfReader(input_path)
        writer = pypdf.PdfWriter()

        for page_num, page in enumerate(reader.pages):
            # 創建浮水印
            temp_pdf = tempfile.mktemp(suffix='.pdf')

            # 獲取頁面尺寸
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            c = canvas.Canvas(temp_pdf, pagesize=(page_width, page_height))

            # 設定透明度和顏色
            watermark_color = Color(color[0]/255, color[1]/255, color[2]/255, alpha=opacity)
            c.setFillColor(watermark_color)
            c.setFont(font_name, font_size)

            # 計算位置（使用自訂邊距）
            text_width = c.stringWidth(watermark_text, font_name, font_size)

            if position == 'center':
                x = page_width / 2
                y = page_height / 2
            elif position == 'top-left':
                x = margin
                y = page_height - margin - font_size
            elif position == 'top-right':
                x = page_width - text_width - margin
                y = page_height - margin - font_size
            elif position == 'bottom-left':
                x = margin
                y = margin
            elif position == 'bottom-right':
                x = page_width - text_width - margin
                y = margin
            else:
                x = page_width / 2
                y = page_height / 2

            # 繪製旋轉的文字
            c.saveState()
            c.translate(x, y)
            c.rotate(rotation)
            c.drawString(0, 0, watermark_text)
            c.restoreState()

            c.save()

            # 合併浮水印到原始頁面
            watermark_reader = pypdf.PdfReader(temp_pdf)
            page.merge_page(watermark_reader.pages[0])
            writer.add_page(page)

            # 清理臨時文件
            try:
                os.remove(temp_pdf)
            except:
                pass

            print(f"已處理第 {page_num + 1}/{len(reader.pages)} 頁")

        # 寫入輸出文件
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        logger.info(f"PDF 浮水印添加完成: {output_path}")
        return True

    except Exception as e:
        logger.error(f"添加 PDF 浮水印失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def add_image_watermark_to_pdf(input_path, output_path, watermark_image_path,
                                position='center', opacity=0.5, scale=0.2, margin=10):
    """
    為 PDF 文件添加圖片浮水印

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        watermark_image_path: 浮水印圖片路徑
        position: 位置 ('center', 'top-left', 'top-right', 'bottom-left', 'bottom-right')
        opacity: 透明度 (0.0-1.0)
        scale: 縮放比例 (相對於頁面寬度)
        margin: 邊距（像素）

    Returns:
        bool: 是否成功
    """
    if not HAS_PYPDF or not HAS_REPORTLAB or not HAS_PIL:
        logger.error("錯誤: 需要 pypdf、reportlab 和 Pillow 套件")
        return False

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader

        if not os.path.exists(watermark_image_path):
            logger.error(f"錯誤: 浮水印圖片不存在: {watermark_image_path}")
            return False

        reader = pypdf.PdfReader(input_path)
        writer = pypdf.PdfWriter()

        # 載入浮水印圖片
        watermark_img = Image.open(watermark_image_path)
        if watermark_img.mode != 'RGBA':
            watermark_img = watermark_img.convert('RGBA')

        for page_num, page in enumerate(reader.pages):
            # 創建浮水印
            temp_pdf = tempfile.mktemp(suffix='.pdf')

            # 獲取頁面尺寸
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            c = canvas.Canvas(temp_pdf, pagesize=(page_width, page_height))

            # 計算浮水印尺寸
            wm_width = page_width * scale
            wm_height = watermark_img.height * wm_width / watermark_img.width

            # 調整透明度
            if opacity < 1.0:
                alpha = watermark_img.split()[3]
                alpha = alpha.point(lambda p: int(p * opacity))
                watermark_img.putalpha(alpha)

            # 計算位置（使用自訂邊距）
            if position == 'center':
                x = (page_width - wm_width) / 2
                y = (page_height - wm_height) / 2
            elif position == 'top-left':
                x = margin
                y = page_height - wm_height - margin
            elif position == 'top-right':
                x = page_width - wm_width - margin
                y = page_height - wm_height - margin
            elif position == 'bottom-left':
                x = margin
                y = margin
            elif position == 'bottom-right':
                x = page_width - wm_width - margin
                y = margin
            else:
                x = (page_width - wm_width) / 2
                y = (page_height - wm_height) / 2

            # 儲存浮水印圖片到臨時文件
            temp_img = tempfile.mktemp(suffix='.png')
            watermark_img.save(temp_img, 'PNG')

            # 繪製圖片
            c.drawImage(temp_img, x, y, width=wm_width, height=wm_height, mask='auto')
            c.save()

            # 合併浮水印到原始頁面
            watermark_reader = pypdf.PdfReader(temp_pdf)
            page.merge_page(watermark_reader.pages[0])
            writer.add_page(page)

            # 清理臨時文件
            try:
                os.remove(temp_pdf)
                os.remove(temp_img)
            except:
                pass

            logger.info(f"已處理第 {page_num + 1}/{len(reader.pages)} 頁")

        # 寫入輸出文件
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        logger.info(f"PDF 圖片浮水印添加完成: {output_path}")
        return True

    except Exception as e:
        logger.error(f"添加 PDF 圖片浮水印失敗: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    
def extract_page(pdf_path, page_number, output_path):
    """
    從 PDF 提取指定頁面

    Args:
        pdf_path: 來源 PDF 路徑
        page_number: 頁碼 (1-based)
        output_path: 輸出 PDF 路徑

    Returns:
        bool: 是否成功
    """
    try:
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        if page_number < 1 or page_number > total_pages:
            logger.error(f"頁碼超出範圍: {page_number} (總頁數: {total_pages})")
            return False

        writer = pypdf.PdfWriter()
        writer.add_page(reader.pages[page_number - 1])

        with open(output_path, 'wb') as f:
            writer.write(f)
            
        logger.info(f"已提取第 {page_number} 頁至: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"提取頁面失敗: {str(e)}")
        return False
