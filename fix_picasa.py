
import os

with open("picasa6.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Keep lines up to 3156 (inclusive)
# Line 3156 in the file (1-based) is index 3155.
# Let's verify what line 3153 is.
# 3153:             self.show_error(message)

# We will cut off everything after line 3154 (which is likely newline)
valid_lines = lines[:3154]

new_tail = """

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MediaToolkit")
    app.setApplicationVersion("6.0")
    window = MediaToolkit()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
"""

with open("picasa6.py", "w", encoding="utf-8") as f:
    f.writelines(valid_lines)
    f.write(new_tail)

print("Fixed picasa6.py")
