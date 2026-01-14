
import sys
import csv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QDockWidget, QListWidget, QTableWidget, QTableWidgetItem, 
                             QToolBar, QStatusBar, QWidget, QVBoxLayout, QCheckBox, 
                             QListWidgetItem, QFrame, QLabel, QMenu, QToolButton,
                             QFileDialog, QMessageBox, QGraphicsRectItem, QGraphicsTextItem,
                             QGraphicsItem, QGraphicsLineItem, QPushButton, QGraphicsPathItem)
from PyQt6.QtCore import Qt, QSize, QRectF, QPointF, QLineF
from PyQt6.QtGui import (QAction, QIcon, QColor, QPen, QBrush, QPainter, 
                         QPainterPath, QLinearGradient, QGradient, QPixmap, QPolygonF,
                         QPainterPathStroker)
import math
import ezdxf
import traceback
import heapq

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

class CADGraphicsScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_size = 50
        self.grid_visible = True
        self.grid_color_light = QColor(220, 220, 220)
        self.grid_color_dark = QColor(200, 200, 200)
        self.setBackgroundBrush(QBrush(QColor("#fafafa")))
        self.setSceneRect(-2000, -2000, 4000, 4000)

    def set_grid_visible(self, visible):
        self.grid_visible = visible
        self.update()

    def drawBackground(self, painter, rect):
        # Fill background
        painter.fillRect(rect, self.backgroundBrush())

        if not self.grid_visible:
            return

        # Draw Grid
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        
        # Grid lines
        lines_light = []
        lines_dark = []
        
        x = left
        while x < rect.right():
            if x % (self.grid_size * 5) == 0:
                lines_dark.append(QPointF(x, rect.top()))
                lines_dark.append(QPointF(x, rect.bottom()))
            else:
                lines_light.append(QPointF(x, rect.top()))
                lines_light.append(QPointF(x, rect.bottom()))
            x += self.grid_size
            
        y = top
        while y < rect.bottom():
            if y % (self.grid_size * 5) == 0:
                lines_dark.append(QPointF(rect.left(), y))
                lines_dark.append(QPointF(rect.right(), y))
            else:
                lines_light.append(QPointF(rect.left(), y))
                lines_light.append(QPointF(rect.right(), y))
            y += self.grid_size

        painter.setPen(QPen(self.grid_color_light, 1))
        painter.drawLines(lines_light)
        
        painter.setPen(QPen(self.grid_color_dark, 1.5))
        painter.drawLines(lines_dark)

class SwitchboardItem(QGraphicsRectItem):
    def __init__(self, name, rect, parent=None):
        super().__init__(rect, parent)
        self.switchboard_name = name
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setBrush(QBrush(QColor("#e0e0e0")))
        self.setPen(QPen(QColor("black"), 2))
        self.setZValue(50)
        
        # Determine label text (first 3 chars?)
        label_text = name[:3] if name else "??"
        
        # Add Text
        text = QGraphicsTextItem(label_text, self)
        font = text.font()
        font.setPointSize(10)
        font.setBold(True)
        text.setFont(font)
        
        # Center text
        br = text.boundingRect()
        wb = rect.width()
        hb = rect.height()
        text.setPos((wb - br.width())/2, (hb - br.height())/2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            new_pos = value
            target_pos = self.snap_to_closest_segment(new_pos)
            if target_pos:
                return target_pos
        return super().itemChange(change, value)

    def snap_to_closest_segment(self, pos):
        # Find all lines in scene
        scene = self.scene()
        items = scene.items()
        
        candidates = []
        for item in items:
            if isinstance(item, QGraphicsLineItem):
                line = item.line()
                center_offset = self.rect().center()
                target_center = pos + center_offset
                p = self.closest_point_on_line(line, target_center)
                dist = QLineF(target_center, p).length()
                candidates.append((dist, p))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        best_p = candidates[0][1]
        new_top_left = best_p - self.rect().center()
        return new_top_left

    def closest_point_on_line(self, line, point):
        x1, y1 = line.p1().x(), line.p1().y()
        x2, y2 = line.p2().x(), line.p2().y()
        px, py = point.x(), point.y()
        
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return line.p1()

        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        return QPointF(closest_x, closest_y)

class ClickableLineItem(QGraphicsLineItem):
    def shape(self):
        path = super().shape()
        stroker = QPainterPathStroker()
        stroker.setWidth(10) # 10 units wide hit area
        return stroker.createStroke(path)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD Viewer Pro 2025")
        self.resize(1200, 800)
        
        # Apply Style
        self.setStyleSheet(STYLESHEET)
        
        # Setup UI
        self.create_actions()
        self.create_dock_widgets()
        self.create_menubar()
        self.create_toolbar()
        self.create_central_widget()
        self.create_statusbar()
        
        # State for placement
        self.placing_switchboard_name = None
        self.placing_switchboard_item_list_ref = None
        
        # Add Demo Content
        # self.add_demo_content()

    def create_actions(self):
        # Only text based actions since we don't have icon files
        # In a real app we'd use QIcon("path/to.png")
        self.act_open = QAction("Open", self)
        self.act_save = QAction("Save", self)
        self.act_exit = QAction("Exit", self)
        
        self.act_zoom_in = QAction("Zoom In", self)
        self.act_zoom_out = QAction("Zoom Out", self)
        self.act_pan = QAction("Pan", self)
        self.act_pan.setCheckable(True)
        self.act_select = QAction("Select", self)
        self.act_select.setCheckable(True)
        self.act_select.setChecked(True)
        self.act_fit = QAction("Fit All", self)

        self.act_open.triggered.connect(self.open_file)
        self.act_fit.triggered.connect(self.zoom_fit)
        
        self.act_pan.triggered.connect(self.activate_pan)
        self.act_select.triggered.connect(self.activate_select)
        self.act_zoom_in.triggered.connect(self.zoom_in)
        self.act_zoom_out.triggered.connect(self.zoom_out)

        # Assign Custom Icons
        self.act_select.setIcon(self.draw_icon("select"))
        self.act_pan.setIcon(self.draw_icon("pan"))
        self.act_fit.setIcon(self.draw_icon("fit"))
        self.act_zoom_in.setIcon(self.draw_icon("zoom_in"))
        self.act_zoom_out.setIcon(self.draw_icon("zoom_out"))

        self.act_toggle_grid = QAction("Mostra Griglia", self)
        self.act_toggle_grid.setCheckable(True)
        self.act_toggle_grid.setChecked(True)
        self.act_toggle_grid.triggered.connect(self.toggle_grid)
        
        self.act_toggle_nodes = QAction("Mostra Nodi", self)
        self.act_toggle_nodes.setCheckable(True)
        self.act_toggle_nodes.setChecked(False) # Default hidden
        self.act_toggle_nodes.triggered.connect(self.toggle_nodes)

        self.act_import_csv = QAction("Importa CSV Cavi...", self)
        self.act_import_csv.triggered.connect(self.import_csv)

    def create_menubar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self.act_open)
        file_menu.addAction(self.act_import_csv)
        file_menu.addAction(self.act_save)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)
        
        edit_menu = menubar.addMenu("Modifica")
        edit_menu.addAction("Undo")
        edit_menu.addAction("Redo")
        
        view_menu = menubar.addMenu("Visualizza")
        view_menu.addAction(self.dock_tools.toggleViewAction())
        view_menu.addAction(self.dock_props.toggleViewAction())
        view_menu.addAction(self.dock_errors.toggleViewAction())
        view_menu.addAction(self.dock_switchboards.toggleViewAction())
        view_menu.addAction(self.dock_connections.toggleViewAction())
        view_menu.addSeparator()
        view_menu.addSeparator()
        view_menu.addAction(self.act_toggle_grid)
        view_menu.addAction(self.act_toggle_nodes)
        view_menu.addSeparator()
        view_menu.addAction(self.act_zoom_in)
        view_menu.addAction(self.act_zoom_out)
        view_menu.addAction(self.act_fit)
        
        tools_menu = menubar.addMenu("Strumenti")
        tools_menu.addAction("Measure")
        tools_menu.addAction("Properties")
        
        help_menu = menubar.addMenu("Aiuto")
        help_menu.addAction("About")

    def create_toolbar(self):
        # --- Top Toolbar (File + Layers) ---
        self.top_toolbar = QToolBar("Top Toolbar")
        self.top_toolbar.setIconSize(QSize(24, 24))
        self.top_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.top_toolbar)
        
        style = self.style()
        self.act_open.setIcon(style.standardIcon(style.StandardPixmap.SP_DialogOpenButton))
        self.act_save.setIcon(style.standardIcon(style.StandardPixmap.SP_DialogSaveButton))
        
        self.top_toolbar.addAction(self.act_open)
        self.top_toolbar.addAction(self.act_save)
        self.top_toolbar.addSeparator()
        
        # Layer Dropdown
        self.btn_layers = QToolButton()
        self.btn_layers.setText("Layers \u25BC") # \u25BC is a down arrow
        self.btn_layers.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.btn_layers.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_layers.setMenu(self.create_layer_menu())
        self.top_toolbar.addWidget(self.btn_layers)

    def draw_icon(self, name):
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor("#444"))
        pen.setWidth(2)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        if name == "select":
            # Cursor Arrow
            poly = QPolygonF([QPointF(7, 5), QPointF(7, 19), QPointF(11, 15), 
                              QPointF(14, 21), QPointF(16, 20), QPointF(13, 14), QPointF(18, 14)])
            painter.drawPolygon(poly)
            
        elif name == "pan":
            # 4-way arrow
            painter.drawLine(12, 4, 12, 20) # Vertical
            painter.drawLine(4, 12, 20, 12) # Horizontal
            # Arrow heads
            painter.drawLine(12, 4, 9, 7)
            painter.drawLine(12, 4, 15, 7)
            painter.drawLine(12, 20, 9, 17)
            painter.drawLine(12, 20, 15, 17)
            painter.drawLine(4, 12, 7, 9)
            painter.drawLine(4, 12, 7, 15)
            painter.drawLine(20, 12, 17, 9)
            painter.drawLine(20, 12, 17, 15)
            
        elif name == "fit":
            # [ ] corners
            l = 5; r = 19; t = 5; b = 19
            s = 4 # size of corner
            # Top-Left
            painter.drawPolyline(QPolygonF([QPointF(l, t+s), QPointF(l, t), QPointF(l+s, t)]))
            # Top-Right
            painter.drawPolyline(QPolygonF([QPointF(r, t+s), QPointF(r, t), QPointF(r-s, t)]))
            # Bottom-Right
            painter.drawPolyline(QPolygonF([QPointF(r, b-s), QPointF(r, b), QPointF(r-s, b)]))
            # Bottom-Left
            painter.drawPolyline(QPolygonF([QPointF(l, b-s), QPointF(l, b), QPointF(l+s, b)]))
            
            # Center dot
            painter.setBrush(QBrush(QColor("#444")))
            painter.drawEllipse(10, 10, 4, 4)
            
        elif name == "zoom_in":
            # Magnifier +
            painter.drawEllipse(6, 6, 10, 10)
            painter.drawLine(14, 14, 19, 19)
            painter.drawLine(11, 8, 11, 14)
            painter.drawLine(8, 11, 14, 11)
            
        elif name == "zoom_out":
            # Magnifier -
            painter.drawEllipse(6, 6, 10, 10)
            painter.drawLine(14, 14, 19, 19)
            painter.drawLine(8, 11, 14, 11)

        painter.end()
        return QIcon(pixmap)

    def create_layer_menu(self):
        menu = QMenu(self)
        layers = [("Layer 0", "#000000"), ("Walls", "#FF0000"), ("Doors", "#00FF00"), ("Electrics", "#0000FF")]
        
        for name, color_code in layers:
            action = QAction(name, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.setIcon(self.create_color_pixmap(color_code))
            menu.addAction(action)
            
        return menu

    def create_central_widget(self):
        self.scene = CADGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setMouseTracking(True) # For coordinates
        self.view.viewport().installEventFilter(self) # Capture mouse move
        
        self.setCentralWidget(self.view)
        
        # Connect selection change
        self.scene.selectionChanged.connect(self.on_selection_changed)

    def eventFilter(self, source, event):
        if source == self.view.viewport():
            if event.type() == event.Type.MouseMove:
                pos = self.view.mapToScene(event.pos())
                self.lbl_coords.setText(f"X: {pos.x():.2f}  Y: {pos.y():.2f}")
            
            elif event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if self.placing_switchboard_name:
                    pos = self.view.mapToScene(event.pos())
                    self.finalize_placement(pos)
                    return True # Consume event

        return super().eventFilter(source, event)

    def finalize_placement(self, pos):
        name = self.placing_switchboard_name
        
        # Remove existing item with same name if any
        for item in self.scene.items():
            if isinstance(item, SwitchboardItem) and item.switchboard_name == name:
                self.scene.removeItem(item)
                break # Assuming only one exists

        wb = 80
        hb = 50
        rect_item = SwitchboardItem(name, QRectF(0, 0, wb, hb))
        self.scene.addItem(rect_item)
        
        # Center the item on the click position
        # top-left = pos - (width/2, height/2)
        top_left = pos - QPointF(wb/2, hb/2)
        
        # This setPos will trigger checking for snap in SwitchboardItem.itemChange 
        # because we set 'ItemSendsGeometryChanges'. 
        # Wait, itemChange is called on setPos.
        rect_item.setPos(top_left)
        
        text = self.scene.addText(name)
        text.setDefaultTextColor(QColor("black"))
        br = text.boundingRect()
        text.setPos((wb - br.width())/2, (hb - br.height())/2)
        text.setParentItem(rect_item)
        
        self.scene.clearSelection()
        rect_item.setSelected(True)
        
        # Update styling of list item
        if self.placing_switchboard_item_list_ref:
            item = self.placing_switchboard_item_list_ref
            item.setForeground(QBrush(QColor("gray")))
            font = item.font()
            font.setStrikeOut(True)
            item.setFont(font)
            
        self.lbl_status.setText(f"Posizionato: {name}")
        
        # Reset mode
        self.placing_switchboard_name = None
        self.placing_switchboard_item_list_ref = None
        self.view.setCursor(Qt.CursorShape.ArrowCursor)


    def create_dock_widgets(self):
        # LEFT: Tools (formerly Toolbar)
        self.dock_tools = QDockWidget("Strumenti", self)
        self.dock_tools.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        tools_widget = QWidget()
        tools_layout = QVBoxLayout()
        tools_layout.setContentsMargins(5, 5, 5, 5)
        tools_layout.setSpacing(10)
        tools_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Helper to add button
        def add_tool_btn(action):
            btn = QToolButton()
            btn.setDefaultAction(action)
            btn.setIconSize(QSize(32, 32))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btns_size = QSize(40, 40)
            btn.setFixedSize(btns_size)
            tools_layout.addWidget(btn)
            
        add_tool_btn(self.act_pan)
        add_tool_btn(self.act_select)
        add_tool_btn(self.act_fit)
        
        # Spacer or separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tools_layout.addWidget(line)
        
        add_tool_btn(self.act_zoom_in)
        add_tool_btn(self.act_zoom_out)
        
        tools_widget.setLayout(tools_layout)
        self.dock_tools.setWidget(tools_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_tools)

        # RIGHT: Properties
        self.dock_props = QDockWidget("Proprietà", self)
        self.dock_props.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.table_props = QTableWidget()
        self.table_props.setColumnCount(2)
        self.table_props.setHorizontalHeaderLabels(["Proprietà", "Valore"])
        self.table_props.verticalHeader().setVisible(False)
        self.table_props.setShowGrid(False)
        self.table_props.setAlternatingRowColors(True)
        header = self.table_props.horizontalHeader()
        header.setStretchLastSection(True)
        
        self.dock_props.setWidget(self.table_props)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_props)

        # BOTTOM: Errors
        self.dock_errors = QDockWidget("Errori", self)
        self.dock_errors.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        self.list_errors = QListWidget()
        self.dock_errors.setWidget(self.list_errors)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_errors)

        # SWITCHBOARDS DOCK
        self.dock_switchboards = QDockWidget("Lista Quadri", self)
        self.dock_switchboards.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        self.list_switchboards = QListWidget()
        self.list_switchboards.setToolTip("Doppio click per posizionare il quadro nella scena")
        self.list_switchboards.itemDoubleClicked.connect(self.place_switchboard_from_list)
        
        self.dock_switchboards.setWidget(self.list_switchboards)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_switchboards)

        # CONNECTIONS DOCK
        self.dock_connections = QDockWidget("Lista Connessioni", self)
        self.dock_connections.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        conn_widget = QWidget()
        conn_layout = QVBoxLayout()
        conn_layout.setContentsMargins(0, 0, 0, 0)
        
        # Filter Input
        from PyQt6.QtWidgets import QLineEdit
        self.txt_filter_conn = QLineEdit()
        self.txt_filter_conn.setPlaceholderText("Filtra connessioni (Da/A)...")
        self.txt_filter_conn.textChanged.connect(self.filter_connections)
        conn_layout.addWidget(self.txt_filter_conn)
        
        self.table_connections = QTableWidget()
        # Columns will be set dynamically based on CSV
        self.table_connections.verticalHeader().setVisible(False)
        self.table_connections.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_connections.setAlternatingRowColors(True)
        self.table_connections.setSortingEnabled(True) # Enable sorting
        self.table_connections.itemSelectionChanged.connect(self.on_connection_selected)
        # self.table_connections.horizontalHeader().setStretchLastSection(True) # Maybe better to resize to contents
        conn_layout.addWidget(self.table_connections)
        
        self.btn_calc_routes = QPushButton("Calculation")
        self.btn_calc_routes.clicked.connect(self.calculate_routes)
        conn_layout.addWidget(self.btn_calc_routes)
        
        conn_widget.setLayout(conn_layout)
        self.dock_connections.setWidget(conn_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_connections)
        self.tabifyDockWidget(self.dock_props, self.dock_connections) # Tabify with properties by default

    def log_error(self, message):
        item = QListWidgetItem(message)
        item.setForeground(QBrush(QColor("red")))
        self.list_errors.addItem(item)
        # Ensure the dock is visible if an error occurs? Optional, maybe annoying.
        # self.dock_errors.setVisible(True)

    def create_color_pixmap(self, color_str):
        from PyQt6.QtGui import QPixmap
        pix = QPixmap(16, 16)
        pix.fill(QColor(color_str))
        return QIcon(pix)

    def create_statusbar(self):
        status = QStatusBar()
        self.setStatusBar(status)
        
        self.lbl_coords = QLabel("X: 0.00 Y: 0.00")
        self.lbl_coords.setFixedWidth(200)
        self.lbl_zoom = QLabel("Zoom: 100%")
        self.lbl_status = QLabel("Pronto")
        
        status.addPermanentWidget(self.lbl_zoom)
        status.addPermanentWidget(self.lbl_coords)
        status.addWidget(self.lbl_status)

    def add_demo_content(self):
        # Lines
        pen_wall = QPen(QColor("#333"), 3)
        line1 = self.scene.addLine(0, 0, 500, 0, pen_wall)
        line1.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        line1.setToolTip("Wall Segment")
        
        line2 = self.scene.addLine(500, 0, 500, 300, pen_wall)
        line2.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        line3 = self.scene.addLine(500, 300, 0, 300, pen_wall)
        line3.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        line4 = self.scene.addLine(0, 300, 0, 0, pen_wall)
        line4.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        # Circle
        pen_door = QPen(QColor("blue"), 2)
        circle = self.scene.addEllipse(200, 100, 100, 100, pen_door, QBrush(QColor(0, 0, 255, 50)))
        circle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        circle.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        
        # Text
        text = self.scene.addText("Sala Principale")
        text.setScale(2)
        text.setPos(150, 150)
        text.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        text.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def zoom_fit(self):
        if not self.scene.items():
            return
        rect = self.scene.itemsBoundingRect()
        if rect.isNull():
            return
        # Add some margin
        rect.adjust(-50, -50, 50, 50)
        self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_in(self):
        self.view.scale(1.2, 1.2)
        self.update_zoom_label()

    def zoom_out(self):
        self.view.scale(1 / 1.2, 1 / 1.2)
        self.update_zoom_label()
        
    def update_zoom_label(self):
        # Approximate zoom level based on transform
        zoom = self.view.transform().m11()
        self.lbl_zoom.setText(f"Zoom: {int(zoom * 100)}%")

    def activate_pan(self):
        self.act_pan.setChecked(True)
        self.act_select.setChecked(False)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.lbl_status.setText("Mode: Pan")

    def activate_select(self):
        self.act_select.setChecked(True)
        self.act_pan.setChecked(False)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.lbl_status.setText("Mode: Select")

    def toggle_grid(self, checked):
        self.scene.set_grid_visible(checked)
        self.lbl_status.setText(f"Griglia {'visibile' if checked else 'nascosta'}")

    def toggle_nodes(self, checked):
        if hasattr(self, 'nodes_group') and self.nodes_group:
            self.nodes_group.setVisible(checked)
        self.lbl_status.setText(f"Nodi {'visibili' if checked else 'nascosti'}")

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importa CSV Cavi", "", "CSV Files (*.csv);;All Files (*.*)")
        if not path: return
        
        try:
            unique_sw = set()
            self.all_connections = [] # Store all connection data
            
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Check for headers FROM and TO
                if not reader.fieldnames or 'FROM' not in reader.fieldnames or 'TO' not in reader.fieldnames:
                    QMessageBox.warning(self, "Formato CSV", "Il file CSV deve contenere le colonne 'FROM' e 'TO'.")
                    return
                    
                for row in reader:
                    self.all_connections.append(row)
                    if row.get('FROM'): unique_sw.add(row['FROM'].strip())
                    if row.get('TO'): unique_sw.add(row['TO'].strip())
            
            self.list_switchboards.clear()
            for name in sorted(unique_sw):
                item = QListWidgetItem(name)
                self.list_switchboards.addItem(item)
            
            self.populate_connections_list()
            
            self.dock_switchboards.setVisible(True)
            self.dock_switchboards.raise_()
            self.dock_connections.setVisible(True)
            self.dock_connections.raise_()
            
            QMessageBox.information(self, "Importazione", f"Trovati {len(unique_sw)} quadri unici e {len(self.all_connections)} connessioni.\nConsulta i pannelli laterali.")
            
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Errore lettura CSV: {e}")
            traceback.print_exc()

    def populate_connections_list(self):
        self.table_connections.setSortingEnabled(False) # Disable sorting while populating
        self.table_connections.setRowCount(0)
        self.table_connections.setColumnCount(0)
        
        if not hasattr(self, 'all_connections') or not self.all_connections:
            return

        # Determine columns from first row + ensure FROM/TO are first if possible?
        # self.all_connections is a list of dicts
        headers = list(self.all_connections[0].keys())
        
        # Optional: Prioritize FROM, TO, Cable Type
        priority = ['FROM', 'TO', 'Cable Type']
        sorted_headers = []
        for p in priority:
            if p in headers:
                sorted_headers.append(p)
                headers.remove(p)
        sorted_headers.extend(headers) # Append remaining
        
        self.table_connections.setColumnCount(len(sorted_headers))
        self.table_connections.setHorizontalHeaderLabels(sorted_headers)

        self.table_connections.setRowCount(len(self.all_connections))
        
        for row, conn in enumerate(self.all_connections):
            for col, key in enumerate(sorted_headers):
                val = conn.get(key, '')
                item = QTableWidgetItem(str(val))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row) # Store index
                self.table_connections.setItem(row, col, item)

        self.table_connections.setSortingEnabled(True) # Re-enable sorting

    def filter_connections(self, text):
        text = text.lower()
        rows = self.table_connections.rowCount()
        cols = self.table_connections.columnCount()
        
        for i in range(rows):
            visible = False
            # Check all columns
            for c in range(cols):
                item = self.table_connections.item(i, c)
                if item and text in item.text().lower():
                    visible = True
                    break
            self.table_connections.setRowHidden(i, not visible)

    def place_switchboard_from_list(self, item):
        name = item.text()
        
        # Enter Placement Mode
        self.placing_switchboard_name = name
        self.placing_switchboard_item_list_ref = item
        
        # Change cursor to indicate placement
        self.view.setCursor(Qt.CursorShape.CrossCursor)
        self.lbl_status.setText(f"MODALITÀ POSIZIONAMENTO: Clicca sul disegno per posizionare '{name}'. (Esc per annullare)")
        self.view.setFocus()


    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Apri File CAD", 
            "", 
            "CAD Files (*.dxf *.dwg);;DXF Files (*.dxf);;DWG Files (*.dwg);;All Files (*.*)"
        )
        
        if not path:
            return
            
        if path.lower().endswith(".dwg"):
            QMessageBox.warning(self, "Formato DWG", 
                                "Il supporto diretto per i file DWG è limitato.\n"
                                "Per favore, converti il file in DXF per visualizzarlo correttamente.")
            return

        try:
            self.load_dxf(path)
            self.lbl_status.setText(f"Caricato: {path}")
            self.setWindowTitle(f"CAD Viewer Pro 2025 - {path}")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il file:\n{str(e)}")
            traceback.print_exc()

    def load_dxf(self, filename):
        try:
            doc = ezdxf.readfile(filename)
            msp = doc.modelspace()
            
            self.scene.clear()
            self.nodes_group = self.scene.createItemGroup([])
            self.nodes_group.setZValue(100)
            self.nodes_group.setVisible(self.act_toggle_nodes.isChecked())
            
            pen_default = QPen(QColor("#333"), 1.5)
            pen_default.setCosmetic(True) # Keep width constant on zoom
            
            count = 0
            for entity in msp:
                item = None
                try:
                    if entity.dxftype() == 'LINE':
                        start = entity.dxf.start
                        end = entity.dxf.end
                        item = ClickableLineItem(start.x, -start.y, end.x, -end.y)
                        item.setPen(pen_default)
                        self.scene.addItem(item)
                        
                    elif entity.dxftype() == 'CIRCLE':
                        center = entity.dxf.center
                        radius = entity.dxf.radius
                        item = self.scene.addEllipse(
                            center.x - radius, -(center.y + radius), 
                            radius * 2, radius * 2, 
                            pen_default
                        )
                    
                    elif entity.dxftype() == 'ARC':
                        center = entity.dxf.center
                        radius = entity.dxf.radius
                        start_angle = entity.dxf.start_angle
                        end_angle = entity.dxf.end_angle
                        
                        path = QPainterPath()
                        # Angles in Qt are degrees, counter-clockwise.
                        # ARC angles are also CCW.
                        # Need to calculate span
                        span_angle = end_angle - start_angle
                        if span_angle < 0:
                            span_angle += 360
                            
                        # Correct rectangle for arc
                        rect = QRectF(center.x - radius, -(center.y + radius), radius * 2, radius * 2)
                        
                        # Note: startAngle and spanAngle in arcMoveTo/arcTo are in degrees
                        # But we need to handle the Y-flip. 
                        # If we map (x, y) to (x, -y), CCW becomes CW ?
                        # Let's keep it simple: draw raw geometry, user can pan/zoom.
                        # Adjusting angles for Y-flip is tricky. 
                        # Let's just draw as is with -y coords. 
                        # Using arcTo with negative height? No.
                        # Let's just use positive coords for now and see or invert Y properly.
                        # Simple approach: Inverted Y axis scene.
                        path.arcMoveTo(rect, start_angle) 
                        path.arcTo(rect, start_angle, span_angle)
                        
                        item = self.scene.addPath(path, pen_default)
                        
                    elif entity.dxftype() == 'LWPOLYLINE':
                        points = entity.get_points(format='xy')
                        if points:
                            path = QPainterPath()
                            path.moveTo(points[0][0], -points[0][1])
                            for p in points[1:]:
                                path.lineTo(p[0], -p[1])
                            if entity.closed:
                                path.closeSubpath()
                            item = self.scene.addPath(path, pen_default)
                            
                            # Nodes for Polyline
                            for p in points:
                                self.add_node(p[0], -p[1])
                            
                    elif entity.dxftype() in ('TEXT', 'MTEXT'):
                        insert = entity.dxf.insert
                        text_item = self.scene.addText(entity.dxf.text)
                        # Text scaling is complex, just placing it
                        text_item.setPos(insert.x, -insert.y)
                        text_item.setScale(entity.dxf.height / 10 if entity.dxf.height else 1)
                        # text_item.setRotation(entity.dxf.rotation) # Rotation might need specific origin
                        item = text_item

                    if item:
                         # Nodes for basic entities
                        if entity.dxftype() == 'LINE':
                             self.add_node(entity.dxf.start.x, -entity.dxf.start.y)
                             self.add_node(entity.dxf.end.x, -entity.dxf.end.y)
                        elif entity.dxftype() == 'CIRCLE' or entity.dxftype() == 'ARC':
                             self.add_node(entity.dxf.center.x, -entity.dxf.center.y)

                        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
                        # Try to get color
                        if entity.dxf.color != 256 and entity.dxf.color != 0: # 256 is ByLayer
                            # Basic ACI color map could be implemented, but ignoring for now
                            pass
                        count += 1
                        
                        count += 1
                        
                except Exception as ex:
                    self.log_error(f"Error importing entity {entity.dxftype()}: {ex}")

            self.zoom_fit()
            if self.list_errors.count() > 0:
                self.dock_errors.setVisible(True)
                QMessageBox.warning(self, "Importazione con Errori", 
                                  f"Importati {count} oggetti.\nCi sono stati {self.list_errors.count()} errori. Controlla il pannello Errori.")
            else:
                QMessageBox.information(self, "Importazione", f"Importati {count} oggetti.")

        except Exception as e:
            raise e

    def add_node(self, x, y):
        # Create a yellow circle representing a node
        radius = 2.0 # In scene units
        node = self.scene.addEllipse(
            x - radius, y - radius, 
            radius * 2, radius * 2,
            QPen(QColor("orange"), 1),
            QBrush(QColor("yellow"))
        )
        node.setZValue(100) # Ensure it's on top
        # Make the node invariant to zoom? For now let's scale with scene.
        # But we need to add it to the group
        if hasattr(self, 'nodes_group') and self.nodes_group:
            self.nodes_group.addToGroup(node)

    def on_selection_changed(self):
        try:
            items = self.scene.selectedItems()
        except RuntimeError:
            return  # Scene might be deleted during exit

        self.table_props.setRowCount(0)
        
        if not items:
            self.lbl_status.setText("Nessun oggetto selezionato")
            return
            
        if len(items) > 1:
            self.lbl_status.setText(f"{len(items)} oggetti selezionati")
            self.table_props.setRowCount(1)
            self.table_props.setItem(0, 0, QTableWidgetItem("Conteggio"))
            self.table_props.setItem(0, 1, QTableWidgetItem(str(len(items))))
            # Debug: print what items are selected
            print(f"DEBUG: Selected items: {[type(i).__name__ for i in items]}")
            return

        item = items[0] # Show first item props if only one is selected
        self.lbl_status.setText(f"Oggetto selezionato: {type(item).__name__}")
        
        props = {
            "Tipo": type(item).__name__.replace("QGraphics", "").replace("Item", ""),
            "X": f"{item.x():.2f}",
            "Y": f"{item.y():.2f}",
            "Visibile": str(item.isVisible()),
            "Opacity": f"{item.opacity()}"
        }
        
        if hasattr(item, "rect"): # Rect based
            r = item.rect()
            props["Width"] = f"{r.width():.2f}"
            props["Height"] = f"{r.height():.2f}"
        
        if hasattr(item, "line"): # Line based
            l = item.line()
            props["Length"] = f"{l.length():.2f}"
            props["Angle"] = f"{l.angle():.2f}"
            
            # Check for cable usage in this segment
            # We need p1, p2 normalized
            if hasattr(self, 'segment_usage'):
                p1 = self.get_node_key(l.x1(), l.y1())
                p2 = self.get_node_key(l.x2(), l.y2())
                key = tuple(sorted((p1, p2)))
                print(f"DEBUG: Checking segment {key}")
                if hasattr(self, 'segment_usage'):
                     print(f"DEBUG: Usage Map Keys Sample: {list(self.segment_usage.keys())[:3]}")
                cables = self.segment_usage.get(key, [])
                if cables:
                    props["---"] = "---"
                    props["Cavi"] = f"{len(cables)}"
                    for i, c in enumerate(cables):
                        # Display compact info: "From->To"
                        label = f"{c.get('FROM', '?')}->{c.get('TO', '?')}"
                        # Truncate if too long?
                        props[f"Cavo {i+1}"] = label
                else:
                    print(f"DEBUG: No cables found for key {key}. Usage map has {len(self.segment_usage)} entries.")

        self.table_props.setRowCount(len(props))
        for i, (k, v) in enumerate(props.items()):
            self.table_props.setItem(i, 0, QTableWidgetItem(k))
            self.table_props.setItem(i, 1, QTableWidgetItem(v))

    def get_node_key(self, x, y):
        return (round(x, 1), round(y, 1))

    def calculate_routes(self):
        graph = self.build_routing_graph()
        if not graph:
            QMessageBox.warning(self, "Routing", "Nessun segmento trovato per il routing (Layer 'Lines' vuoto?)")
            return

        # Locate Switchboards
        sw_positions = {}
        for item in self.scene.items():
            if isinstance(item, SwitchboardItem):
                # Center of the switchboard in scene coords
                pos = item.pos() + item.rect().center()
                sw_positions[item.switchboard_name] = (pos.x(), pos.y())
        
        if not hasattr(self, 'all_connections'):
            QMessageBox.warning(self, "Routing", "Nessuna lista connessioni caricata.")
            return

        # Clear old routes
        if hasattr(self, 'route_items'):
            for i in self.route_items:
                self.scene.removeItem(i)
        self.route_items = []
        
        # Reset segment usage map
        # Key: tuple(sorted((p1, p2))), Value: list of connection dicts
        self.segment_usage = {}

        pen_route = QPen(QColor(0, 200, 0, 180), 4) # Semi-transparent green
        pen_route.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen_route.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        count = 0
        missing = []
        
        for conn in self.all_connections:
            start_name = conn.get('FROM')
            end_name = conn.get('TO')
            
            if start_name not in sw_positions:
                if start_name not in missing: missing.append(start_name)
                continue
            if end_name not in sw_positions:
                if end_name not in missing: missing.append(end_name)
                continue
                
            start_pos = sw_positions[start_name]
            end_pos = sw_positions[end_name]
            
            # Snap to nearest graph nodes
            start_node = self.find_nearest_node(graph, start_pos)
            end_node = self.find_nearest_node(graph, end_pos)
            
            if not start_node or not end_node:
                continue
                
            path_nodes = self.astar(graph, start_node, end_node)
            if path_nodes:
                # Store the graphics item in the connection dict for retrieval
                item = self.draw_route(path_nodes, pen_route)
                conn['_route_item'] = item
                count += 1
                
                # Populate segment usage
                for i in range(len(path_nodes) - 1):
                    u = path_nodes[i]
                    v = path_nodes[i+1]
                    # path nodes are already tuples (x, y) - rounded by graph build? 
                    # graph keys are from build_routing_graph which uses rounded.
                    # Yes, they should match.
                    key = tuple(sorted((u, v)))
                    if key not in self.segment_usage:
                        self.segment_usage[key] = []
                    self.segment_usage[key].append(conn)
            else:
                self.log_error(f"Path not found: {start_name} -> {end_name}")
                if '_route_item' in conn:
                     # Remove old invalid route if exists
                     if conn['_route_item'] in self.scene.items():
                         self.scene.removeItem(conn['_route_item'])
                     del conn['_route_item']
                
        if missing:
            msg = f"Calcolati {count} percorsi.\nMissed {len(missing)} quadri: {', '.join(missing[:5])}..."
        else:
            msg = f"Calcolo completato. {count} percorsi creati."
            
        QMessageBox.information(self, "Routing", msg)
        self.lbl_status.setText(msg)

    def on_connection_selected(self):
        # Reset all routes to default style
        default_pen = QPen(QColor(0, 200, 0, 180), 4)
        default_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        default_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        highlight_pen = QPen(QColor(255, 0, 0, 255), 6)
        highlight_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        highlight_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        # Reset all first
        if hasattr(self, 'all_connections'):
            for conn in self.all_connections:
                if '_route_item' in conn:
                    item = conn['_route_item']
                    if item.scene(): # Only if still in scene
                        item.setPen(default_pen)
                        item.setZValue(10)
        
        # Highlight selected
        selected_rows = self.table_connections.selectionModel().selectedRows()
        if not selected_rows:
            return

        for index in selected_rows:
            # Map proxy index to source? No, getting item from column 0
            # row() gives visual row.
            row = index.row()
            item_widget = self.table_connections.item(row, 0)
            if item_widget:
                conn_idx = item_widget.data(Qt.ItemDataRole.UserRole)
                if conn_idx is not None and 0 <= conn_idx < len(self.all_connections):
                    conn = self.all_connections[conn_idx]
                    if '_route_item' in conn:
                        item = conn['_route_item']
                        if item.scene():
                            item.setPen(highlight_pen)
                            item.setZValue(20) # Bring to front

    def build_routing_graph(self):
        graph = {}
        
        for item in self.scene.items():
            if isinstance(item, QGraphicsLineItem):
                # We assume walls and such are lines. 
                # If we want to restrict to specific layers/colors, check item attributes.
                l = item.line()
                p1 = self.get_node_key(l.x1(), l.y1())
                p2 = self.get_node_key(l.x2(), l.y2())
                length = l.length()
                
                if p1 not in graph: graph[p1] = []
                if p2 not in graph: graph[p2] = []
                
                # Check for dupes?
                graph[p1].append((p2, length))
                graph[p2].append((p1, length))
                
        return graph

    def find_nearest_node(self, graph, pos):
        if not graph: return None
        min_dist = float('inf')
        best = None
        px, py = pos
        for nx, ny in graph.keys():
            dist = math.hypot(nx - px, ny - py)
            if dist < min_dist:
                min_dist = dist
                best = (nx, ny)
        return best

    def astar(self, graph, start, end):
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {node: float('inf') for node in graph}
        g_score[start] = 0
        f_score = {node: float('inf') for node in graph}
        
        # Heuristic: Euclidean distance
        def h(n):
            return math.hypot(n[0] - end[0], n[1] - end[1])
            
        f_score[start] = h(start)
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            
            if current == end:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1] # Reverse
                
            for neighbor, weight in graph.get(current, []):
                tentative_g = g_score[current] + weight
                if tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + h(neighbor)
                    if (f_score[neighbor], neighbor) not in open_set:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
                        
        return None

    def draw_route(self, path_nodes, pen):
        if len(path_nodes) < 2: return None
        
        path = QPainterPath()
        path.moveTo(path_nodes[0][0], path_nodes[0][1])
        for p in path_nodes[1:]:
            path.lineTo(p[0], p[1])
            
        item = QGraphicsPathItem(path)
        item.setPen(pen)
        item.setZValue(10) # Below switchboards (50), above lines?
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton) # Let clicks pass through
        self.scene.addItem(item)
        self.route_items.append(item)
        return item

from PyQt6.QtWidgets import QGraphicsItem, QHBoxLayout

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Global nicer font
    font = app.font()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
