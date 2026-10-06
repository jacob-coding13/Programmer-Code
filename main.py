import sys
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from settings import Settings
from theme_manager import get_app_style

def main():
    app = QApplication(sys.argv)

    settings = Settings()

    font = QFont(
        settings.ui_font_family,
        int(settings.ui_font_size)
    )
    app.setFont(font)

    app.setStyleSheet(get_app_style(settings))

    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()