
import os
import sys
import platform

print(f"Python: {sys.version}")
print(f"Platform: {platform.system()}")

try:
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    print(f"ReportLab version: {reportlab.Version}")
    HAS_REPORTLAB = True
except ImportError as e:
    print(f"ReportLab import failed: {e}")
    HAS_REPORTLAB = False

if HAS_REPORTLAB:
    print("\nChecking Fonts...")
    font_paths = [
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/mingliu.ttc",
        "C:/Windows/Fonts/kaiu.ttf"
    ]
    
    found_font = None
    for path in font_paths:
        exists = os.path.exists(path)
        print(f"Font path: {path} - Exists: {exists}")
        if exists and not found_font:
            try:
                if path.endswith('.ttc'):
                     # TTC files might need explicit index, reportlab usually handles it or needs 'FontName'
                     # Try loading first font in TTC
                     font = TTFont('TestFont', path)
                else:
                     font = TTFont('TestFont', path)
                
                pdfmetrics.registerFont(font)
                print(f"  -> Successfully registered {path}")
                found_font = path
            except Exception as e:
                print(f"  -> Failed to register {path}: {e}")

    if not found_font:
        print("WARNING: No Chinese font found/registered. ReportLab will use Helvetica (no Chinese support).")

    # Simulate TOC creation with Chinese
    try:
        print("\nSimulating TOC generation...")
        c = canvas.Canvas("test_toc.pdf")
        font_name = 'TestFont' if found_font else 'Helvetica'
        c.setFont(font_name, 12)
        c.drawString(100, 100, "測試中文 Test Chinese")
        c.save()
        print("TOC generation successful (test_toc.pdf created)")
    except Exception as e:
        print(f"TOC generation failed: {e}")

else:
    print("Skipping font check because ReportLab is missing.")
