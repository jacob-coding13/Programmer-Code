from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont
from PySide6.QtWidgets import QWidget

class Minimap(QWidget):
    def __init__(self, editor=None, parent=None):
        super().__init__(parent)
        self.editor = None
        self.setFixedWidth(110)

        self.font = QFont("Consolas", 2)
        self.font.setStyleHint(QFont.Monospace)

        self.is_dragging = False

        if editor:
            self.set_editor(editor)

    def set_editor(self, editor):
        self.editor = editor
        self.editor.textChanged.connect(self.update)
        self.editor.verticalScrollBar().valueChanged.connect(self.update)

    def paintEvent(self, event):
        if not self.editor:
            return

        painter = QPainter(self)
        painter.setFont(self.font)

        bg_color = self.editor.palette().base().color()
        painter.fillRect(self.rect(), bg_color)

        doc = self.editor.document()
        if not doc:
            return

        font_metrics = painter.fontMetrics()
        line_height = max(3, font_metrics.height())

        total_lines = doc.blockCount()
        total_content_height = total_lines * line_height

        scroll_bar = self.editor.verticalScrollBar()
        max_scroll = scroll_bar.maximum()
        
        scroll_ratio = scroll_bar.value() / max_scroll if max_scroll > 0 else 0
        
        overflow = max(0, total_content_height - self.height())
        y_offset = scroll_ratio * overflow

        default_color = self.editor.palette().text().color()

        block = doc.begin()
        y = line_height - y_offset

        while block.isValid():
            if y + line_height >= 0 and y <= self.height() + line_height:
                text = block.text()
                if text:
                    layout = block.layout()
                    formats = layout.formats() if layout else []

                    if not formats:
                        painter.setPen(default_color)
                        painter.drawText(4, int(y), text)
                    else:
                        current_x = 4
                        for fmt_range in formats:
                            start = fmt_range.start
                            length = fmt_range.length
                            sub_text = text[start:start + length]

                            color = fmt_range.format.foreground().color()
                            if not color.isValid() or color.alpha() == 0:
                                color = default_color

                            painter.setPen(color)
                            painter.drawText(int(current_x), int(y), sub_text)
                            current_x += font_metrics.horizontalAdvance(sub_text)

            y += line_height
            block = block.next()

        self._draw_overlay(painter, line_height, total_content_height, y_offset, scroll_ratio)

    def _draw_overlay(self, painter, line_height, total_content_height, y_offset, scroll_ratio):
        scroll_bar = self.editor.verticalScrollBar()
        max_scroll = scroll_bar.maximum()

        visible_ratio = self.editor.height() / max(1, self.editor.height() + max_scroll)
        overlay_height = max(15.0, min(self.height(), total_content_height * visible_ratio))

        if total_content_height > self.height():
            overlay_top = scroll_ratio * (self.height() - overlay_height)
        else:
            overlay_top = (scroll_ratio * (total_content_height - overlay_height))

        overlay_rect = QRectF(0, overlay_top, self.width(), overlay_height)
        
        painter.fillRect(overlay_rect, QColor(255, 255, 255, 30))
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
        painter.drawRect(overlay_rect)

    def _scroll_editor_to_y(self, click_y):
        if not self.editor:
            return

        scroll_bar = self.editor.verticalScrollBar()
        max_scroll = scroll_bar.maximum()
        if max_scroll <= 0:
            return

        ratio = max(0.0, min(1.0, click_y / self.height()))
        scroll_bar.setValue(int(ratio * max_scroll))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self._scroll_editor_to_y(event.position().y())

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self._scroll_editor_to_y(event.position().y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False