from PySide6.QtWidgets import QPushButton, QColorDialog
from PySide6.QtGui import QColor

class ColorButton(QPushButton):

    def __init__(self, color="#ffffff"):
        super().__init__()

        self.color = color

        self.clicked.connect(
            self.choose_color
        )

        self.update_button()

    def choose_color(self):

        color = QColorDialog.getColor(
            QColor(self.color)
        )

        if color.isValid():

            self.color = color.name()

            self.update_button()

    def update_button(self):

        self.setText(
            self.color
        )

        self.setStyleSheet(
            f"""
            QPushButton {{
                background:{self.color};
                color:white;
                padding:6px;
                border-radius:4px;
            }}
            """
        )

    def value(self):

        return self.color

    def set_value(self, color):

        self.color = color

        self.update_button()