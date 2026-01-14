from PyQt6.QtWidgets import (QTableWidget, QStyledItemDelegate, QDialog, QVBoxLayout, QLineEdit, QListWidget, QFrame, QListWidgetItem, QCheckBox, QDialogButtonBox, QHeaderView, QToolButton, QStyle, QAbstractItemView, QTableWidgetItem, QMenu)
from PyQt6.QtCore import Qt, QSize, QPointF, pyqtSignal, QRectF
from PyQt6.QtGui import QColor, QBrush, QIcon

class NoFocusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if option.state & QStyle.StateFlag.State_HasFocus:
            option.state = option.state & ~QStyle.StateFlag.State_HasFocus
        super().paint(painter, option, index)

class FilterDialog(QDialog):
    def __init__(self, values, current_filter, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(4, 4, 4, 4)
        
        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("Cerca...")
        self.layout().addWidget(self.search)
        
        # List
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame) # Rimuovi bordo per look pulito
        self.layout().addWidget(self.list_widget)
        
        # Select All Item
        self.item_all = QListWidgetItem()
        self.list_widget.addItem(self.item_all)
        self.chk_all = QCheckBox("(Seleziona Tutto)")
        self.list_widget.setItemWidget(self.item_all, self.chk_all)
        
        self.rows = [] # (item, checkbox_widget, value_text)
        sorted_vals = sorted(list(values))
        
        # Check logic
        all_included = True
        
        for val in sorted_vals:
            val_str = str(val)
            item = QListWidgetItem()
            self.list_widget.addItem(item)
            
            chk = QCheckBox(val_str)
            checked = True
            if current_filter is not None:
                checked = val in current_filter
                if not checked: all_included = False
            
            chk.setChecked(checked)
            self.list_widget.setItemWidget(item, chk)
            self.rows.append((item, chk, val_str))
            
        self.chk_all.setChecked(all_included)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        self.layout().addWidget(btns)
        
        # Connections
        self.search.textChanged.connect(self.on_search)
        self.chk_all.stateChanged.connect(self.on_all_changed)
        
        self.resize(200, 300)

    def on_all_changed(self, state):
        # Apply to all VISIBLE items
        is_checked = (state == 2) # Qt.CheckState.Checked is 2
        for item, chk, val in self.rows:
            if not item.isHidden():
                chk.blockSignals(True)
                chk.setChecked(is_checked)
                chk.blockSignals(False)

    def on_search(self, text):
        text = text.lower()
        for item, chk, val in self.rows:
            visible = text in val.lower()
            item.setHidden(not visible)

    def get_selected(self):
        # If all selected (checkboxes), return None
        # Verify real state
        selected = set()
        all_checked = True
        
        for item, chk, val in self.rows:
            if chk.isChecked():
                selected.add(val)
            else:
                all_checked = False
        
        if all_checked and not self.search.text():
             return None
        return selected

class ExcelFilterHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setSectionsClickable(True)
        self.setSortIndicatorShown(True)
        self.setSectionsMovable(True)
        self._filters = {} 
        self._buttons = {} # logicalIndex -> QToolButton

        self.sectionResized.connect(self.adjust_positions)
        self.sectionMoved.connect(self.adjust_positions)
        self.geometriesChanged.connect(self.adjust_positions)
        
    def showEvent(self, event):
        # Connetti allo scroll della tabella genitore per aggiornare posizioni
        if self.parent() and hasattr(self.parent(), "horizontalScrollBar"):
            self.parent().horizontalScrollBar().valueChanged.connect(self.adjust_positions)
        self.adjust_positions()
        super().showEvent(event)
        
    def adjust_positions(self):
        # Aggiorna posizione dei pulsanti filtro
        count = self.count()
        for i in range(count):
            if i not in self._buttons:
                btn = QToolButton(self)
                # Usa Icona Standard invece di testo per evitare confusione
                btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
                btn.setCursor(Qt.CursorShape.ArrowCursor)
                # Stile minimale trasparent
                btn.setStyleSheet("QToolButton { border: none; background: transparent; } "
                                  "QToolButton:hover { background: #e0e0e0; border-radius: 3px; }")
                btn.clicked.connect(lambda checked, col=i: self.show_filter_menu(col))
                self._buttons[i] = btn
            
            btn = self._buttons[i]
            
            # Calcola geometria relativa all'header
            x = self.sectionViewportPosition(i)
            w = self.sectionSize(i)
            h = self.height()
            
            # Nascondi se width troppo piccola o fuori schermo
            if w < 20: 
                btn.hide()
                continue
                
            # Posiziona a destra
            btn_w = 16
            btn_h = 16
            margin_right = 8 # Aumentato margine per lasciare spazio alla maniglia di ridimensionamento columns
            
            # Centra verticalmente
            y = (h - btn_h) // 2
            
            # Se la colonna è nascosta o fuori visuale logica (non solo scroll)
            if self.isSectionHidden(i):
                 btn.hide()
                 continue

            btn.setGeometry(x + w - btn_w - margin_right, y, btn_w, btn_h)
            btn.show()
            
            # Colora se attivo
            is_active = i in self._filters and self._filters[i] is not None
            if is_active:
                btn.setStyleSheet("QToolButton { border: none; background: transparent; color: blue; font-weight: bold; font-size: 10px; }")
            else:
                btn.setStyleSheet("QToolButton { border: none; background: transparent; color: gray; font-size: 10px; } "
                                  "QToolButton:hover { color: black; background: #e0e0e0; border-radius: 3px; }")

    def show_filter_menu(self, col):
        table = self.parent()
        
        # Raccogli valori unici
        values = set()
        for r in range(table.rowCount()):
            item = table.item(r, col)
            if item:
                values.add(item.text())
        
        current_filter = self._filters.get(col)
        
        # Usa il Dialog
        dlg = FilterDialog(values, current_filter, self)
        
        # Posiziona sotto il bottone
        btn = self._buttons[col]
        global_pos = btn.mapToGlobal(QPointF(0, btn.height()).toPoint())
        dlg.move(global_pos)
        
        if dlg.exec():
            # Applica
            selected = dlg.get_selected()
            self._filters[col] = selected
            self.apply_filters()
            self.adjust_positions()

    def apply_filters(self):
        table = self.parent()
        for r in range(table.rowCount()):
            visible = True
            for col, allowed in self._filters.items():
                if allowed is None: continue
                item = table.item(r, col)
                val = item.text() if item else ""
                if val not in allowed:
                    visible = False
                    break
            table.setRowHidden(r, not visible)


class ReorderableTableWidget(QTableWidget):
    row_order_changed = pyqtSignal()

    def __init__(self, *args, enable_filter=True, **kwargs):
        super().__init__(*args, **kwargs)
        
        if enable_filter:
            # Header Excel Style
            self.excel_header = ExcelFilterHeader(self)
            self.setHorizontalHeader(self.excel_header)
        else:
            # Standard Header
            self.horizontalHeader().setSectionsMovable(True)
            
        self.setSortingEnabled(True)
        
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # Usa DragDrop generico invece di InternalMove per evitare logiche "Magic" di rimozione
        self.setDragDropMode(QTableWidget.DragDropMode.DragDrop)
        # Imposta CopyAction come default per evitare che la vista cancelli la riga sorgente
        # (La cancellazione è già gestita manualmente in dropEvent)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        
        # Rimuove il "rettangolino" di focus sulla cella singola
        self.setItemDelegate(NoFocusDelegate(self))

    def dropEvent(self, event):
        if event.source() != self:
            return

        pos = event.position().toPoint()
        drop_row = self.indexAt(pos).row()
        
        if drop_row == -1:
            drop_row = self.rowCount()
        else:
            # Se siamo sulla metà inferiore della riga, inseriamo dopo
            rect = self.visualItemRect(self.item(drop_row, 0))
            if rect.isValid(): # Check valid
                if pos.y() > rect.center().y():
                    drop_row += 1

        source_rows = sorted(set(item.row() for item in self.selectedItems()))
        if not source_rows: return
        source_row = source_rows[0]
        
        if source_row == drop_row or drop_row == source_row + 1:
            event.accept()
            return
            
        # STRATEGIA RICOSTRUZIONE TOTALE (Safety First)
        # Catturiamo tutti i dati per evitare conflitti interni di QTableWidget
        all_rows_data = []
        for r in range(self.rowCount()):
            row_cols = []
            for c in range(self.columnCount()):
                # Save Widget if exists (e.g. Checkbox)
                widget = self.cellWidget(r, c)
                w_obj = None
                if widget:
                    widget.setParent(None) # Detach ownership
                    w_obj = widget
                
                it = self.item(r, c)
                if it:
                    d = {
                        'text': it.text(),
                        'flags': it.flags(),
                        'user_data': it.data(Qt.ItemDataRole.UserRole),
                        'widget': w_obj
                    }
                    row_cols.append(d)
                else:
                    if w_obj:
                         d = {'text': "", 'flags': Qt.ItemFlag.NoItemFlags, 'user_data': None, 'widget': w_obj}
                         row_cols.append(d)
                    else:
                         row_cols.append(None)
            all_rows_data.append(row_cols)
            
        # Manipolazione Lista Python (Sicura)
        row_to_move = all_rows_data.pop(source_row)
        
        if source_row < drop_row:
            drop_row -= 1
            
        drop_row = max(0, min(drop_row, len(all_rows_data)))
        all_rows_data.insert(drop_row, row_to_move)
        
        # Ricostruzione Tabella
        self.setUpdatesEnabled(False)
        sorting_was_enabled = self.isSortingEnabled()
        self.setSortingEnabled(False)
        
        self.setRowCount(0)
        self.setRowCount(len(all_rows_data))
        
        for r, row_data in enumerate(all_rows_data):
            for c, d in enumerate(row_data):
                if d:
                    new_it = QTableWidgetItem(d['text'])
                    new_it.setFlags(d['flags'])
                    if d['user_data'] is not None:
                         new_it.setData(Qt.ItemDataRole.UserRole, d['user_data'])
                    self.setItem(r, c, new_it)
                    
                    if d.get('widget'):
                        self.setCellWidget(r, c, d['widget'])
                    
        self.setSortingEnabled(sorting_was_enabled)
        self.setUpdatesEnabled(True)
        self.selectRow(drop_row)
        
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()
        
        # Riapplica filtri se presenti
        if hasattr(self, "excel_header"):
            self.excel_header.apply_filters()
        
        # Aggiorna posizioni bottoni header se necessario
        if hasattr(self, "excel_header"):
            self.excel_header.adjust_positions()
            
        self.row_order_changed.emit()
