from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem

class CompletionPopup(QListWidget):

    completed = Signal(str)

    def __init__(self):
        super().__init__()

        self.hide()

        self.setWindowFlags(
            Qt.Popup | Qt.FramelessWindowHint
        )

        self.itemClicked.connect(
            self.choose
        )

    def show_items(self, words, pos):

        self.clear()

        for word in sorted(words):

            self.addItem(
                QListWidgetItem(word)
            )

        if not words:
            self.hide()
            return

        self.setCurrentRow(0)

        self.move(pos)

        self.resize(260, min(250, len(words) * 22 + 4))

        self.show()

        self.raise_()

        self.setFocus()

    def choose(self, item):

        self.completed.emit(item.text())

        self.hide()

    def keyPressEvent(self, event):

        if event.key() in (
            Qt.Key_Return,
            Qt.Key_Enter
        ):

            item = self.currentItem()

            if item:
                self.completed.emit(item.text())

            self.hide()
            return

        if event.key() == Qt.Key_Escape:
            self.hide()
            return

        super().keyPressEvent(event)