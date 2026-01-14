import sys
import csv
import math
import traceback
import ezdxf
import zipfile
import json
import io
import os
import tempfile
import ast
from PyQt6.QtWidgets import (
    QMainWindow, QGraphicsView, QGraphicsScene, QDockWidget, QListWidget, 
    QTableWidget, QTableWidgetItem, QToolBar, QStatusBar, QWidget, QVBoxLayout, 
    QHBoxLayout, QCheckBox, QListWidgetItem, QFrame, QLabel, QMenu, QToolButton, 
    QFileDialog, QMessageBox, QGraphicsPathItem, QGraphicsItem, QPushButton, 
    QGraphicsRectItem, QGraphicsLineItem, QComboBox, QDialog, QDialogButtonBox, 
    QTextEdit, QFormLayout, QGraphicsTextItem, QStyle, QHeaderView, QLineEdit, 
    QWidgetAction, QGroupBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize, QRectF, QPointF, QLineF, pyqtSignal
from PyQt6.QtGui import (QAction, QIcon, QColor, QPen, QBrush, QPainter, 
                         QPainterPath, QLinearGradient, QGradient, QPixmap, QPolygonF, QFont)

from src.config import STYLESHEET, resource_path
from src.graphics.scene import CADGraphicsScene
from src.graphics.items import SwitchboardItem, ClickableLineItem, AnalysisPointItem
import src.core.routing as routing
from src.core.trays.models import TrayCatalog, TrayInstance
from src.ui.widgets.table_widget import ReorderableTableWidget
from src.ui.dialogs.new_project_dialog import NewProjectDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CableRouteCAD")
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
        
        # Routing state
        self.route_items = []
        self.segment_usage = {}
        self.all_connections = []
        self.segment_trays = {} # key -> list of TrayInstance (New Multi-Tray Structure)
        self.segment_details = {} 
        self.segment_labels = {} # key -> QGraphicsTextItem
        self.segment_label_visibility = {} # key -> bool (individual visibility preference)
        self.segment_label_config = {} # key -> set of property names to show in label
        self.selected_segment_key = None
        self.mixed_service_definitions = {} # key -> list of strings (included services)
        self.heatmap_group = None

    def create_actions(self):
        self.act_new = QAction("Nuovo Progetto...", self)
        self.act_new.setShortcut("Ctrl+N")
        self.act_new.triggered.connect(self.new_project)
        
        self.act_open = QAction("Open", self)
        self.act_save = QAction("Save", self)
        self.act_exit = QAction("Exit", self)
        
        self.act_open.setShortcut("Ctrl+O")
        self.act_save.setShortcut("Ctrl+S")
        self.act_exit.setShortcut("Ctrl+Q")
        
        self.act_zoom_in = QAction("Zoom In", self)
        self.act_zoom_in.setShortcut("+")
        self.act_zoom_out = QAction("Zoom Out", self)
        self.act_zoom_out.setShortcut("-")
        
        self.act_pan = QAction("Pan", self)
        self.act_pan.setShortcut("H")
        self.act_pan.setCheckable(True)
        
        self.act_select = QAction("Select", self)
        self.act_select.setShortcut("S")
        self.act_select.setCheckable(True)
        self.act_select.setChecked(True)
        
        self.act_fit = QAction("Fit All", self)
        self.act_fit.setShortcut("F")

        self.act_open.triggered.connect(self.open_project)
        self.act_save.triggered.connect(self.save_project)
        self.act_fit.triggered.connect(self.zoom_fit)
        
        self.act_pan.triggered.connect(self.activate_pan)
        self.act_select.triggered.connect(self.activate_select)
        self.act_zoom_in.triggered.connect(self.zoom_in)
        self.act_zoom_out.triggered.connect(self.zoom_out)

        # Assign Icons
        self.act_open.setIcon(self.load_icon("open"))
        self.act_save.setIcon(self.load_icon("save"))

        
        self.act_select.setIcon(self.load_icon("select"))
        self.act_pan.setIcon(self.load_icon("pan"))
        self.act_fit.setIcon(self.load_icon("fit"))
        self.act_zoom_in.setIcon(self.load_icon("zoom_in"))
        self.act_zoom_out.setIcon(self.load_icon("zoom_out"))



        self.act_toggle_grid = QAction("Mostra Griglia", self)
        self.act_toggle_grid.setIcon(self.load_icon("grid"))
        self.act_toggle_grid.setCheckable(True)
        self.act_toggle_grid.setChecked(True)
        self.act_toggle_grid.setShortcut("G")
        self.act_toggle_grid.triggered.connect(self.toggle_grid)
        
        self.act_toggle_nodes = QAction("Mostra Nodi", self)
        self.act_toggle_nodes.setIcon(self.load_icon("nodes"))
        self.act_toggle_nodes.setCheckable(True)
        self.act_toggle_nodes.setChecked(False) # Default hidden
        self.act_toggle_nodes.setShortcut("N")
        self.act_toggle_nodes.triggered.connect(self.toggle_nodes)
        
        self.act_toggle_labels = QAction("Mostra Etichette", self)
        self.act_toggle_labels.setIcon(self.load_icon("labels"))
        self.act_toggle_labels.setCheckable(True)
        self.act_toggle_labels.setChecked(True)
        self.act_toggle_labels.setShortcut("L")
        self.act_toggle_labels.triggered.connect(self.toggle_labels)

        self.act_toggle_dimensions = QAction("Mostra Quote", self)
        self.act_toggle_dimensions.setCheckable(True)
        self.act_toggle_dimensions.setChecked(False)
        self.act_toggle_dimensions.setShortcut("D")
        self.act_toggle_dimensions.triggered.connect(self.toggle_dimensions)
        
        self.act_toggle_routes = QAction("Mostra Cavi Tracciati", self)
        self.act_toggle_routes.setCheckable(True)
        self.act_toggle_routes.setChecked(True)
        self.act_toggle_routes.triggered.connect(self.toggle_routes)

        self.act_import_csv = QAction("Importa CSV Cavi...", self)
        self.act_import_csv.setIcon(self.load_icon("import_csv"))
        self.act_import_csv.triggered.connect(self.import_csv)

        self.act_import_dxf = QAction("Importa DXF...", self)
        self.act_import_dxf.setIcon(self.load_icon("import_dxf"))
        self.act_import_dxf.triggered.connect(self.import_dxf)

    def load_icon(self, name):
        path = resource_path(os.path.join("assets", "icons", f"{name}.svg"))
        if os.path.exists(path):
            return QIcon(path)
        return QIcon()

    def create_dock_widgets(self):
        # Tools
        self.dock_tools = QDockWidget("Strumenti", self)
        self.dock_tools.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        tools_widget = QWidget()
        tools_layout = QVBoxLayout()
        tools_layout.setContentsMargins(5, 5, 5, 5)
        tools_layout.setSpacing(10)
        tools_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        def add_tool_btn(action):
            btn = QToolButton()
            btn.setDefaultAction(action)
            btn.setIconSize(QSize(32, 32))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btn.setFixedSize(40, 40)
            tools_layout.addWidget(btn)

        add_tool_btn(self.act_pan)
        add_tool_btn(self.act_select)
        add_tool_btn(self.act_fit)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        tools_layout.addWidget(line)
        
        add_tool_btn(self.act_zoom_in)
        add_tool_btn(self.act_zoom_out)

        tools_widget.setLayout(tools_layout)
        self.dock_tools.setWidget(tools_widget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_tools)

        # Props
        self.dock_props = QDockWidget("Proprietà", self)
        self.dock_props.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.widget_props = QWidget()
        self.layout_props = QVBoxLayout()
        self.layout_props.setContentsMargins(0, 0, 0, 0)

        self.table_props = ReorderableTableWidget(0, 3, enable_filter=False)
        self.table_props.setHorizontalHeaderLabels(["Proprietà", "Valore", "Mostra"])
        self.table_props.verticalHeader().setVisible(False)
        self.table_props.setAlternatingRowColors(True)
        self.table_props.setShowGrid(False)
        
        header = self.table_props.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table_props.setColumnWidth(0, 120)
        self.table_props.setSortingEnabled(False)
        self.table_props.row_order_changed.connect(lambda: self.on_label_prop_toggled(None, None))
        self.layout_props.addWidget(self.table_props)
        

        
        # Mapping to store segment capacities
        # self.segment_capacities = {}

        self.widget_props.setLayout(self.layout_props)
        self.dock_props.setWidget(self.widget_props)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_props)
        
        # Errors
        self.dock_errors = QDockWidget("Errori", self)
        # Errors
        self.dock_errors = QDockWidget("Errori", self)
        self.list_errors = QTableWidget(0, 5)
        self.list_errors.setHorizontalHeaderLabels(["Sorgente", "Destinazione", "Tipo Cavo", "Formazione", "Errore"])
        header = self.list_errors.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.list_errors.verticalHeader().setVisible(False)
        self.list_errors.setAlternatingRowColors(True)
        self.list_errors.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.list_errors.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.dock_errors.setWidget(self.list_errors)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_errors)
        # self.dock_errors.hide() # Keep visible or manage elsewhere

        # Switchboards
        self.dock_switchboards = QDockWidget("Lista Quadri", self)
        self.list_switchboards = QListWidget()
        self.list_switchboards.setToolTip("Doppio click per posizionare il quadro nella scena")
        # Ensure the handler exists or use the click one
        self.list_switchboards.itemClicked.connect(self.place_switchboard_from_list) 
        self.dock_switchboards.setWidget(self.list_switchboards)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_switchboards)
        # self.dock_switchboards.hide() # Visible by default

        # Connections
        self.dock_connections = QDockWidget("Lista Connessioni", self)
        self.widget_connections = QWidget()
        self.layout_connections = QVBoxLayout()
        self.layout_connections.setContentsMargins(0, 0, 0, 0)
        
        self.table_connections = QTableWidget(0, 3)
        self.table_connections.verticalHeader().setVisible(False)
        self.table_connections.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_connections.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_connections.setAlternatingRowColors(True)
        self.table_connections.itemSelectionChanged.connect(self.on_connection_selected)
        self.table_connections.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout_connections.addWidget(self.table_connections)
        
        self.btn_calc_routes = QPushButton("Calcola Percorsi")
        self.btn_calc_routes.clicked.connect(self.calculate_routes)
        self.layout_connections.addWidget(self.btn_calc_routes)
        

        
        self.widget_connections.setLayout(self.layout_connections)
        self.dock_connections.setWidget(self.widget_connections)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_connections)
        
        self.tabifyDockWidget(self.dock_props, self.dock_connections)
        
        # Routed Cables (Cavi Tracciati) - New Tab
        self.dock_routed_cables = QDockWidget("Cavi Tracciati", self)
        self.dock_routed_cables.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        cols_routed = ["ID", "Sorgente", "Destinazione", "Tipo", "Formazione", "Lunghezza (m)"]
        self.table_routed_cables = QTableWidget(0, len(cols_routed))
        self.table_routed_cables.setHorizontalHeaderLabels(cols_routed)
        self.table_routed_cables.verticalHeader().setVisible(False)
        self.table_routed_cables.setAlternatingRowColors(True)
        self.table_routed_cables.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_routed_cables.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_routed_cables.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_routed_cables.itemSelectionChanged.connect(self.on_routed_cable_selected)
        
        self.dock_routed_cables.setWidget(self.table_routed_cables)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_routed_cables)
        
        self.tabifyDockWidget(self.dock_connections, self.dock_routed_cables)
        self.dock_cables = QDockWidget("Dettaglio Cavi", self)
        self.dock_cables.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        # New columns structure
        columns_cables = ["Cavo", "Percorso", "Tipo", "Formazione", "Diametro", "Circuito"]
        self.table_cables = QTableWidget(0, len(columns_cables))
        self.table_cables.setHorizontalHeaderLabels(columns_cables)
        
        self.table_cables.verticalHeader().setVisible(False)
        self.table_cables.setAlternatingRowColors(True)
        self.table_cables.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_cables.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_cables.setShowGrid(True)
        self.table_cables.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # remove stretch last section to allow all to resize or set specific modes?
        # self.table_cables.horizontalHeader().setStretchLastSection(True) 
        self.dock_cables.setWidget(self.table_cables)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_cables)
        
        # Tabify with connections/props, but maybe separate? Let's tabify with them for now 
        # or put it below. The user asked for a separate window (dock).
        self.tabifyDockWidget(self.dock_routed_cables, self.dock_cables)

    def create_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self.act_new)
        file_menu.addAction(self.act_open)
        file_menu.addSeparator()
        file_menu.addAction(self.act_import_dxf)
        file_menu.addAction(self.act_import_csv)
        file_menu.addAction(self.act_save)
        file_menu.addSeparator()
        file_menu.addAction(self.act_exit)

        view_menu = menubar.addMenu("Visualizza")
        view_menu.addAction(self.dock_tools.toggleViewAction())
        view_menu.addAction(self.dock_props.toggleViewAction())
        view_menu.addAction(self.dock_errors.toggleViewAction())
        view_menu.addAction(self.dock_switchboards.toggleViewAction())
        view_menu.addAction(self.dock_connections.toggleViewAction())
        view_menu.addAction(self.dock_routed_cables.toggleViewAction())
        view_menu.addAction(self.dock_cables.toggleViewAction())
        view_menu.addSeparator()
        view_menu.addAction(self.act_toggle_grid)
        view_menu.addAction(self.act_toggle_nodes)
        view_menu.addAction(self.act_toggle_labels)
        view_menu.addAction(self.act_toggle_dimensions)
        view_menu.addAction(self.act_toggle_routes)

    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        toolbar.addAction(self.act_open)
        toolbar.addAction(self.act_save)
        toolbar.addSeparator()
        toolbar.addAction(self.act_pan)
        toolbar.addAction(self.act_select)

    def create_central_widget(self):
        self.scene = CADGraphicsScene()
        self.nodes_group = self.scene.createItemGroup([])
        self.nodes_group.setZValue(100)
        self.nodes_group.setVisible(False)
        self.heatmap_group = self.scene.createItemGroup([])
        self.heatmap_group.setZValue(5)
        # Dimensions Layer (container)
        self.dimensions_group = QGraphicsRectItem()
        self.dimensions_group.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(self.dimensions_group)
        self.dimensions_group.setZValue(110) # Above nodes
        self.dimensions_group.setVisible(False)

        self.view = QGraphicsView(self.scene)
        self.view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self.setCentralWidget(self.view)
        
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        # Install event filter
        self.view.viewport().installEventFilter(self)
        self.view.setMouseTracking(True)

    def create_statusbar(self):
        self.lbl_status = QLabel("Ready")
        self.lbl_coords = QLabel("X: 0.00 Y: 0.00")
        self.lbl_zoom = QLabel("Zoom: 100%")
        self.statusBar().addWidget(self.lbl_status, 1)
        self.statusBar().addPermanentWidget(self.lbl_coords)
        self.statusBar().addPermanentWidget(self.lbl_zoom)

    def eventFilter(self, source, event):
        if source == self.view.viewport():
            if event.type() == event.Type.Wheel:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    # Ctrl + Scroll -> Zoom
                    delta = event.angleDelta().y()
                    if delta > 0:
                        self.zoom_in()
                    else:
                        self.zoom_out()
                    self.update_zoom_label()
                    return True # Consume event

            if event.type() == event.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.MiddleButton:
                    self.zoom_fit()
                    return True

            if event.type() == event.Type.MouseButtonPress:
                # Middle Click -> Pan (Start)
                if event.button() == Qt.MouseButton.MiddleButton:
                    self._panning_middle = True
                    self._last_pan_pos = event.pos()
                    self.view.setCursor(Qt.CursorShape.ClosedHandCursor)
                    return True # Consume event to prevent default behavior
                
                # Existing Left Click Logic
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.placing_switchboard_name:
                        self.finalize_placement()
                        return True
                    
                    # Clear table selections and highlights when clicking on canvas
                    # (Unless clicking items? User said "on drawing or empty space")
                    # We clear blindly; if user actually clicked an item, the view will select that item.
                    # But the "Table Reference" (highlighted cable) should disappear.
                    self.table_connections.clearSelection()
                    self.table_routed_cables.clearSelection()
                    self.table_cables.clearSelection()
                    self.list_errors.clearSelection()
                    self.reset_highlight()
            
            if event.type() == event.Type.MouseButtonRelease:
                 # Middle Click -> Pan (End)
                 if event.button() == Qt.MouseButton.MiddleButton:
                     self._panning_middle = False
                     self.view.setCursor(Qt.CursorShape.ArrowCursor) # Or restore previous
                     return True
                     


                     
            if event.type() == event.Type.MouseMove:
                # Manual Pan
                if hasattr(self, '_panning_middle') and self._panning_middle:
                    delta = event.pos() - self._last_pan_pos
                    self._last_pan_pos = event.pos()
                    
                    # Update Scrollbars (Invert delta)
                    scrollbar_h = self.view.horizontalScrollBar()
                    scrollbar_v = self.view.verticalScrollBar()
                    
                    scrollbar_h.setValue(scrollbar_h.value() - delta.x())
                    scrollbar_v.setValue(scrollbar_v.value() - delta.y())
                    return True

                # Standard tracking
                pos = self.view.mapToScene(event.pos())
                self.lbl_coords.setText(f"X: {pos.x():.2f}  Y: {pos.y():.2f}")
                
                # Handle ghost item movement
                if self.placing_switchboard_item_list_ref and hasattr(self, 'ghost_item') and self.ghost_item:
                    rect = self.ghost_item.rect()
                    center_offset = QPointF(rect.width()/2, rect.height()/2)
                    top_left_target = pos - center_offset
                    self.ghost_item.setPos(top_left_target)
                    


        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if hasattr(self, 'placing_switchboard_name') and self.placing_switchboard_name:
                # Cancel placement
                if hasattr(self, 'ghost_item') and self.ghost_item:
                    self.scene.removeItem(self.ghost_item)
                    self.ghost_item = None
                
                self.placing_switchboard_name = None
                self.placing_switchboard_item_list_ref = None
                self.view.setCursor(Qt.CursorShape.ArrowCursor)
                self.lbl_status.setText("Posizionamento annullato.")
                return

        if event.key() == Qt.Key.Key_Delete:
            # Check if scene has focus or we are just effectively global override
            # Better to check if focusWidget is the view or if we just want this global
            
            selected_items = self.scene.selectedItems()
            if not selected_items:
                return super().keyPressEvent(event)
                
            deleted_count = 0
            for item in selected_items:
                if isinstance(item, SwitchboardItem):
                    # Remove from scene
                    self.scene.removeItem(item)
                    deleted_count += 1
                    
                    # Restore list item
                    name = item.switchboard_name
                    for i in range(self.list_switchboards.count()):
                        list_item = self.list_switchboards.item(i)
                        if list_item.text() == name:
                            # Restore style
                            list_item.setForeground(QBrush(QColor("black")))
                            f = list_item.font()
                            f.setStrikeOut(False)
                            list_item.setFont(f)
                            break
                            
            if deleted_count > 0:
                self.lbl_status.setText(f"Rimossi {deleted_count} quadri")
                return # Consumed
        
        return super().keyPressEvent(event)

    def finalize_placement(self):
        if not hasattr(self, 'ghost_item') or not self.ghost_item: return
        
        name = self.placing_switchboard_name
        
        # Remove any existing item with same name to avoid duplicates
        for item in self.scene.items():
            if isinstance(item, SwitchboardItem) and item.switchboard_name == name and item != self.ghost_item:
                self.scene.removeItem(item)
                break 
        
        # Finalize the ghost item
        self.ghost_item.setOpacity(1.0)
        self.ghost_item.setZValue(50) # Ensure it's on top
        
        self.scene.clearSelection()
        self.ghost_item.setSelected(True)
        
        if self.placing_switchboard_item_list_ref:
            item = self.placing_switchboard_item_list_ref
            item.setForeground(QBrush(QColor("gray")))
            font = item.font()
            font.setStrikeOut(True)
            item.setFont(font)
            
        self.lbl_status.setText(f"Posizionato: {name}")
        self.placing_switchboard_name = None
        self.placing_switchboard_item_list_ref = None
        self.ghost_item = None
        self.view.setCursor(Qt.CursorShape.ArrowCursor)

    def log_error(self, message):
        row = self.list_errors.rowCount()
        self.list_errors.insertRow(row)
        self.list_errors.setItem(row, 0, QTableWidgetItem("-"))
        self.list_errors.setItem(row, 1, QTableWidgetItem("-"))
        self.list_errors.setItem(row, 2, QTableWidgetItem("-"))
        self.list_errors.setItem(row, 3, QTableWidgetItem("-"))
        self.list_errors.setItem(row, 4, QTableWidgetItem(str(message)))
        self.list_errors.scrollToBottom()

    def load_dxf(self, filename):
        try:
            doc = ezdxf.readfile(filename)
            self.dxf_doc = doc # Store for saving
            msp = doc.modelspace()
            self.scene.clear()
            
            # Recreate groups after clear
            self.nodes_group = self.scene.createItemGroup([])
            self.nodes_group.setZValue(100)
            self.nodes_group.setVisible(self.act_toggle_nodes.isChecked())
            
            # Initialize heatmap group safely
            self.heatmap_group = self.scene.createItemGroup([])
            self.heatmap_group.setZValue(5)
            
            pen_default = QPen(QColor("#333"), 1.5)
            pen_default.setCosmetic(True)
            
            # Count entities for progress
            total_entities = 0
            if hasattr(msp, '__len__'):
                total_entities = len(msp)
            else:
                 # Check if we can get count cheaper?
                 pass

            progress = None
            if total_entities > 1000:
                progress = QProgressDialog("Importazione DXF in corso...", "Annulla", 0, total_entities, self)
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.show()

            processed = 0
            count = 0
            from PyQt6.QtWidgets import QApplication
            
            for entity in msp:
                if progress and progress.wasCanceled():
                    break
                    
                processed += 1
                if progress and processed % 100 == 0:
                    progress.setValue(processed)
                    QApplication.processEvents()
                
                item = None
                try:
                    if entity.dxftype() == 'LINE':
                        start = entity.dxf.start; end = entity.dxf.end
                        item = ClickableLineItem(start.x, -start.y, end.x, -end.y)
                        item.setPen(pen_default)
                        self.scene.addItem(item)
                    elif entity.dxftype() == 'CIRCLE':
                        center = entity.dxf.center; radius = entity.dxf.radius
                        item = self.scene.addEllipse(center.x - radius, -(center.y+radius), radius*2, radius*2, pen_default)
                    elif entity.dxftype() == 'LWPOLYLINE':
                        points = entity.get_points(format='xy')
                        if points:
                            path = QPainterPath()
                            path.moveTo(points[0][0], -points[0][1])
                            for p in points[1:]: path.lineTo(p[0], -p[1])
                            if entity.closed: path.closeSubpath()
                            item = self.scene.addPath(path, pen_default)
                            for p in points: self.add_node(p[0], -p[1])
                    if item:
                        if entity.dxftype() == 'LINE':
                             self.add_node(entity.dxf.start.x, -entity.dxf.start.y)
                             self.add_node(entity.dxf.end.x, -entity.dxf.end.y)
                        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
                        count += 1
                except Exception as ex: self.log_error(f"Error {entity.dxftype()}: {ex}")
            self.zoom_fit()
            QMessageBox.information(self, "Importazione", f"Importati {count} oggetti.")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile aprire il file:\n{str(e)}")

    def add_node(self, x, y):
        radius = 2.0 
        node = self.scene.addEllipse(x-radius, y-radius, radius*2, radius*2, QPen(QColor("orange"), 1), QBrush(QColor("yellow")))
        node.setZValue(100)
        self.nodes_group.addToGroup(node)



    def on_selection_changed(self):
        try: items = self.scene.selectedItems()
        except RuntimeError: return

        
        # Clear tables
        self.table_props.setRowCount(0)
        self.table_cables.setRowCount(0)
        self.selected_segment_keys = []
        self.selected_segment_map = {}
        
        if not items: 
            self.lbl_status.setText("Nessun oggetto selezionato")
            return
            
        # Filter Segments
        segments = [i for i in items if (isinstance(i, QGraphicsLineItem) or hasattr(i, 'line'))]
        
        # If no segments, maybe fallback to showing first item info (like switchboard)
        if not segments:
            # Ensure keyboard focus on view when clicking/selecting items
            self.view.setFocus()
            
            # Check if switchboard logic
            if items:
                 item = items[0]
                 self.lbl_status.setText(f"Oggetto selezionato: {type(item).__name__}")
                 props = {"Tipo": type(item).__name__, "X": f"{item.x():.2f}", "Y": f"{item.y():.2f}"}
                 self.table_props.setRowCount(len(props))
                 for i, (k, v) in enumerate(props.items()):
                    self.table_props.setItem(i, 0, QTableWidgetItem(k))
                    self.table_props.setItem(i, 1, QTableWidgetItem(v))
                    self.table_props.setItem(i, 2, QTableWidgetItem("")) 
                 return

        self.lbl_status.setText(f"Selezionati {len(segments)} segmenti")
        
        


        # Collect keys and aggregate data

        keys = []
        
        # We need to build a common property set. 
        # If values differ, show <Misti>.
        # We also need to determine Checkbox state: if ALL have it active -> Checked.
        
        agg_props = {}
        agg_config = {} # Prop -> True/False (if all have it)
        
        first = True
        
        all_cable_rows = []
        
        for item in segments:
            l = item.line()
            p1 = routing.get_node_key(l.x1(), l.y1()); p2 = routing.get_node_key(l.x2(), l.y2())
            key = tuple(sorted((p1, p2)))
            keys.append(key)
            self.selected_segment_map[key] = item
            
            # --- Build Props for this segment ---
            current_props = {}
            current_props["Lunghezza"] = f"{l.length():.2f}"
            
            # Show assigned capacity if any
            # Show assigned capacity if any
            if hasattr(self, 'segment_trays') and key in self.segment_trays:
                 trays = self.segment_trays[key]
                 if trays:
                     # current_props["Sezione"] = f"{len(trays)} element(i)" # REMOVED as per user request
                     for idx, t in enumerate(trays):
                         current_props[f"Passerella {idx+1}"] = f"{t.name} ({t.service})"
                     
                     service_sums = {}
                     for t in trays:
                         if hasattr(t, 'included_services') and t.included_services:
                             for item in t.included_services:
                                 if isinstance(item, dict):
                                     s_name = item.get('name')
                                     s_pct = item.get('percent', 0)
                                     val = t.capacity * (s_pct / 100.0)
                                     service_sums[s_name] = service_sums.get(s_name, 0) + val
                                 elif isinstance(item, str):
                                     service_sums[item] = service_sums.get(item, 0) + t.capacity
                         else:
                             s_name = t.service
                             service_sums[s_name] = service_sums.get(s_name, 0) + t.capacity
                             
                     for s_name, val in service_sums.items():
                         if val > 0:
                             current_props[f"Cap. {s_name}"] = f"{val:.0f} mm²"

            if hasattr(self, 'segment_capacities') and key in self.segment_capacities:
                 val = self.segment_capacities[key]
                 if isinstance(val, tuple):
                     current_props["Capacità"] = f"{val[0]} mm²"
                     current_props["Passerella"] = f"{val[1]}"
                 else:
                     current_props["Capacità"] = f"{val} mm²"
            
            if hasattr(self, 'segment_details') and key in self.segment_details:
                note = self.segment_details[key]
                if note: current_props["Note"] = note
                
            # Cables
            if hasattr(self, 'segment_usage'):
                 cables = self.segment_usage.get(key, [])
                 if cables:
                     current_props["Totale Cavi"] = f"{len(cables)}"
                     # Add to detailed cable list
                     for i, c in enumerate(cables):
                        c_id = c.get('ID', f"Cavo {i+1}")
                        route = f"{c.get('FROM')}->{c.get('TO')}"
                        c_type = c.get('Cable Type', c.get('TYPE', ''))
                        form = c.get('Cable Formation', '')
                        diam = f"{c.get('Diameter (mm)', '')} mm"
                        circ = c.get('Circuit Type', '')
                        all_cable_rows.append([c_id, route, c_type, form, diam, circ])

            # Config
            current_config = self.segment_label_config.get(key, {"Trays", "Note"}) # Changed Default
            if key not in self.segment_label_config:
                # Store default if missing, avoids issues later
                self.segment_label_config[key] = current_config 

            # Force "Lunghezza" if global toggle is active
            if self.act_toggle_dimensions.isChecked():
                current_config.add("Lunghezza") 

            # --- Aggregate ---
            if first:
                agg_props = current_props.copy()
                # Checkbox state: start with first
                for p in current_props:
                    if p in current_config: agg_config[p] = True
                    else: agg_config[p] = False
                first = False
            else:
                # Merge props
                for k, v in current_props.items():
                    if k not in agg_props: 
                         # Prop exists in current but not in agg (so not in previous). 
                         agg_props[k] = "<Vari>" 
                    elif agg_props[k] != v and agg_props[k] != "<Vari>":
                         agg_props[k] = "<Vari>"
                
                # Check config
                for p in list(agg_config.keys()):
                    if p not in current_config: agg_config[p] = False
                
                # Handled mixed availability by defaulting to False if new
                for p in current_props:
                     if p not in agg_config:
                          agg_config[p] = False 
                          
        self.selected_segment_keys = keys
        



        # Populate Props Table
        # Ensure standard keys are present if we want to allow enabling them explicitly?
        # No, show what we found.
        
        self.table_props.setRowCount(len(agg_props))
        for i, (k, v) in enumerate(agg_props.items()):
            self.table_props.setItem(i, 0, QTableWidgetItem(k))
            self.table_props.setItem(i, 1, QTableWidgetItem(v))
            
            # Checkbox
            chk = QCheckBox()
            # Checked only if True in agg_config
            chk.setChecked(agg_config.get(k, False))
            
            chk.toggled.connect(lambda state, p=k: self.on_label_prop_toggled(p, state))
            
            container = QWidget()
            lay = QVBoxLayout(container); lay.setContentsMargins(0,0,0,0); lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(chk)
            self.table_props.setCellWidget(i, 2, container)

        self.table_props.resizeRowsToContents()
        
        # Force refresh of labels on canvas with new config
        self.on_label_prop_toggled(None, None)
            
        # Cables
        self.table_cables.setRowCount(len(all_cable_rows))
        for r, row_data in enumerate(all_cable_rows):
            for c, val in enumerate(row_data):
                self.table_cables.setItem(r, c, QTableWidgetItem(str(val)))
        if all_cable_rows:
            self.table_cables.resizeColumnsToContents()
            self.dock_cables.show()


    def on_label_prop_toggled(self, prop_name, checked):
        if not hasattr(self, 'selected_segment_keys') or not self.selected_segment_keys: return
        
        # Update Model from Args (if provided)
        if prop_name is not None and checked is not None:
            for key in self.selected_segment_keys:
                if key not in self.segment_label_config:
                    self.segment_label_config[key] = set() # Default empty if new
                
                if checked:
                    self.segment_label_config[key].add(prop_name)
                else:
                    self.segment_label_config[key].discard(prop_name)
        
        # Rebuild Labels based on TABLE ORDER
        # Iterate over table rows to get visual order
        
        for key in self.selected_segment_keys:
            item = self.selected_segment_map.get(key)
            if not item: continue
            
            lines = []
            
            # Use Table Props Order
            for r in range(self.table_props.rowCount()):
                # Get Property Name and Checkbox State
                p_item = self.table_props.item(r, 0)
                v_item = self.table_props.item(r, 1)
                
                if not p_item or not v_item: continue
                
                p_name = p_item.text()
                val_text = v_item.text()
                
                # Check Widget State directly from Table (Source of Truth for Visual Order)
                chk_widget = self.table_props.cellWidget(r, 2)
                is_checked = False
                if chk_widget:
                    # chk_widget is container, find child chk
                    chk = chk_widget.findChild(QCheckBox)
                    if chk: is_checked = chk.isChecked()
                
                if is_checked:
                    # Add to label
                    # Formatting logic:
                    if "Passerella" in p_name:
                         # Value is "Name (Service)" -> Label "- Name (Service)"?
                         lines.append(f"- {val_text}")
                    elif "Lunghezza" in p_name:
                         lines.append(f"L: {val_text}")
                    elif "Capacità" in p_name: # Cap. Power / Cap. Data
                         lines.append(f"{p_name}: {val_text}")  
                    elif "Totale Cavi" in p_name:
                         lines.append(f"Cavi: {val_text}")
                    elif "Note" in p_name:
                         lines.append(val_text)
                    else:
                         # Default
                         lines.append(f"{val_text}")

            final_text = "\n".join(lines)
            
            self.update_segment_label(key, item.line(), final_text)
            
            lbl = self.segment_labels.get(key)
            if lbl:
                 indiv = self.segment_label_visibility.get(key, True)
                 glob = self.act_toggle_labels.isChecked()
                 if not final_text.strip():
                     lbl.setVisible(False)
                 else:
                     lbl.setVisible(indiv and glob)
    
    def toggle_dimensions(self):
        # Global Toggle: Enable "Lunghezza" property for ALL segments
        target_state = self.act_toggle_dimensions.isChecked()
        
        # 1. Iterate all lines in scene
        for item in self.scene.items():
            if isinstance(item, ClickableLineItem) or (isinstance(item, QGraphicsLineItem) and hasattr(item, 'line')):
                l = item.line()
                p1 = routing.get_node_key(l.x1(), l.y1())
                p2 = routing.get_node_key(l.x2(), l.y2())
                key = tuple(sorted((p1, p2)))
                
                # Ensure Config Exists
                if key not in self.segment_label_config:
                    self.segment_label_config[key] = {"Trays", "Note"}
                
                # Update Config
                if target_state:
                    self.segment_label_config[key].add("Lunghezza")
                else:
                    self.segment_label_config[key].discard("Lunghezza")
                
                # Trigger Label Refresh
                # We need to construct the text. calling update_segment_label with empty text might hide it?
                # No, update_segment_label takes text. We need to Re-evaluate text.
                # Use a helper or just re-run the logic?
                # Actually on_label_prop_toggled logic rebuilds text.
                # But that function relies on TABLE PROPS for order.
                # If we are doing this globally, we might not have a table for every item.
                # We need a headless way to rebuild label text.
                
                self.rebuild_label_for_segment(key, item)

        # 2. Update Properties Table (if open)
        # Scan rows for "Lunghezza" and update chk
        for r in range(self.table_props.rowCount()):
             item = self.table_props.item(r, 0)
             if item and "Lunghezza" in item.text():
                 chk_widget = self.table_props.cellWidget(r, 2)
                 if chk_widget:
                     chk = chk_widget.findChild(QCheckBox)
                     if chk:
                         chk.blockSignals(True) # Prevent recursion
                         chk.setChecked(target_state)
                         chk.blockSignals(False)
                 break
                 
    def rebuild_label_for_segment(self, key, item):
        # Reconstruct label text based on config
        cfg = self.segment_label_config.get(key, set())
        lines = []
        
        # We need values. Length is easy. Other props need lookup.
        l = item.line()
        
        # Order: Lunghezza, Capacità, Cavi, Note, (Others from trays?)
        # We define a standard order since we don't have the table here.
        
        # 1. Lunghezza
        if "Lunghezza" in cfg:
            lines.append(f"L: {l.length():.2f}")
            
        # 2. Capacities / Trays
        if hasattr(self, 'segment_trays') and key in self.segment_trays:
             trays = self.segment_trays[key]
             for idx, t in enumerate(trays):
                 p_name = f"Passerella {idx+1}"
                 # How to check if this specific tray is enabled? 
                 # In Table we used specific names.
                 # Let's assume if "Trays" or specific name is in cfg.
                 # Simplified: user usually toggles "Passerella X".
                 if p_name in cfg or "Trays" in cfg: # Backwards compat
                      lines.append(f"- {t.name} ({t.service})")
                      
             # Capacities (Calculated)
             # ... Logic from on_selection_changed copying ...
             # This duplication is messy. Ideally refactor "get_segment_properties(key)"
             # For now, let's just handle Length primarily as requested.
        
        # 3. Cable Count
        if "Totale Cavi" in cfg and hasattr(self, 'segment_usage'):
             cables = self.segment_usage.get(key, [])
             if cables: lines.append(f"Cavi: {len(cables)}")
             
        # 4. Notes
        if "Note" in cfg and hasattr(self, 'segment_details'):
             note = self.segment_details.get(key)
             if note: lines.append(note)

        final_text = "\n".join(lines)
        self.update_segment_label(key, l, final_text)

    def toggle_routes(self, checked):
        if hasattr(self, 'heatmap_group') and self.heatmap_group:
            self.heatmap_group.setVisible(checked)

    def calculate_routes(self):
        self.log_file = None # Initialize to None
        try:
            # Open Log File
            self.log_file = open("routing_log.txt", "w", encoding="utf-8")
            
            def log(msg):
                print(msg, flush=True)
                if self.log_file:
                    self.log_file.write(msg + "\n")
                    self.log_file.flush()

            log("--- Routing Log Started ---")
            
            # Clear previous errors
            self.list_errors.setRowCount(0)
            self.dock_errors.hide()
            
            # 1. Build Graph
            log(f"M: Starting calculate_routes...")
            try:
                items = [i for i in self.scene.items() if (isinstance(i, QGraphicsLineItem) or hasattr(i, 'line'))]
                graph = routing.build_routing_graph(items)
                if not graph: 
                    log("M: Graph is empty.")
                    QMessageBox.warning(self, "Errore", "Impossibile costruire il grafo di routing.")
                    return
                log(f"M: Graph built with {len(graph)} nodes.")
            except Exception as e:
                log(f"M: Error building graph: {e}")
                traceback.print_exc()
                return

            # 2. Cleanup Old Routes
            # No need to remove items from scene as we don't add them anymore.
            # Just clear data.
            if hasattr(self, 'all_connections'):
                for conn in self.all_connections:
                    if '_route_path' in conn: del conn['_route_path']


            # 3. Add Virtual Nodes (Switchboards)
            try:
                lines = [i for i in self.scene.items() if isinstance(i, QGraphicsLineItem)]
                sw_positions_map = {} 
                points_to_map = []
                for item in self.scene.items():
                    if isinstance(item, SwitchboardItem):
                        pos = item.pos() + item.rect().center()
                        p = (pos.x(), pos.y())
                        sw_positions_map[item.switchboard_name] = p
                        points_to_map.append(p)
                
                log(f"M: Found {len(sw_positions_map)} switchboards.")
                node_mapping = routing.add_virtual_nodes(graph, points_to_map, lines)
                log("M: Virtual nodes added.")
                
                # DEBUG: Print status of first 5 segments in graph to see their assigned service
                count_debug = 0
                for k, v in graph.items():
                    if count_debug >= 3: break
                    for cost, neighbor, props in v:
                        trays_debug = props.get('trays', [])
                        services_debug = [getattr(t, 'service', 'Unassigned') if hasattr(t, 'service') else t.get('service','?') for t in trays_debug]
                        log(f"M: Segment Check: Node={k} Neighbor={neighbor} Services={services_debug}")
                        count_debug += 1
                        if count_debug >= 3: break
                
            except Exception as e:
                 log(f"M: Error adding virtual nodes: {e}")
                 traceback.print_exc()
                 return

            if not hasattr(self, 'all_connections'): 
                log("M: No connections loaded.")
                return
            
            self.segment_usage = {}
            pen_route = QPen(QColor(0, 200, 0, 180), 4)
            pen_route = QPen(QColor(0, 200, 0, 180), 4)
            count = 0 # Initialize count variable
            failed_connections = []
            
            # 4. Route Connections
            # 4. Route Connections
            log(f"M: Routing {len(self.all_connections)} connections...")
            for conn_idx, conn in enumerate(self.all_connections):
                try:
                    s_name = conn.get('FROM'); e_name = conn.get('TO')
                    
                    if s_name == e_name:
                         log(f"M: Warning: Self-connection detected on {s_name}. Skipping routing.")
                         failed_connections.append({
                            'from': s_name, 
                            'to': e_name, 
                            'type': '-', 
                            'formation': '-',
                            'error': "Self-connection (From=To)"
                         })
                         continue
                    
                    # Extract cable info EARLY so it's available for error reporting
                    # STRICTLY prioritize 'Circuit Type'. 
                    # If not present, try others, but default to 'Unassigned' instead of 'Power'
                    raw_type = conn.get('Circuit Type')
                    
                    if not raw_type:
                        raw_type = conn.get('Cable Type') or conn.get('Type') or conn.get('Service') or 'Unassigned'
                    
                    cable_type = str(raw_type).strip()
                    
                    # Try multiple keys for formation
                    form_val = conn.get('Cable Formation') or conn.get('Formation') or conn.get('Formazione') or conn.get('Form') or '-'
                    cable_formation = str(form_val).strip()

                    if s_name in sw_positions_map and e_name in sw_positions_map:
                        s_pos = sw_positions_map[s_name]; e_pos = sw_positions_map[e_name]
                        s_node = node_mapping.get(s_pos)
                        e_node = node_mapping.get(e_pos)
                        
                        if s_node and e_node:
                            # Debug first few connections to verify data and AVAILABLE KEYS
                            if count < 3:
                                log(f"M: Connection {s_name}->{e_name}")
                                log(f"M:   Resolved Type: '{cable_type}'")
                                if count == 0:
                                    log(f"M:   Available Keys: {list(conn.keys())}")

                            try: d = float(conn.get('Diameter (mm)', 0))
                            except: d = 0
                            cable_size = math.pi * ((d/2)**2)
                            
                            path = routing.astar(graph, s_node, e_node, cable_type, cable_size)
                            if path:
                                display_path = [s_pos] + path + [e_pos]
                                route_path = self.create_route_path(display_path)
                                conn['_route_path'] = route_path
                                count += 1
                                for i in range(len(path)-1):
                                    k = tuple(sorted((path[i], path[i+1])))
                                    if k not in self.segment_usage: self.segment_usage[k] = []
                                    self.segment_usage[k].append(conn)
                            else:
                                failure_reason = "Segregation/Capacity/Connectivity"
                                # log specific failure for debug?
                                if count < 3: log(f"M:   FAILED: {failure_reason}")
                                failed_connections.append({
                                    'from': s_name, 
                                    'to': e_name, 
                                    'type': cable_type, 
                                    'formation': cable_formation,
                                    'error': failure_reason
                                })
                        else:
                             failed_connections.append({
                                'from': s_name,
                                'to': e_name,
                                'type': cable_type,
                                'formation': cable_formation,
                                'error': "Switchboard not connected to network"
                             })
                    else:
                         failed_connections.append({
                            'from': s_name,
                            'to': e_name,
                            'type': cable_type,
                            'formation': cable_formation,
                            'error': "Switchboard positions not found"
                         })
                         
                except Exception as e:
                    log(f"M: Error checking connection {conn_idx}: {e}")
                    continue
                    
            log(f"M: Routing complete. Found {count} paths.")
            
            # Debug Stats
            pair_counts = {}
            # Debug Stats
            pair_counts = {}
            for conn in self.all_connections:
                if '_route_path' in conn and conn['_route_path'] is not None:
                    pair = tuple(sorted((conn.get('FROM'), conn.get('TO'))))
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1
            
            log("--- Routing Stats (Success) ---")
            for pair, c in pair_counts.items():
                log(f"  {pair[0]} <-> {pair[1]}: {c}")
            log("-------------------------------")
            
            # --- Populate Routed Cables Table ---
            self.table_routed_cables.setRowCount(0)
            self.routed_connections_map = [] # Store reference to conn for each row
            
            for conn in self.all_connections:
                if '_route_path' in conn and conn['_route_path'] is not None:
                    path = conn['_route_path']
                    length = path.length()
                    
                    self.routed_connections_map.append(conn)
                    
                    row = self.table_routed_cables.rowCount()
                    self.table_routed_cables.insertRow(row)
                    
                    # Columns: ID, Source, Dest, Type, Form, Length
                    self.table_routed_cables.setItem(row, 0, QTableWidgetItem(str(conn.get('ID', '-'))))
                    self.table_routed_cables.setItem(row, 1, QTableWidgetItem(str(conn.get('FROM', '-'))))
                    self.table_routed_cables.setItem(row, 2, QTableWidgetItem(str(conn.get('TO', '-'))))
                    self.table_routed_cables.setItem(row, 3, QTableWidgetItem(str(conn.get('Cable Type', '-'))))
                    self.table_routed_cables.setItem(row, 4, QTableWidgetItem(str(conn.get('Cable Formation', '-'))))
                    self.table_routed_cables.setItem(row, 5, QTableWidgetItem(f"{length:.2f}"))
            
            self.table_routed_cables.resizeColumnsToContents()
            self.dock_routed_cables.show()
            self.dock_routed_cables.raise_()
            
            # Show Errors if any
            if failed_connections:
                 self.report_routing_errors(failed_connections)
            
            # 5. Heatmap
            self.update_heatmap()
            
            QMessageBox.information(self, "Routing", f"Calcolati {count} percorsi.\nVerifica mappa termica (Blu/Arancio/Rosso) per riempimento.")
            
        except Exception as e:
            log(f"M: CRITICAL ERROR IN ROUTING: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Errore", f"Errore critico nel routing: {e}")

    def update_heatmap(self):
        print("M: Updating Heatmap...", flush=True)
        try:
            default_tray_name = "Default (100x50)"
            default_capacity = 5000.0 

            # Create group
            print("M: Handling heatmap group...", flush=True)
            if self.heatmap_group is not None:
                try:
                    self.scene.removeItem(self.heatmap_group)
                except Exception as e:
                    print(f"M: Cleanup ignored: {e}", flush=True)
                self.heatmap_group = None
            
            self.heatmap_group = self.scene.createItemGroup([])
            self.heatmap_group.setZValue(5) 
            self.heatmap_group.setVisible(self.act_toggle_routes.isChecked())
            print("M: Heatmap group created.", flush=True)

            print(f"M: Processing {len(self.segment_usage)} segments for heatmap...", flush=True)
            for segment, cables in self.segment_usage.items():
                try:
                    p1, p2 = segment
                    
                    total_area = 0.0
                    for c in cables:
                        try: d = float(c.get('Diameter (mm)', '0').strip() or 0)
                        except: d = 0
                        total_area += math.pi * ((d/2)**2)
                        
                    capacity = default_capacity
                    tray_name = default_tray_name
                    
                    if hasattr(self, 'segment_trays') and segment in self.segment_trays:
                        trays = self.segment_trays[segment]
                        if trays:
                            capacity = sum(t.capacity for t in trays)
                            tray_name = " + ".join([t.name for t in trays])
                            if len(trays) > 1: tray_name = f"Multi ({len(trays)})"
                    elif hasattr(self, 'segment_capacities') and segment in self.segment_capacities:
                        val = self.segment_capacities[segment]
                        if isinstance(val, tuple): capacity, tray_name = val
                        else: capacity = val
                    
                    if not capacity or capacity <= 0: capacity = 1.0
                    ratio = total_area / capacity
                    
                    # --- Simplified Heatmap Visualization (Blue only) ---
                    
                    # 1. Color = Blue
                    main_color = QColor("blue")
                    main_color.setAlpha(180) # Slight transparency

                    # 2. Variable Thickness - Reduced
                    # New range: 2 to 6 pixels
                    base_width = 2.0 + (min(ratio, 1.0) * 4.0)
                    
                    # 3. Glow Effect (Removed for cleaner look as requested "contenuto")
                    # If desired, keep it very subtle or remove. Let's remove to reduce thickness.
                    

                    
                    # 4. Main Line
                    pen_main = QPen(main_color, base_width)
                    pen_main.setCapStyle(Qt.PenCapStyle.RoundCap)
                    
                    line_main = QGraphicsLineItem(p1[0], p1[1], p2[0], p2[1])
                    line_main.setPen(pen_main)
                    
                    # Tooltip only on main line
                    info_tooltip = (f"Passerella: {tray_name}\n"
                                  f"Riempimento: {ratio*100:.1f}%\n"
                                  f"Cavi Presenti: {len(cables)}\n"
                                  f"Area Occupata: {total_area:.1f} mm²\n"
                                  f"Capacità Totale: {capacity:.1f} mm²")
                    line_main.setToolTip(info_tooltip)
                    
                    self.heatmap_group.addToGroup(line_main)
                    
                except Exception as e:
                    print(f"M: Error processing heatmap segment: {e}")
                    
        except Exception as e:
            print(f"M: Error updating heatmap: {e}")

        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            QMessageBox.critical(self, "Errore Inatteso", f"Si è verificato un errore durante il calcolo:\n{str(e)}\n\n{tb}")
            return
        


    def create_route_path(self, path_nodes):
        path = QPainterPath()
        if not path_nodes: return path
        path.moveTo(path_nodes[0][0], path_nodes[0][1])
        for p in path_nodes[1:]: path.lineTo(p[0], p[1])
        return path

    def report_routing_errors(self, errors):
        # errors is a list of dicts now
        self.list_errors.setRowCount(0)
        
        for err in errors:
            row = self.list_errors.rowCount()
            self.list_errors.insertRow(row)
            
            # Check format, simpler fallback if string
            if isinstance(err, str):
                self.list_errors.setItem(row, 0, QTableWidgetItem("-"))
                self.list_errors.setItem(row, 1, QTableWidgetItem("-"))
                self.list_errors.setItem(row, 2, QTableWidgetItem("-"))
                self.list_errors.setItem(row, 3, QTableWidgetItem("-"))
                self.list_errors.setItem(row, 4, QTableWidgetItem(err))
            else:
                self.list_errors.setItem(row, 0, QTableWidgetItem(err.get('from', '-')))
                self.list_errors.setItem(row, 1, QTableWidgetItem(err.get('to', '-')))
                self.list_errors.setItem(row, 2, QTableWidgetItem(err.get('type', '-')))
                self.list_errors.setItem(row, 3, QTableWidgetItem(err.get('formation', '-')))
                self.list_errors.setItem(row, 4, QTableWidgetItem(err.get('error', '-')))
        
        self.dock_errors.show()
        self.dock_errors.raise_()
        # Enforce stretch mode
        self.list_errors.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        QMessageBox.warning(self, "Attenzione", f"{len(errors)} collegamenti non instradati. Vedi pannello 'Errori'.")

    def reset_highlight(self):
        if hasattr(self, 'highlight_overlay') and self.highlight_overlay:
            if self.highlight_overlay.scene() == self.scene:
                self.scene.removeItem(self.highlight_overlay)
            self.highlight_overlay = None

    def highlight_connection(self, conn):
        cid = conn.get('ID', '?')
        self.lbl_status.setText(f"Selezionato: {cid}")
        
        # 1. Clear existing highlight overlay if any
        self.reset_highlight()
            
        # 2. Add new highlight overlay
        if '_route_path' in conn:
            path = conn['_route_path']
            
            if path.isEmpty():
                print("DEBUG: Path is empty!")
                return

            self.highlight_overlay = QGraphicsPathItem(path)
            
            # Check bounding rect
            br = path.boundingRect()
            
            # STYLE: Red, Width 8
            pen = QPen(QColor("red"), 8) 
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            self.highlight_overlay.setPen(pen)
                
            self.highlight_overlay.setZValue(9999) # Absolute top
            self.highlight_overlay.setOpacity(1.0)
            
            self.scene.addItem(self.highlight_overlay)
            
            # Pan view
            center = br.center()
            self.view.ensureVisible(br, 50, 50) 
            self.view.centerOn(center)
            
            self.scene.update()
        else:
            self.lbl_status.setText(f"Selezionato: {cid} (Non instradato)")

    def on_connection_selected(self):
        try:
            rows = self.table_connections.selectionModel().selectedRows()
            if not rows: 
                self.reset_highlight()
                return
            
            row = rows[0].row()
            if row < 0 or row >= len(self.all_connections): return
            
            conn = self.all_connections[row]
            self.highlight_connection(conn)

        except Exception as e:
            traceback.print_exc()
            print(f"Error selecting connection: {e}")

    def on_routed_cable_selected(self):
        try:
            if not hasattr(self, 'routed_connections_map'): return
            
            rows = self.table_routed_cables.selectionModel().selectedRows()
            if not rows: 
                self.reset_highlight()
                return
            
            row = rows[0].row()
            if row < 0 or row >= len(self.routed_connections_map): return
            
            conn = self.routed_connections_map[row]
            self.highlight_connection(conn)
            
        except Exception as e:
            traceback.print_exc()
            print(f"Error selecting routed cable: {e}")
            print(f"DEBUG: Error in selection: {e}")
            import traceback
            traceback.print_exc()

    def import_dxf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importa DXF", "", "DXF (*.dxf)")
        if path: self.load_dxf(path)

    def new_project(self):
        # 1. Open Dialog
        dlg = NewProjectDialog(self)
        if dlg.exec():
            dxf_path, csv_path, save_path = dlg.get_data()
            
            if not save_path:
                QMessageBox.warning(self, "Attenzione", "Devi selezionare un percorso per salvare il progetto.")
                return

    def cleanup_groups(self):
        # Safely remove groups if they exist
        if hasattr(self, 'nodes_group') and self.nodes_group:
            if self.nodes_group.scene() == self.scene: self.scene.removeItem(self.nodes_group)
            self.nodes_group = None
            
        if hasattr(self, 'heatmap_group') and self.heatmap_group:
            if self.heatmap_group.scene() == self.scene: self.scene.removeItem(self.heatmap_group)
            self.heatmap_group = None

    def reset_application_state(self):
        self.cleanup_groups()
        self.scene.clear()
        
        self.dxf_doc = None
        
        # Data Structures
        self.segment_trays = {}
        self.segment_details = {}
        # self.segment_capacities = {} # Deprecated
        self.segment_usage = {}
        self.segment_labels = {}
        self.segment_label_config = {}
        self.segment_label_visibility = {}
        self.route_items = []
        self.all_connections = []
        
        # Temp items
        self.placing_switchboard_name = None
        self.placing_switchboard_item_list_ref = None
        self.ghost_item = None
        
        # UI Tables
        self.list_switchboards.clear()
        self.table_connections.setRowCount(0)
        self.table_routed_cables.setRowCount(0)
        self.table_cables.setRowCount(0)
        self.table_props.setRowCount(0)
        self.list_errors.setRowCount(0)
        
        self.current_project_path = None
        self.setWindowTitle("CableRouteCAD")

    def process_loaded_connections(self):
        # Processes self.all_connections to populate UI
        if not self.all_connections: return
        
        self.list_switchboards.clear()
        sws = set()
        for c in self.all_connections: 
            if c.get('FROM'): sws.add(c['FROM'])
            if c.get('TO'): sws.add(c['TO'])
            
        for s in sorted(sws): 
            self.list_switchboards.addItem(s)
            
        self.populate_connections_list()
        
        # Show relevant docks
        self.dock_connections.show()
        if sws: self.dock_switchboards.show()

    def new_project(self):
        # 1. Open Dialog
        dlg = NewProjectDialog(self)
        if dlg.exec():
            dxf_path, csv_path, save_path = dlg.get_data()
            
            if not save_path:
                QMessageBox.warning(self, "Attenzione", "Devi selezionare un percorso per salvare il progetto.")
                return

            # 2. Reset Everything
            self.reset_application_state()
            
            self.current_project_path = save_path 
            self.setWindowTitle(f"CableRouteCAD - {os.path.basename(save_path)}")
            
            # 3. Load DXF
            if dxf_path and os.path.exists(dxf_path):
                self.load_dxf(dxf_path)
            
            # 4. Load CSV
            if csv_path and os.path.exists(csv_path):
                try:
                    with open(csv_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        self.all_connections = list(reader)
                    
                    self.process_loaded_connections()
                    
                    QMessageBox.information(self, "Progetto", "Nuovo progetto creato con successo!")
                except Exception as e:
                    QMessageBox.critical(self, "Errore CSV", f"Errore caricamento CSV: {e}")


    def zoom_fit(self):
        if self.scene.items(): self.view.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_in(self): self.view.scale(1.2, 1.2); self.update_zoom_label()
    def zoom_out(self): self.view.scale(1/1.2, 1/1.2); self.update_zoom_label()
    def update_zoom_label(self): self.lbl_zoom.setText(f"Zoom: {int(self.view.transform().m11()*100)}%")
    
    def activate_pan(self): self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
    def activate_select(self): self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
    
    def toggle_grid(self, c): self.scene.set_grid_visible(c)
    def toggle_nodes(self, c): self.nodes_group.setVisible(c)
    
    def toggle_labels(self, c):
        # Global toggle
        for key, lbl in self.segment_labels.items():
            indiv = self.segment_label_visibility.get(key, True)
            lbl.setVisible(c and indiv)

    def set_individual_label_visibility(self, visible, key):
        self.segment_label_visibility[key] = visible
        if key in self.segment_labels:
            global_visible = self.act_toggle_labels.isChecked()
            self.segment_labels[key].setVisible(global_visible and visible)
    
    def place_switchboard_from_list(self, item):
        self.placing_switchboard_name = item.text()
        self.placing_switchboard_item_list_ref = item
        
        # Remove old ghost if exists
        if hasattr(self, 'ghost_item') and self.ghost_item:
            self.scene.removeItem(self.ghost_item)
            
        # Create new ghost
        wb = 80; hb = 50
        self.ghost_item = SwitchboardItem(self.placing_switchboard_name, QRectF(0, 0, wb, hb))
        self.ghost_item.setOpacity(0.6)
        self.scene.addItem(self.ghost_item)
        
        self.view.setCursor(Qt.CursorShape.CrossCursor)
        self.lbl_status.setText(f"Posiziona {item.text()}")

    def _segment_key_to_str(self, key):
        # key is ((x1,y1), (x2,y2)) (sorted)
        p1, p2 = key
        return f"{p1[0]},{p1[1]}|{p2[0]},{p2[1]}"

    def _str_to_segment_key(self, s):
        try:
            parts = s.split('|')
            p1_s = parts[0].split(',')
            p2_s = parts[1].split(',')
            p1 = (float(p1_s[0]), float(p1_s[1]))
            p2 = (float(p2_s[0]), float(p2_s[1]))
            return tuple(sorted((p1, p2)))
        except:
             return None

    def save_project(self):
        if hasattr(self, 'current_project_path') and self.current_project_path:
            self._save_to_path(self.current_project_path)
            QMessageBox.information(self, "Salvataggio", f"Progetto salvato in:\n{self.current_project_path}")
        else:
            self.save_project_as()

    def save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salva Progetto Come...", "", "Cable Project (*.cvp)")
        if path:
            if not path.endswith(".cvp"): path += ".cvp"
            self.current_project_path = path
            self.setWindowTitle(f"CAD Viewer Pro 2025 - {os.path.basename(path)}")
            self._save_to_path(path)

    def _save_to_path(self, path):
        try:
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # 1. Save DXF
                if hasattr(self, 'dxf_doc') and self.dxf_doc:
                    # Save to memory buffer
                    from io import StringIO
                    # ezdxf write needs a stream usually, let's use temporary file to be safe compatible with all versions
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                        self.dxf_doc.saveas(tmp.name)
                        tmp.close()
                        zf.write(tmp.name, "drawing.dxf")
                        os.unlink(tmp.name)
                else:
                    # Should we warn?
                    pass
                    
                # 2. Save Connections (CSV)
                if hasattr(self, 'all_connections') and self.all_connections:
                    buf = io.StringIO()
                    if len(self.all_connections) > 0:
                        keys = list(self.all_connections[0].keys())
                        writer = csv.DictWriter(buf, fieldnames=keys)
                        writer.writeheader()
                        writer.writerows(self.all_connections)
                    zf.writestr("connections.csv", buf.getvalue())
                    
                # 3. Save State (JSON)
                state = {
                    "version": "1.0",
                    "switchboards": {},
                    "segments": {},
                    "mixed_definitions": self.mixed_service_definitions,
                    "settings": {
                        "grid_visible": self.act_toggle_grid.isChecked(),
                        "nodes_visible": self.act_toggle_nodes.isChecked(),
                        "labels_visible": self.act_toggle_labels.isChecked()
                    }
                }
                
                # Switchboards
                for item in self.scene.items():
                    if isinstance(item, SwitchboardItem):
                         state["switchboards"][item.switchboard_name] = {
                             "x": item.pos().x(),
                             "y": item.pos().y(),
                             "rotation": item.rotation()
                         }
                         
                # Segments
                # We need to iterate over known data (segment_trays, segment_details)
                # We collect all known keys
                all_keys = set(self.segment_trays.keys()) | set(self.segment_details.keys()) | set(self.segment_label_config.keys()) | set(self.segment_label_visibility.keys())
                
                for k in all_keys:
                    k_str = self._segment_key_to_str(k)
                    seg_data = {}
                    
                    if k in self.segment_trays:
                        seg_data["trays"] = [t.to_dict() for t in self.segment_trays[k]]
                    
                    if k in self.segment_details:
                        seg_data["notes"] = self.segment_details[k]
                        
                    if k in self.segment_label_config:
                        seg_data["labels_config"] = list(self.segment_label_config[k])
                        
                    if k in self.segment_label_visibility:
                        seg_data["visible"] = self.segment_label_visibility[k]
                        
                    state["segments"][k_str] = seg_data
                    
                zf.writestr("project.json", json.dumps(state, indent=2))
                
            self.lbl_status.setText(f"Progetto salvato: {path}")
            
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Errore Salvataggio", f"Errore: {e}")

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Apri Progetto", "", "Cable Project (*.cvp)")
        if not path: return
        
        self.reset_application_state()
        self.current_project_path = path
        self.setWindowTitle(f"CableRouteCAD - {os.path.basename(path)}")
        
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                # 1. Load DXF
                if "drawing.dxf" in zf.namelist():
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                        tmp.write(zf.read("drawing.dxf"))
                        tmp.close()
                        self.load_dxf(tmp.name)
                        os.unlink(tmp.name)
                else:
                     # If no DXF, ensure groups exist (reset_application_state cleared them)
                     self.nodes_group = self.scene.createItemGroup([])
                     self.nodes_group.setZValue(100)
                     self.heatmap_group = self.scene.createItemGroup([])
                     self.heatmap_group.setZValue(5)
                
                # 2. Load Connections
                if "connections.csv" in zf.namelist():
                    csv_text = zf.read("connections.csv").decode('utf-8')
                    f = io.StringIO(csv_text)
                    reader = csv.DictReader(f)
                    self.all_connections = list(reader)
                    self.process_loaded_connections()
                    
                # 3. Load State
                if "project.json" in zf.namelist():
                    state = json.loads(zf.read("project.json"))
                    
                    # Settings
                    s = state.get("settings", {})
                    self.act_toggle_grid.setChecked(s.get("grid_visible", True))
                    self.act_toggle_nodes.setChecked(s.get("nodes_visible", False))
                    self.act_toggle_labels.setChecked(s.get("labels_visible", True))
                    self.toggle_grid(self.act_toggle_grid.isChecked())
                    self.toggle_nodes(self.act_toggle_nodes.isChecked())
                    
                    # Mixed Definitions
                    self.mixed_service_definitions = state.get("mixed_definitions", {})
                    
                    # Switchboards
                    placed_sw = state.get("switchboards", {})
                    for name, data in placed_sw.items():
                        sb_item = SwitchboardItem(name, QRectF(0,0,80,50)) # Size should use consts
                        sb_item.setPos(data["x"], data["y"])
                        if "rotation" in data: sb_item.setRotation(data["rotation"])
                        self.scene.addItem(sb_item)
                        
                        # Update list widget
                        for i in range(self.list_switchboards.count()):
                            it = self.list_switchboards.item(i)
                            if it.text() == name:
                                it.setForeground(QBrush(QColor("gray")))
                                f = it.font(); f.setStrikeOut(True); it.setFont(f)
                                
                    # Segments
                    segments = state.get("segments", {})
                    
                    # Optimization: Build map of scene lines
                    lines_map = {} 
                    for item in self.scene.items():
                        if isinstance(item, QGraphicsLineItem):
                            l = item.line()
                            p1 = routing.get_node_key(l.x1(), l.y1())
                            p2 = routing.get_node_key(l.x2(), l.y2())
                            k = tuple(sorted((p1, p2)))
                            lines_map[k] = item
                            
                    for k_str, data in segments.items():
                        k = self._str_to_segment_key(k_str)
                        if not k: continue
                        
                        if "trays" in data:
                            self.segment_trays[k] = [TrayInstance.from_dict(t) for t in data["trays"]]
                            
                        if "notes" in data:
                            self.segment_details[k] = data["notes"]
                            
                        if "labels_config" in data:
                            self.segment_label_config[k] = set(data["labels_config"])
                            
                        if "visible" in data:
                            self.segment_label_visibility[k] = data["visible"]
                            
                        # Restore Label
                        if k in lines_map:
                            txt_parts = []
                            if k in self.segment_trays:
                                trays = self.segment_trays[k]
                                if trays: txt_parts.append("\n".join([f"- {t.name} [{t.service}]" for t in trays]))
                            if k in self.segment_details and self.segment_details[k]:
                                txt_parts.append(self.segment_details[k])
                            
                            if txt_parts:
                                self.update_segment_label(k, lines_map[k].line(), "\n".join(txt_parts))
                                
            # Force update labels visibility
            self.toggle_labels(self.act_toggle_labels.isChecked())
            self.lbl_status.setText(f"Progetto caricato: {path}")

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Errore Apertura", f"Errore: {e}")

        
    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "CSV", "", "CSV (*.csv)")
        if path:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.all_connections = list(reader)
            self.process_loaded_connections()

    def populate_connections_list(self):
        self.table_connections.setRowCount(len(self.all_connections))
        columns = ["ID", "From", "To", "Type", "Formation", "Circuit", "Diameter"]
        keys = ["ID", "FROM", "TO", "Cable Type", "Cable Formation", "Circuit Type", "Diameter (mm)"]
        
        self.table_connections.setColumnCount(len(columns))
        self.table_connections.setHorizontalHeaderLabels(columns)
        
        for r, c in enumerate(self.all_connections):
            for i, key in enumerate(keys):
                val = c.get(key, "")
                if not val and key == "Type": # Fallback for compatibility
                     val = c.get("TYPE", "") 
                self.table_connections.setItem(r, i, QTableWidgetItem(str(val)))
        
        # self.table_connections.resizeColumnsToContents()

    def export_boq(self):
        if not hasattr(self, 'all_connections') or not self.all_connections:
            QMessageBox.warning(self, "Export", "Nessuna connessione caricata.")
            return

        # Aggregate data
        boq = {} # (Type, Formation) -> Total Length (m)
        detailed_boq = [] # For optional detailed sheet, but for now simple agg
        
        processed_count = 0
        for conn in self.all_connections:
            if '_route_path' in conn:
                path = conn['_route_path']
                length_px = path.length()
                # Use raw units
                length = length_px 
                
                k = (conn.get('Cable Type', 'Unknown'), conn.get('Cable Formation', 'Unknown'))
                boq[k] = boq.get(k, 0.0) + length
                processed_count += 1
                
        if processed_count == 0:
            QMessageBox.warning(self, "Export", "Nessun percorso calcolato. Esegui prima il routing.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Salva Computo", "computo.csv", "CSV (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Cable Type", "Formation", "Total Length (units)"])
                QMessageBox.information(self, "Export", f"Computo esportato con successo.\n{processed_count} cavi inclusi.")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante l'export: {e}")


    def update_segment_label(self, key, line, text):
        # Remove old if exists
        if key in self.segment_labels:
            item = self.segment_labels[key]
            if item.scene() == self.scene:
                self.scene.removeItem(item)
            del self.segment_labels[key]
            
        # Create new
        lbl = QGraphicsTextItem(text)
        lbl.setDefaultTextColor(QColor("blue"))
        font = QFont("Arial", 8)
        lbl.setFont(font)
        
        # Make movable
        lbl.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        lbl.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        # Position at center with Offset
        center = line.pointAt(0.5)
        rect = lbl.boundingRect()
        
        # Calculate perpendicular offset
        angle = line.angle() * math.pi / 180.0
        # QLineF angle is 0..360.
        # Normal vector (90 deg rotation)
        # angle implies direction. Perpendicular is +90 deg
        offset_angle = angle + math.pi / 2
        
        offset_dist = 15.0
        off_x = offset_dist * math.cos(offset_angle)
        off_y = -offset_dist * math.sin(offset_angle) # Y is inverted in Qt Scene normally? 
        # Actually QLineF angle() is mathematical (CCW from X axis)? 
        # Qt Y grows downwards. QLineF.angle() returns 0 for vector (1,0).
        # For vector (1, -1) (up-right), angle is 315 or 45?
        # Let's rely on standard trig.
        
        # Adjust for Y-down coordinate system if needed, but let's try standard math first.
        # If I want "above" the line visually...
        
        lbl.setPos(center.x() + off_x - rect.width()/2, center.y() + off_y - rect.height()/2)
        lbl.setZValue(150) # On top of everything
        
        # Visibility (Global AND Individual)
        if key not in self.segment_label_visibility:
             self.segment_label_visibility[key] = True # Default True
             
        global_vis = self.act_toggle_labels.isChecked()
        indiv_vis = self.segment_label_visibility[key]
        lbl.setVisible(global_vis and indiv_vis)
        
        self.scene.addItem(lbl)
        self.segment_labels[key] = lbl

