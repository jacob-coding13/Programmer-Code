from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QMouseEvent


class LineNumberArea(QWidget):

    def __init__(self, editor):
        super().__init__(editor)

        self.editor = editor

    def sizeHint(self):
        return QSize(
            self.editor.line_number_area_width(),
            0
        )

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.LeftButton:
            return

        editor = self.editor
        y = event.position().y()

        block = editor.firstVisibleBlock()

        top = editor.blockBoundingGeometry(
            block
        ).translated(
            editor.contentOffset()
        ).top()

        line_height = editor.fontMetrics().height()

        while block.isValid():

            height = editor.blockBoundingRect(block).height()
            bottom = top + height

            center_y = top + line_height * 1.75

            # Nur prüfen, ob der Klick beim Dreieck liegt
            if abs(y - center_y) <= line_height * 0.5:

                line = block.blockNumber() + 1

                for start, end in editor.folding.folds:
                    if start == line:
                        editor.toggle_fold(start)
                        return

                return

            top = bottom
            block = block.next()