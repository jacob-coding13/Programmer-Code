import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

class SearchDialog(QDialog):

    def __init__(self, teacher, lang, editor, parent=None):
        super().__init__(parent)
        self.teacher = teacher
        self.lang = lang
        self.editor = editor

        self.setWindowTitle(self.lang.get("search"))
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        self.input = QLineEdit()
        self.input.setPlaceholderText(self.lang.get("search"))
        layout.addWidget(self.input)

        self.results = QListWidget()
        layout.addWidget(self.results)

        self.input.textChanged.connect(self.run_search)
        self.results.itemActivated.connect(self.jump_to_line)
        self.results.itemClicked.connect(self.jump_to_line)

    def run_search(self):
        term = self.input.text().strip()
        self.results.clear()

        if not term:
            return

        text = self.teacher.search_term(term)
        if not text:
            return

        for line in text.splitlines():
            if line.strip():
                item = QListWidgetItem(line)
                self.results.addItem(item)

    def jump_to_line(self, item):
        if not self.editor:
            return

        text = item.text()
        match = re.search(r"\b(\d+)\b", text)
        if match:
            try:
                line_no = int(match.group(1))
                self.editor.jump_to_line(line_no)
                self.accept()
            except ValueError:
                pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.results.currentItem():
                self.jump_to_line(self.results.currentItem())
        else:
            super().keyPressEvent(event)