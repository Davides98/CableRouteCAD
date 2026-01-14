from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsItem, QGraphicsTextItem, QGraphicsLineItem, QGraphicsEllipseItem
from PyQt6.QtGui import QBrush, QColor, QPen, QPainterPath, QPainterPathStroker
from PyQt6.QtCore import QLineF, QPointF, Qt
from src.config import STYLESHEET

class AnalysisPointItem(QGraphicsEllipseItem):
    def __init__(self, x, y, radius=6.0, parent=None):
        super().__init__(x - radius, y - radius, radius * 2, radius * 2, parent)
        self.setPen(QPen(QColor("darkred"), 2))
        self.setBrush(QBrush(QColor("red")))
        self.setZValue(200) # Way above nodes
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setToolTip("Punto di Analisi")


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
    def __init__(self, *args, tray_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_tray_instance(tray_instance)
        
    def set_tray_instance(self, tray_instance):
        self.tray_instance = tray_instance
        # tray_instance can be a single object OR a list of objects now
        if self.tray_instance:
             self.setData(Qt.ItemDataRole.UserRole, self.tray_instance)
        else:
             self.setData(Qt.ItemDataRole.UserRole, None)
        self.update_style()
        
    def update_style(self):
        service = "Power"
        if self.tray_instance:
            if isinstance(self.tray_instance, list):
                # If list, determine composite color
                # If all same, usage that. If diff, Mixed.
                srvs = set(getattr(t, 'service', 'Power') for t in self.tray_instance)
                if len(srvs) == 1:
                    service = list(srvs)[0]
                else:
                    service = "Mixed"
            else:
                service = getattr(self.tray_instance, 'service', "Power")
        
        color = QColor("black") # Default or Undefined
        width = 2
        
        if service == "Power": 
            color = QColor("red")
        elif service == "Data": 
            color = QColor("blue")
        elif service.startswith("Mixed"): 
            color = QColor("purple")
        
        pen = QPen(color, width)
        self.setPen(pen)

    def shape(self):
        path = super().shape()
        stroker = QPainterPathStroker()
        stroker.setWidth(10) # 10 units wide hit area
        return stroker.createStroke(path)

