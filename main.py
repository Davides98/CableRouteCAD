import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    
    # Global nicer font
    from PyQt6.QtGui import QFont
    app.setFont(QFont("Segoe UI", 10))
    
    # Global Exception Hook to catch crashes and print traceback
    def exception_hook(exctype, value, tb):
        import traceback
        import datetime
        msg = "".join(traceback.format_exception(exctype, value, tb))
        print(msg)
        with open("crash_log.txt", "a") as f:
            f.write(f"\n--- CRASH {datetime.datetime.now()} ---\n{msg}\n")
        sys.exit(1)
    
    sys.excepthook = exception_hook

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        msg = traceback.format_exc()
        print(f"CRASH: {e}")
        with open("crash_log.txt", "a") as f:
            f.write(f"\n--- MAIN CRASH ---\n{msg}\n")
