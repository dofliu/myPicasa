
import sys
import os
import inspect

# Add parent directory to path to import picasa6
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from picasa6 import MediaToolkit
    print("Successfully imported MediaToolkit")
except ImportError as e:
    print(f"Failed to import MediaToolkit: {e}")
    sys.exit(1)

def verify_methods():
    # Check _browse_pdf
    if not hasattr(MediaToolkit, '_browse_pdf'):
        print("FAIL: MediaToolkit does not have _browse_pdf method")
        return False
    
    sig_pdf = inspect.signature(MediaToolkit._browse_pdf)
    print(f"_browse_pdf signature: {sig_pdf}")
    # Expect (self) -> (self) in signature usually shows as () if unbound or (self) if verifying class method
    # For unbound method on class, strictly it is (self). 
    
    # Check _browse_pdf_generic
    if not hasattr(MediaToolkit, '_browse_pdf_generic'):
        print("FAIL: MediaToolkit does not have _browse_pdf_generic method")
        return False

    sig_generic = inspect.signature(MediaToolkit._browse_pdf_generic)
    print(f"_browse_pdf_generic signature: {sig_generic}")

    # Verify parameter counts
    # _browse_pdf should have 1 param (self)
    if len(sig_pdf.parameters) != 1:
        print(f"FAIL: _browse_pdf should have 1 parameter (self), found {len(sig_pdf.parameters)}")
        return False
    
    # _browse_pdf_generic should have 3 params (self, input_widget, key_prefix)
    if len(sig_generic.parameters) != 3:
        print(f"FAIL: _browse_pdf_generic should have 3 parameters, found {len(sig_generic.parameters)}")
        return False
        
    print("SUCCESS: Method signatures are correct.")
    return True

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    # app = QApplication(sys.argv) # Needed if we instantiate, but for inspection we might not need it.
    # However, some classes do heavy stuff on import.
    
    if verify_methods():
        sys.exit(0)
    else:
        sys.exit(1)
