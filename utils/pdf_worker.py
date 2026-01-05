
from PyQt5.QtCore import QThread, pyqtSignal
from utils.pdf_tools import PDFToolKit
import os

class PDFToolsWorker(QThread):
    """
    處理 PDF 進階功能的背景工作
    支援模式: 'split', 'extract', 'to_image', 'compress'
    """
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, mode, **kwargs):
        super().__init__()
        self.mode = mode
        self.kwargs = kwargs
        self.is_cancelled = False
        
    def run(self):
        try:
            self.progress.emit(0)
            
            if self.mode == 'split' or self.mode == 'extract':
                input_path = self.kwargs.get('input_path')
                range_str = self.kwargs.get('range_str')
                output_dir = self.kwargs.get('output_dir')
                
                # Validate PDF
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(input_path)
                    total_pages = len(reader.pages)
                except Exception as e:
                    self.finished.emit(False, f"無法讀取 PDF: {str(e)}")
                    return

                # Parse Range
                indices = PDFToolKit.parse_range_string(range_str, total_pages)
                if not indices:
                    self.finished.emit(False, "無效的頁碼範圍")
                    return
                
                self.progress.emit(30)
                self.status.emit(f"正在處理 {len(indices)} 個頁面...")
                
                if self.mode == 'split':
                    # 合併為一個新 PDF
                    out_path = PDFToolKit.split_pdf(input_path, indices, output_dir)
                    self.progress.emit(100)
                    self.finished.emit(True, f"拆分完成！\n已儲存為：{out_path}")
                    
                elif self.mode == 'extract':
                    # 分別儲存
                    files = PDFToolKit.extract_pages_individual(input_path, indices, output_dir)
                    self.progress.emit(100)
                    self.finished.emit(True, f"擷取完成！\n共產出 {len(files)} 個檔案於：\n{output_dir}")

            elif self.mode == 'to_image':
                input_path = self.kwargs.get('input_path')
                output_dir = self.kwargs.get('output_dir')
                fmt = self.kwargs.get('format', 'png')
                dpi = self.kwargs.get('dpi', 150)
                
                def callback(p, s):
                    if self.is_cancelled:
                        raise Exception("已取消")
                    self.progress.emit(p)
                    self.status.emit(s)
                
                try:
                    files = PDFToolKit.pdf_to_images(
                        input_path, output_dir, fmt, dpi, callback=callback
                    )
                    self.progress.emit(100)
                    self.finished.emit(True, f"轉換完成！\n共產出 {len(files)} 張圖片")
                except Exception as e:
                    if "已取消" in str(e):
                        self.finished.emit(False, "操作已取消")
                    else:
                        raise e

            elif self.mode == 'compress':
                input_path = self.kwargs.get('input_path')
                output_path = self.kwargs.get('output_path')
                compress_mode = self.kwargs.get('compress_mode', 'basic')  # basic, image, deep
                quality = self.kwargs.get('quality', 70)
                dpi = self.kwargs.get('dpi', 150)
                
                def callback(p, s):
                    if self.is_cancelled:
                        raise Exception("已取消")
                    self.progress.emit(p)
                    self.status.emit(s)
                
                try:
                    if compress_mode == 'basic':
                        result = PDFToolKit.compress_pdf_basic(input_path, output_path, callback=callback)
                    elif compress_mode == 'image':
                        result = PDFToolKit.compress_pdf_images(input_path, output_path, quality=quality, callback=callback)
                    elif compress_mode == 'deep':
                        result = PDFToolKit.compress_pdf_deep(input_path, output_path, quality=quality, dpi=dpi, callback=callback)
                    else:
                        self.finished.emit(False, f"不支援的壓縮模式: {compress_mode}")
                        return
                    
                    _, original_size, compressed_size = result
                    
                    # 計算壓縮率
                    if original_size > 0:
                        ratio = (1 - compressed_size / original_size) * 100
                        original_mb = original_size / (1024 * 1024)
                        compressed_mb = compressed_size / (1024 * 1024)
                        
                        self.progress.emit(100)
                        self.finished.emit(True, 
                            f"壓縮完成！\n"
                            f"原始大小：{original_mb:.2f} MB\n"
                            f"壓縮後：{compressed_mb:.2f} MB\n"
                            f"節省了 {ratio:.1f}%\n\n"
                            f"已儲存為：{output_path}")
                    else:
                        self.progress.emit(100)
                        self.finished.emit(True, f"壓縮完成！\n已儲存為：{output_path}")
                        
                except Exception as e:
                    if "已取消" in str(e):
                        self.finished.emit(False, "操作已取消")
                    else:
                        raise e

        except Exception as e:
            self.finished.emit(False, f"處理失敗：{str(e)}")

    def cancel(self):
        self.is_cancelled = True
