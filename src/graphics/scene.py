from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QBrush, QPen

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
