import sys
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- STYLESHEET ---
STYLESHEET = """
QMainWindow {
    background-color: #f5f5f7;
    color: #333333;
    font-family: "Segoe UI", sans-serif;
}

QMenuBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
}

QMenuBar::item {
    padding: 8px 12px;
    background: transparent;
}

QMenuBar::item:selected {
    background-color: #eeeef0;
    border-radius: 4px;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e0e0e0;
    padding: 5px;
    spacing: 10px;
}

QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px;
}

QToolButton:hover {
    background-color: #eeeef0;
    border: 1px solid #d0d0d0;
}

QDockWidget {
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(float.png);
}

QDockWidget::title {
    text-align: left;
    background: #f0f0f2;
    padding-left: 10px;
    padding-top: 4px;
    padding-bottom: 4px;
    border-radius: 4px;
    font-weight: bold;
    color: #555;
}

QListWidget, QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    padding: 5px;
}

QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #0078d4;
    color: white;
    border-radius: 2px;
}

QHeaderView::section {
    background-color: #f5f5f7;
    padding: 4px;
    border: none;
    border-bottom: 1px solid #d0d0d0;
    font-weight: bold;
    color: #666;
}

QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e0e0e0;
    color: #666;
}
"""
