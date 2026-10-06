from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout

from language_manager import LanguageManager

class FindDialog(QDialog):

    def __init__(self, editor, settings):
        super().__init__(editor)

        self.editor = editor
        self.settings = settings
        self.lang = LanguageManager(self.settings.language)

        self.setWindowTitle(self.lang.get("find"))
        self.resize(300, 100)

        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText(self.lang.get("search"))

        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            self.search.setText(cursor.selectedText())
            self.search.selectAll()

        button = QPushButton(self.lang.get("find_next"))

        layout.addWidget(self.search)
        layout.addWidget(button)

        button.clicked.connect(self.find_next)
        self.search.returnPressed.connect(self.find_next)

    def find_next(self):
        text = self.search.text()
        if not text:
            return

        found = self.editor.find(text)

        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(text)