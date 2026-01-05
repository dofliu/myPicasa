"""
Markdown 文件轉換器
支援 MD ↔ PDF, MD ↔ DOCX 雙向轉換

依賴：pypandoc (需要 Pandoc 執行檔)
"""

import os
import tempfile
import logging

logger = logging.getLogger(__name__)

# 檢查 pypandoc 是否可用
try:
    import pypandoc
    HAS_PYPANDOC = True
    try:
        PANDOC_VERSION = pypandoc.get_pandoc_version()
    except OSError:
        HAS_PYPANDOC = False
        PANDOC_VERSION = None
except ImportError:
    HAS_PYPANDOC = False
    PANDOC_VERSION = None


class MarkdownConverter:
    """Markdown 文件轉換器"""
    
    @staticmethod
    def check_pandoc() -> tuple[bool, str]:
        """
        檢查 Pandoc 是否已安裝
        
        Returns:
            (is_available, version_or_error_message)
        """
        if not HAS_PYPANDOC:
            return False, "pypandoc 未安裝或 Pandoc 未找到"
        return True, f"Pandoc {PANDOC_VERSION}"
    
    @staticmethod
    def md_to_pdf(md_path: str, pdf_path: str, callback=None) -> bool:
        """
        Markdown 轉 PDF
        
        使用 MD → DOCX → PDF 流程（透過 docx2pdf）
        
        Args:
            md_path: 輸入的 Markdown 文件路徑
            pdf_path: 輸出的 PDF 文件路徑
            callback: 進度回調函數 callback(progress, status)
            
        Returns:
            成功返回 True，失敗返回 False
        """
        if not HAS_PYPANDOC:
            raise RuntimeError("Pandoc 未安裝，無法進行轉換")
        
        if callback:
            callback(10, "讀取 Markdown 文件...")
        
        if not os.path.exists(md_path):
            raise FileNotFoundError(f"找不到文件：{md_path}")
        
        # 建立臨時 DOCX 檔案
        temp_docx = None
        
        try:
            if callback:
                callback(30, "轉換為 Word...")
            
            # 先轉為 DOCX
            temp_docx = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
            temp_docx.close()
            
            pypandoc.convert_file(
                md_path,
                'docx',
                outputfile=temp_docx.name
            )
            
            if callback:
                callback(60, "轉換為 PDF...")
            
            # 再用 docx2pdf 轉為 PDF
            try:
                from docx2pdf import convert
                convert(temp_docx.name, pdf_path)
            except ImportError:
                raise RuntimeError("docx2pdf 未安裝，請執行: pip install docx2pdf")
            except Exception as e:
                # 如果 docx2pdf 失敗，嘗試使用 LibreOffice
                import subprocess
                import platform
                
                if platform.system() == 'Windows':
                    soffice_paths = [
                        r"C:\Program Files\LibreOffice\program\soffice.exe",
                        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"
                    ]
                    soffice = None
                    for path in soffice_paths:
                        if os.path.exists(path):
                            soffice = path
                            break
                    
                    if soffice:
                        output_dir = os.path.dirname(pdf_path)
                        subprocess.run([
                            soffice, '--headless', '--convert-to', 'pdf',
                            '--outdir', output_dir, temp_docx.name
                        ], check=True)
                        # 重命名輸出檔案
                        generated_pdf = os.path.join(output_dir, os.path.basename(temp_docx.name).replace('.docx', '.pdf'))
                        if os.path.exists(generated_pdf) and generated_pdf != pdf_path:
                            import shutil
                            shutil.move(generated_pdf, pdf_path)
                    else:
                        raise RuntimeError(f"docx2pdf 轉換失敗且 LibreOffice 未找到: {e}")
                else:
                    raise RuntimeError(f"docx2pdf 轉換失敗: {e}")
            
            if callback:
                callback(100, "轉換完成")
            
            return True
            
        except Exception as e:
            logger.error(f"MD to PDF 轉換失敗: {e}")
            raise
            
        finally:
            # 清理臨時檔案
            if temp_docx and os.path.exists(temp_docx.name):
                os.unlink(temp_docx.name)
    
    @staticmethod
    def md_to_docx(md_path: str, docx_path: str, callback=None) -> bool:
        """
        Markdown 轉 Word (DOCX)
        
        使用 pypandoc 進行轉換
        """
        if not HAS_PYPANDOC:
            raise RuntimeError("Pandoc 未安裝，無法進行轉換")
        
        if callback:
            callback(10, "讀取 Markdown 文件...")
        
        if not os.path.exists(md_path):
            raise FileNotFoundError(f"找不到文件：{md_path}")
        
        if callback:
            callback(50, "轉換為 Word...")
        
        try:
            pypandoc.convert_file(
                md_path,
                'docx',
                outputfile=docx_path
            )
            
            if callback:
                callback(100, "轉換完成")
            
            return True
            
        except Exception as e:
            logger.error(f"MD to DOCX 轉換失敗: {e}")
            raise
    
    @staticmethod
    def docx_to_md(docx_path: str, md_path: str, callback=None) -> bool:
        """
        Word (DOCX) 轉 Markdown
        """
        if not HAS_PYPANDOC:
            raise RuntimeError("Pandoc 未安裝，無法進行轉換")
        
        if callback:
            callback(10, "讀取 Word 文件...")
        
        if not os.path.exists(docx_path):
            raise FileNotFoundError(f"找不到文件：{docx_path}")
        
        if callback:
            callback(50, "轉換為 Markdown...")
        
        try:
            pypandoc.convert_file(
                docx_path,
                'markdown',
                outputfile=md_path,
                extra_args=['--wrap=none']  # 不自動換行
            )
            
            if callback:
                callback(100, "轉換完成")
            
            return True
            
        except Exception as e:
            logger.error(f"DOCX to MD 轉換失敗: {e}")
            raise
    
    @staticmethod
    def pdf_to_md(pdf_path: str, md_path: str, callback=None) -> bool:
        """
        PDF 轉 Markdown
        
        注意：PDF 轉換可能會損失格式，效果取決於 PDF 結構
        """
        if not HAS_PYPANDOC:
            raise RuntimeError("Pandoc 未安裝，無法進行轉換")
        
        if callback:
            callback(10, "讀取 PDF 文件...")
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"找不到文件：{pdf_path}")
        
        if callback:
            callback(50, "轉換為 Markdown...")
        
        try:
            pypandoc.convert_file(
                pdf_path,
                'markdown',
                outputfile=md_path,
                extra_args=['--wrap=none']
            )
            
            if callback:
                callback(100, "轉換完成")
            
            return True
            
        except Exception as e:
            logger.error(f"PDF to MD 轉換失敗: {e}")
            raise


def check_dependencies() -> dict:
    """檢查 Markdown 轉換相關依賴"""
    deps = {
        'pypandoc': HAS_PYPANDOC,
        'pandoc_version': PANDOC_VERSION
    }
    return deps


if __name__ == "__main__":
    # 測試
    available, info = MarkdownConverter.check_pandoc()
    print(f"Pandoc 可用: {available}")
    print(f"資訊: {info}")
