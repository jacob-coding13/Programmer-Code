from pathlib import Path
from themes import THEMES

def get_app_style(settings):
    theme_name = getattr(settings, "theme", "Dark")
    theme = THEMES.get(theme_name, THEMES.get("Dark", {}))

    bg = theme.get("background", "#1e1e1e")
    fg = theme.get("foreground", "#d4d4d4")
    line = theme.get("line", "#2d2d30")
    accent = theme.get("accent", "#0e639c")

    try:
        base_font_size = float(getattr(settings, "ui_font_size", 10))
        scale = float(getattr(settings, "ui_scale", 1.0))
        font_size = max(6, round(base_font_size * scale))
    except (ValueError, TypeError):
        font_size = 10

    font_family = getattr(settings, "ui_font_family", "Segoe UI")

    check_icon = (
        Path(__file__).parent / "resources" / "check.svg"
    ).as_posix()

    return f"""
    /* Nutzen von QApplication oder spezifischen Oberklassen statt QWidget */
    QWidget#MainWindow, QDialog, QMainWindow {{
        background-color: {bg};
        color: {fg};
    }}

    * {{
        font-family: "{font_family}";
        font-size: {font_size}pt;
        color: {fg};
    }}

    QPlainTextEdit {{
        background-color: transparent;
        color: inherit;
    }}

    QListWidget {{
        background-color: {bg};
        color: {fg};
        border: 1px solid {line};
    }}

    QMenuBar, QMenu, QToolBar {{
        background-color: {line};
        color: {fg};
        border: none;
    }}

    QMenu::item:selected {{
        background-color: {accent};
    }}

    QPushButton {{
        background-color: {line};
        color: {fg};
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 5px 10px;
    }}

    QPushButton:hover {{
        background-color: {accent};
    }}

    QLineEdit, QSpinBox, QComboBox {{
        background-color: {line};
        color: {fg};
        border: 1px solid {line};
        border-radius: 3px;
        padding: 3px;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {fg};
        border-radius: 3px;
        background: transparent;
    }}

    QCheckBox::indicator:checked {{
        image: url("{check_icon}");
        border: 1px solid {accent};
        background-color: {accent};
    }}

    QCheckBox::indicator:unchecked {{
        border: 1px solid {fg};
        background-color: {line};
    }}
    """