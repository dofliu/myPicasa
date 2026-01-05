
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

    @staticmethod
    def compress_pdf_basic(input_path, output_path, callback=None):
        """
        基礎壓縮：壓縮內容串流 + 移除重複物件（無損壓縮）
        使用 pypdf 的 compress_content_streams 和 compress_identical_objects
        
        Returns: (output_path, original_size, compressed_size)
        """
        if callback:
            callback(10, "讀取 PDF 檔案...")
        
        original_size = os.path.getsize(input_path)
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        # 使用 clone_reader_document_root 來正確複製文檔結構
        writer.clone_reader_document_root(reader)
        
        total_pages = len(writer.pages)
        
        for i, page in enumerate(writer.pages):
            if callback:
                progress = 10 + int((i / total_pages) * 70)
                callback(progress, f"壓縮第 {i+1}/{total_pages} 頁...")
            
            # 壓縮頁面內容串流
            try:
                page.compress_content_streams()
            except Exception:
                pass
        
        if callback:
            callback(85, "移除重複物件...")
        
        # 移除重複物件
        try:
            writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        except Exception:
            pass
        
        if callback:
            callback(95, "儲存檔案...")
        
        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        
        compressed_size = os.path.getsize(output_path)
        return output_path, original_size, compressed_size

    @staticmethod
    def compress_pdf_images(input_path, output_path, quality=70, callback=None):
        """
        圖片壓縮：降低 PDF 中圖片的品質
        使用 pypdf 的 image.replace() 功能
        
        Args:
            quality: 圖片品質 (1-100)
            
        Returns: (output_path, original_size, compressed_size)
        """
        if callback:
            callback(10, "讀取 PDF 檔案...")
        
        original_size = os.path.getsize(input_path)
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        # 使用 clone_reader_document_root 來正確複製文檔結構
        writer.clone_reader_document_root(reader)
        
        total_pages = len(writer.pages)
        
        if callback:
            callback(30, "壓縮圖片中...")
        
        # 處理每一頁的圖片
        for i, page in enumerate(writer.pages):
            if callback:
                progress = 30 + int((i / total_pages) * 50)
                callback(progress, f"處理第 {i+1}/{total_pages} 頁的圖片...")
            
            try:
                # 壓縮頁面內容串流
                page.compress_content_streams()
                
                # 嘗試降低圖片品質
                for img in page.images:
                    try:
                        img.replace(img.image, quality=quality)
                    except Exception:
                        # 某些圖片格式可能不支援，跳過
                        pass
            except Exception:
                # 某些頁面可能沒有圖片或處理失敗，繼續處理下一頁
                pass
        
        if callback:
            callback(90, "移除重複物件...")
        
        # 移除重複物件以進一步減小體積
        try:
            writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)
        except Exception:
            pass
        
        if callback:
            callback(95, "儲存檔案...")
        
        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        
        compressed_size = os.path.getsize(output_path)
        return output_path, original_size, compressed_size

    @staticmethod
    def compress_pdf_deep(input_path, output_path, quality=70, dpi=150, callback=None):
        """
        深度壓縮：將每頁轉為 JPEG 並重新組裝為 PDF
        這種方式可以達到最大壓縮率，但會損失非圖片內容的清晰度
        
        Args:
            quality: JPEG 品質 (1-100)
            dpi: 轉換時的 DPI
            
        Returns: (output_path, original_size, compressed_size)
        """
        import io
        from PIL import Image
        
        if callback:
            callback(5, "讀取 PDF 檔案...")
        
        original_size = os.path.getsize(input_path)
        doc = fitz.open(input_path)
        total_pages = len(doc)
        
        # 收集所有頁面的圖片
        images = []
        
        for i in range(total_pages):
            if callback:
                progress = 5 + int((i / total_pages) * 70)
                callback(progress, f"轉換第 {i+1}/{total_pages} 頁為圖片...")
            
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=dpi)
            
            # 轉為 PIL Image
            img_data = pix.tobytes("ppm")
            img = Image.open(io.BytesIO(img_data))
            
            # 轉換為 RGB（某些頁面可能是 RGBA）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            images.append(img)
        
        doc.close()
        
        if callback:
            callback(80, "重新組裝 PDF...")
        
        if not images:
            raise ValueError("PDF 沒有可處理的頁面")
        
        # 將所有圖片合併為 PDF
        # 第一張作為基礎，其餘附加
        first_img = images[0]
        
        if callback:
            callback(90, "儲存壓縮後的 PDF...")
        
        if len(images) == 1:
            first_img.save(output_path, "PDF", quality=quality, optimize=True)
        else:
            first_img.save(
                output_path, 
                "PDF", 
                quality=quality, 
                optimize=True,
                save_all=True, 
                append_images=images[1:]
            )
        
        # 清理
        for img in images:
            img.close()
        
        compressed_size = os.path.getsize(output_path)
        return output_path, original_size, compressed_size
