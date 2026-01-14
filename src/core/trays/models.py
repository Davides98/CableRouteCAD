import uuid

class TrayInstance:
    def __init__(self, name, capacity, service="Power", width=100, height=60, included_services=None, max_fill_percent=80.0):
        self.id = str(uuid.uuid4())
        self.name = name          # e.g., "100x60 mm"
        self.capacity = capacity  # mm2
        self.service = service    # "Power", "Data", "Control" or "Mixed X"
        self.width = width        # mm
        self.height = height      # mm
        self.included_services = included_services or [] # List of services for Mixed types
        self.max_fill_percent = float(max_fill_percent) # Default 80%
        self.current_load = 0     # mm2, dynamic load
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "capacity": self.capacity,
            "service": self.service,
            "width": self.width,
            "height": self.height,
            "included_services": self.included_services,
            "max_fill_percent": self.max_fill_percent
        }

    @staticmethod
    def from_dict(data):
        t = TrayInstance(
            data.get("name", "Unknown"), 
            data.get("capacity", 0), 
            data.get("service", "Power"),
            data.get("width", 100),
            data.get("height", 60),
            data.get("included_services", []),
            data.get("max_fill_percent", 80.0)
        )
        t.id = data.get("id", str(uuid.uuid4()))
        return t

class TrayCatalog:
    """Manages standard tray sizes."""
    STANDARD_TRAYS = {
        "100x50 mm":  {"capacity": 5000,  "width": 100, "height": 50},
        "150x60 mm":  {"capacity": 9000,  "width": 150, "height": 60},
        "200x60 mm":  {"capacity": 12000, "width": 200, "height": 60},
        "300x60 mm":  {"capacity": 18000, "width": 300, "height": 60},
        "400x100 mm": {"capacity": 40000, "width": 400, "height": 100},
        "Tubo Ø20":   {"capacity": 314,   "width": 20,  "height": 20},
        "Tubo Ø25":   {"capacity": 490,   "width": 25,  "height": 25},
        "Tubo Ø32":   {"capacity": 804,   "width": 32,  "height": 32}
    }
    
    _loaded = False

    @staticmethod
    def load_from_csv(filepath="data/catalogo.csv"):
        import csv
        import os
        
        if not os.path.exists(filepath):
            return

        try:
            new_trays = {}
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';') # Semicolon common in IT
                # Check for comma if semicolon fails? 
                # Let's assume semicolon or comma auto-detection if we use sniff?
                # Simpler: Try to read.
                
                # Normalize headers: Type/Name, Capacity, Width, Height
                for row in reader:
                    # Clean keys
                    r = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                    
                    # Identificatori possibili per il Nome
                    name = r.get('type') or r.get('tipo') or r.get('name') or r.get('nome')
                    if not name: continue
                    
                    try:
                        cap = float(r.get('capacity', r.get('capacita', r.get('capacità', 0))))
                        w = float(r.get('width', r.get('larghezza', 0)))
                        h = float(r.get('height', r.get('altezza', 0)))
                        
                        new_trays[name] = {"capacity": cap, "width": w, "height": h}
                    except ValueError:
                        continue
            
            if new_trays:
                TrayCatalog.STANDARD_TRAYS = new_trays
                TrayCatalog._loaded = True
                print(f"Loaded {len(new_trays)} trays from CSV.")
                
        except Exception as e:
            print(f"Error loading catalog: {e}")

    @staticmethod
    def create_instance(name, service="Power"):
        if not TrayCatalog._loaded:
             TrayCatalog.load_from_csv()
             
        info = TrayCatalog.STANDARD_TRAYS.get(name, {"capacity": 5000, "width": 100, "height": 50})
        return TrayInstance(name, info["capacity"], service, info["width"], info["height"], max_fill_percent=80.0)
