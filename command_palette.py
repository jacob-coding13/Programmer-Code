from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget

class CommandPalette(QDialog):

    def __init__(self, commands, lang):
        super().__init__()
        self.lang = lang
        self.setWindowTitle(self.lang.get("command_palette"))
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        self.input = QLineEdit()
        self.input.setPlaceholderText(self.lang.get("search_commands"))
        layout.addWidget(self.input)

        self.list = QListWidget()
        layout.addWidget(self.list)

        for cmd in commands:
            self.list.addItem(cmd)

        self.input.textChanged.connect(self.filter)

    def filter(self, text):
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(text.lower() not in item.text().lower())