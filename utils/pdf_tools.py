
import os
import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
from natsort import natsorted

class PDFToolKit:
    """PDF 進階工具：拆分與格式轉換"""

    @staticmethod
    def parse_range_string(range_str, max_pages):
        """
        解析頁碼範圍字串，返回 0-based page index list。
        格式支援: "1, 3, 5-7" -> [0, 2, 4, 5, 6]
        """
        if not range_str or not range_str.strip():
            return []
            
        pages = set()
        parts = range_str.split(',')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    # 轉換為 0-based，且確保範圍有效
                    start = max(1, start)
                    end = min(max_pages, end)
                    if start <= end:
                        for i in range(start - 1, end):
                            pages.add(i)
                except ValueError:
                    continue
            else:
                try:
                    page = int(part)
                    if 1 <= page <= max_pages:
                        pages.add(page - 1)
                except ValueError:
                    continue
                    
        return sorted(list(pages))

    @staticmethod
    def split_pdf(input_path, page_indices, output_dir):
        """
        拆分 PDF 並儲存選定頁面
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        reader = PdfReader(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        
        # 建立一個包含選定頁面的新 PDF
        writer = PdfWriter()
        
        for idx in page_indices:
            if 0 <= idx < len(reader.pages):
                writer.add_page(reader.pages[idx])
                
        output_path = os.path.join(output_dir, f"{base_name}_split.pdf")
        with open(output_path, "wb") as f_out:
            writer.write(f_out)
            
        return output_path

    @staticmethod
    def extract_pages_individual(input_path, page_indices, output_dir):
        """
        將選定頁面分別儲存為單獨的 PDF
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        reader = PdfReader(input_path)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_files = []
        
        for idx in page_indices:
            if 0 <= idx < len(reader.pages):
                writer = PdfWriter()
                writer.add_page(reader.pages[idx])
                
                # Page number is 1-based in filename
                out_name = f"{base_name}_page_{idx+1}.pdf"
                out_path = os.path.join(output_dir, out_name)
                
                with open(out_path, "wb") as f_out:
                    writer.write(f_out)
                output_files.append(out_path)
                
        return output_files

    @staticmethod
    def pdf_to_images(input_path, output_dir, fmt="png", dpi=150, callback=None):
        """
        將 PDF 轉為圖片 (使用 PyMuPDF)
        callback(progress_int, status_str)
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        doc = fitz.open(input_path)
        total_pages = len(doc)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_files = []
        
        for i in range(total_pages):
            if callback:
                # Check for cancellation if callback returns False (not implemented here but good practice)
                callback(int((i / total_pages) * 100), f"正在轉換第 {i+1}/{total_pages} 頁...")
                
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=dpi)
            
            output_name = f"{base_name}_page_{i+1}.{fmt}"
            output_path = os.path.join(output_dir, output_name)
            pix.save(output_path)
            output_files.append(output_path)
            
        doc.close()
        return output_files
