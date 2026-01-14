from PyQt6.QtWidgets import (QDialog, QTableWidget, QHeaderView, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QAbstractItemView, QWidget, QCheckBox, QTableWidgetItem, QDialogButtonBox, QMessageBox)
from PyQt6.QtCore import Qt

class MixedServiceBuilderDialog(QDialog):
    def __init__(self, available_services, initial_name="", initial_included=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Definizione Servizio Misto")
        self.resize(500, 600)
        self.result_data = None
        self.percentages = {} 
        
        # Initialize table_details EARLY to avoid crash on signal trigger
        self.table_details = QTableWidget(0, 2)
        self.table_details.setHorizontalHeaderLabels(["Servizio", "% Spazio"])
        self.table_details.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_details.cellChanged.connect(self.on_details_cell_changed)
        
        # Parse initial_included
        initial_set = set()
        if initial_included:
            for item in initial_included:
                if isinstance(item, dict):
                    name = item.get('name')
                    pct = item.get('percent', 0)
                    initial_set.add(name)
                    self.percentages[name] = pct
                else:
                    initial_set.add(item)
                    self.percentages[item] = 0
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Nome Servizio (es. Mixed Power):"))
        self.txt_name = QLineEdit(initial_name if initial_name else "Mixed 1")
        layout.addWidget(self.txt_name)
        
        # --- Selection Table ---
        layout.addWidget(QLabel("1. Seleziona Tipologie:"))
        
        tools_layout = QHBoxLayout()
        btn_all = QPushButton("Seleziona Tutto")
        btn_none = QPushButton("Deseleziona Tutto")
        btn_all.clicked.connect(self.select_all)
        btn_none.clicked.connect(self.select_none)
        tools_layout.addWidget(btn_all)
        tools_layout.addWidget(btn_none)
        layout.addLayout(tools_layout)
        
        self.table_selection = QTableWidget(0, 2)
        self.table_selection.setHorizontalHeaderLabels(["Includi", "Tipologia"])
        self.table_selection.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_selection.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_selection.verticalHeader().setVisible(False)
        self.table_selection.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_selection.setAlternatingRowColors(True)
        self.table_selection.cellClicked.connect(self.on_selection_cell_clicked)
        
        if available_services:
            self.table_selection.setRowCount(len(available_services))
            for i, s in enumerate(available_services):
                # Widget Checkbox
                container = QWidget()
                hlo = QHBoxLayout(container)
                hlo.setContentsMargins(0,0,0,0)
                hlo.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cb = QCheckBox()
                cb.setChecked(s in initial_set)
                cb.stateChanged.connect(lambda _: self.update_details_table())
                hlo.addWidget(cb)
                self.table_selection.setCellWidget(i, 0, container)
                
                # Name Item
                name_item = QTableWidgetItem(s)
                name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table_selection.setItem(i, 1, name_item)
                
        layout.addWidget(self.table_selection)
        
        # --- Table Details (Add to layout) ---
        layout.addWidget(QLabel("2. Dettagli Distribuzione (%):"))
        # self.table_details was created early
        layout.addWidget(self.table_details)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept_data)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        # Initial Build
        self.update_details_table()
        
    def _get_checkbox(self, row):
        widget = self.table_selection.cellWidget(row, 0)
        if widget:
            return widget.findChild(QCheckBox)
        return None

    def on_selection_cell_clicked(self, row, col):
        # Allow toggling check by clicking name (col 1)
        if col == 1:
            cb = self._get_checkbox(row)
            if cb:
                cb.setChecked(not cb.isChecked())

    def select_all(self):
        self.table_details.blockSignals(True)
        for i in range(self.table_selection.rowCount()):
            cb = self._get_checkbox(i)
            if cb: cb.setChecked(True)
        self.table_details.blockSignals(False)
        self.update_details_table()

    def select_none(self):
        self.table_details.blockSignals(True)
        for i in range(self.table_selection.rowCount()):
            cb = self._get_checkbox(i)
            if cb: cb.setChecked(False)
        self.table_details.blockSignals(False)
        self.update_details_table()
            
    def update_details_table(self):
        self.table_details.blockSignals(True)
        
        checked_items = []
        for i in range(self.table_selection.rowCount()):
            cb = self._get_checkbox(i)
            if cb and cb.isChecked():
                name = self.table_selection.item(i, 1).text()
                checked_items.append(name)
        
        self.table_details.setRowCount(len(checked_items))
        
        for i, name in enumerate(checked_items):
            # Name Col
            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable) 
            self.table_details.setItem(i, 0, name_item)
            
            # Percent Col
            val = self.percentages.get(name, 0)
            pct_item = QTableWidgetItem(str(val))
            self.table_details.setItem(i, 1, pct_item)
            
        self.table_details.blockSignals(False)

    def on_details_cell_changed(self, row, col):
        if col == 1:
            name_item = self.table_details.item(row, 0)
            val_item = self.table_details.item(row, 1)
            if name_item and val_item:
                try:
                    val = float(val_item.text())
                    self.percentages[name_item.text()] = val
                except ValueError:
                    pass 

    def accept_data(self):
        name = self.txt_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Attenzione", "Inserisci un nome per il servizio.")
            return
            
        # Collect Data
        included = []
        rows = self.table_details.rowCount()
        for i in range(rows):
            s_name = self.table_details.item(i, 0).text()
            s_val_text = self.table_details.item(i, 1).text()
            try:
                s_val = float(s_val_text)
            except:
                s_val = 0
            
            included.append({'name': s_name, 'percent': s_val})
        
        if not included:
            QMessageBox.warning(self, "Attenzione", "Seleziona almeno una tipologia da includere.")
            return

        self.result_data = (name, included)
        self.accept()
