from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QFileDialog, QDialogButtonBox, QLabel, QHBoxLayout

class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuovo Progetto")
        self.resize(500, 200)
        
        self.dxf_path = None
        self.csv_path = None
        
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        # DXF Selection
        self.txt_dxf = QLineEdit()
        self.txt_dxf.setReadOnly(True)
        self.btn_dxf = QPushButton("Sfoglia...")
        self.btn_dxf.clicked.connect(self.browse_dxf)
        
        row_dxf = QHBoxLayout()
        row_dxf.addWidget(self.txt_dxf)
        row_dxf.addWidget(self.btn_dxf)
        form_layout.addRow("File DXF:", row_dxf)
        
        # CSV Selection
        self.txt_csv = QLineEdit()
        self.txt_csv.setReadOnly(True)
        self.btn_csv = QPushButton("Sfoglia...")
        self.btn_csv.clicked.connect(self.browse_csv)
        
        row_csv = QHBoxLayout()
        row_csv.addWidget(self.txt_csv)
        row_csv.addWidget(self.btn_csv)
        form_layout.addRow("Lista Cavi (CSV):", row_csv)
        
        # Save Location
        self.txt_save = QLineEdit()
        self.txt_save.setReadOnly(True)
        self.btn_save = QPushButton("Sfoglia...")
        self.btn_save.clicked.connect(self.browse_save)
        
        row_save = QHBoxLayout()
        row_save.addWidget(self.txt_save)
        row_save.addWidget(self.btn_save)
        form_layout.addRow("Salva Progetto in:", row_save)
        
        layout.addLayout(form_layout)
        
        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.setLayout(layout)
        
    def browse_dxf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona Layout DXF", "", "DXF Files (*.dxf)")
        if path:
            self.dxf_path = path
            self.txt_dxf.setText(path)
            
    def browse_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleziona Lista Cavi CSV", "", "CSV Files (*.csv)")
        if path:
            self.csv_path = path
            self.txt_csv.setText(path)

    def browse_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salva Progetto Come...", "", "Cable Project (*.cvp);;Tutti i file (*.*)")
        if path:
            if not path.endswith(".cvp"):
                path += ".cvp"
            self.save_path = path
            self.txt_save.setText(path)
            
    def get_data(self):
        return self.txt_dxf.text(), self.txt_csv.text(), self.txt_save.text()
