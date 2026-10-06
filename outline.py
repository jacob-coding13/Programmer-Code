from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem
)

from PySide6.QtCore import Signal

from parser import PythonParser
from language_manager import LanguageManager

class Outline(QTreeWidget):

    item_clicked = Signal(int)

    def __init__(self, settings):
        super().__init__()

        self.settings = settings
        self.lang = LanguageManager(self.settings.language)
        self.setHeaderLabel(self.lang.get("outline"))

        self.parser = PythonParser()

        self.itemClicked.connect(
            self.clicked_item
        )

    def reload_language(self):
        self.lang = LanguageManager(self.settings.language)
        self.setHeaderLabel(self.lang.get("outline"))

    def load_file(self, path):

        self.clear()

        try:
            items = self.parser.parse(path)

        except Exception:
            return

        for item in items:

            if item["type"] == "class":
                parent = QTreeWidgetItem([f" {item['name']}"])
                parent.setData(0, 1, item["line"])
                self.addTopLevelItem(parent)

                for child in item["children"]:
                    child_item = QTreeWidgetItem(
                        [f"ƒ {child['name']}"]
                    )
                    child_item.setData(0, 1, child["line"])
                    parent.addChild(child_item)

            elif item["type"] == "function":
                function = QTreeWidgetItem(
                    [f"ƒ {item['name']}"]
                )
                function.setData(0, 1, item["line"])
                self.addTopLevelItem(function)

    def clicked_item(self, item, column):

        line = item.data(
            0,
            1
        )

        if line:

            self.item_clicked.emit(line)