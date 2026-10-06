from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem

class CompletionPopup(QListWidget):

    completed = Signal(str)

    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.ToolTip)

        self.setFocusPolicy(Qt.NoFocus)

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.setVerticalScrollMode(
            QListWidget.ScrollPerPixel
        )

        self.setMaximumHeight(250)
        self.setMinimumWidth(260)

        self.itemClicked.connect(
            self.on_item_clicked
        )

        self.setStyleSheet("""
            QListWidget {
                background: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                font-family: Consolas;
                font-size: 11pt;
                outline: none;
            }

            QListWidget::item {
                height: 24px;
                padding-left: 8px;
            }

            QListWidget::item:selected {
                background: #094771;
                color: white;
            }
        """)

    def show_items(self, items, rect, editor):

        if not items:
            self.hide()
            return

        current = [
            self.item(i).text()
            for i in range(self.count())
        ]

        if current != items:

            self.setUpdatesEnabled(False)

            self.clear()

            for word in items:
                self.addItem(QListWidgetItem(word))

            self.setUpdatesEnabled(True)

        self.setCurrentRow(0)

        pos = editor.mapToGlobal(
            rect.bottomLeft()
        )

        self.move(
            pos.x(),
            pos.y() + 2
        )

        height = min(
            self.count() * 24 + 4,
            250
        )

        self.resize(
            260,
            height
        )

        if not self.isVisible():
            self.show()

    def move_up(self):

        row = self.currentRow()

        if row > 0:
            self.setCurrentRow(row - 1)

    def move_down(self):

        row = self.currentRow()

        if row < self.count() - 1:
            self.setCurrentRow(row + 1)

    def complete_current(self):

        item = self.currentItem()

        if item is None:
            return None

        self.hide()

        return item.text()

    def current_word(self):

        item = self.currentItem()

        if item is None:
            return ""

        return item.text()

    def on_item_clicked(self, item):

        self.completed.emit(item.text())
        self.hide()