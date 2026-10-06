from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QStackedWidget,
    QLineEdit,
    QPushButton,
    QLabel,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QDoubleSpinBox
)

from color_button import ColorButton
from language_manager import LanguageManager

class SettingsDialog(QDialog):

    def __init__(self, settings):
        super().__init__()

        self.settings = settings

        self.lang = LanguageManager(
            self.settings.language
        )

        self.setWindowTitle(
            self.lang.get("programmer_code_settings")
        )

        self.resize(
            850,
            550
        )

        self.create_ui()

        self.load_settings()

    def create_ui(self):

        main = QVBoxLayout(self)

        self.search = QLineEdit()

        self.search.setPlaceholderText(
            self.lang.get("search_settings")
        )

        main.addWidget(
            self.search
        )

        body = QHBoxLayout()

        self.categories = QListWidget()

        self.categories.addItems(
            [
                self.lang.get("language"),
                self.lang.get("editor"),
                self.lang.get("appearance"),
                self.lang.get("terminal"),
                self.lang.get("files"),
                self.lang.get("python"),
                self.lang.get("advanced")
            ]
        )

        self.categories.setFixedWidth(
            180
        )

        body.addWidget(
            self.categories
        )

        self.pages = QStackedWidget()

        self.pages.addWidget(
            self.language_page()
        )

        self.pages.addWidget(
            self.editor_page()
        )

        self.pages.addWidget(
            self.appearance_page()
        )

        self.pages.addWidget(
            self.terminal_page()
        )

        self.pages.addWidget(
            self.files_page()
        )

        self.pages.addWidget(
            self.python_page()
        )

        self.pages.addWidget(
            self.advanced_page()
        )

        body.addWidget(
            self.pages
        )

        main.addLayout(
            body
        )

        buttons = QHBoxLayout()

        buttons.addStretch()

        cancel = QPushButton(
            self.lang.get("cancel")
        )

        apply = QPushButton(
            self.lang.get("apply")
        )

        cancel.clicked.connect(
            self.reject
        )

        apply.clicked.connect(
            self.apply_settings
        )

        buttons.addWidget(
            cancel
        )

        buttons.addWidget(
            apply
        )

        main.addLayout(
            buttons
        )

        self.categories.currentRowChanged.connect(
            self.pages.setCurrentIndex
        )
        self.search.textChanged.connect(
            self.filter_settings
        )

        self.categories.setCurrentRow(
            0
        )

    def filter_settings(self, text):
        query = text.strip().casefold()
        first_match = -1

        for index in range(self.categories.count()):
            item = self.categories.item(index)
            page = self.pages.widget(index)
            labels = [item.text()]

            for widget in page.findChildren(QWidget):
                widget_text = getattr(widget, "text", None)
                if callable(widget_text):
                    labels.append(widget_text())

                if isinstance(widget, QComboBox):
                    labels.extend(
                        widget.itemText(option_index)
                        for option_index in range(widget.count())
                    )

            matches = not query or any(
                query in label.casefold() for label in labels if label
            )
            item.setHidden(not matches)

            if matches and first_match == -1:
                first_match = index

        if first_match != -1:
            self.categories.setCurrentRow(first_match)

    def language_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        title = QLabel(
            self.lang.get("language")
        )

        title.setStyleSheet(
            """
            font-size:18px;
            font-weight:bold;
            """
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            QLabel(
                self.lang.get("application_language")
            )
        )

        self.language = QComboBox()

        self.language.addItem(
            "Deutsch",
            "de"
        )

        self.language.addItem(
            "English",
            "en"
        )

        self.language.addItem(
            "Français",
            "fr"
        )

        self.language.addItem(
            "Español",
            "es"
        )

        layout.addWidget(
            self.language
        )

        layout.addStretch()

        return page

    def editor_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        title = QLabel(
            self.lang.get("editor")
        )

        title.setStyleSheet(
            """
            font-size:18px;
            font-weight:bold;
            """
        )

        layout.addWidget(title)

        self.editor_font = QComboBox()

        self.editor_font.addItems(
            [
                "Consolas",
                "Cascadia Code",
                "JetBrains Mono",
                "Fira Code",
                "Courier New"
            ]
        )

        layout.addWidget(
            QLabel(
                self.lang.get("editor_font")
            )
        )

        layout.addWidget(
            self.editor_font
        )

        self.editor_size = QSpinBox()

        self.editor_size.setRange(
            8,
            40
        )

        layout.addWidget(
            QLabel(
                self.lang.get("font_size")
            )
        )

        layout.addWidget(
            self.editor_size
        )

        self.tab_size = QSpinBox()

        self.tab_size.setRange(
            1,
            16
        )

        layout.addWidget(
            QLabel(
                self.lang.get("tab_size")
            )
        )

        layout.addWidget(
            self.tab_size
        )

        self.syntax = QCheckBox(
            self.lang.get("syntax_highlighting")
        )

        self.autocomplete = QCheckBox(
            self.lang.get("autocomplete")
        )

        self.autocomplete_parentheses = QCheckBox(
            self.lang.get("autocomplete_parentheses")
        )

        self.auto_brackets = QCheckBox(
            self.lang.get("auto_brackets")
        )

        self.highlight_current_line = QCheckBox(
            self.lang.get("highlight_current_line")
        )

        self.show_whitespace = QCheckBox(
            self.lang.get("show_whitespace")
        )

        self.word_wrap = QCheckBox(
            self.lang.get("word_wrap")
        )

        self.auto_indent = QCheckBox(
            self.lang.get("auto_indent")
        )

        self.highlight_matching_brackets = QCheckBox(
            self.lang.get("highlight_matching_brackets")
        )

        self.scroll_speed = QDoubleSpinBox()
        self.scroll_speed.setRange(0.1, 5.0)
        self.scroll_speed.setSingleStep(0.1)
        self.scroll_speed.setValue(self.settings.scroll_speed)
        self.scroll_speed.setSuffix("×")

        self.minimap = QCheckBox(
            self.lang.get("show_minimap")
        )

        layout.addWidget(
            self.syntax
        )

        layout.addWidget(
            self.autocomplete
        )

        layout.addWidget(
            self.autocomplete_parentheses
        )

        layout.addWidget(
            self.auto_brackets
        )

        layout.addWidget(
            self.highlight_current_line
        )

        layout.addWidget(
            self.show_whitespace
        )

        layout.addWidget(
            QLabel(
                self.lang.get("scroll_speed")
            )
        )

        layout.addWidget(
            self.scroll_speed
        )

        layout.addWidget(
            self.word_wrap
        )

        layout.addWidget(
            self.auto_indent
        )

        layout.addWidget(
            self.highlight_matching_brackets
        )

        layout.addWidget(
            self.minimap
        )

        layout.addStretch()

        return page

    def appearance_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        title = QLabel(
            self.lang.get("appearance")
        )

        title.setStyleSheet(
            """
            font-size:18px;
            font-weight:bold;
            """
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            QLabel(
                self.lang.get("theme")
            )
        )

        self.theme = QComboBox()

        self.theme.addItems(
            [
                "Dark",
                "Dracula",
                "Monokai",
                "Nord"
            ]
        )

        layout.addWidget(
            self.theme
        )

        layout.addWidget(
            QLabel(
                self.lang.get("ui_font")
            )
        )

        self.ui_font = QComboBox()

        self.ui_font.addItems(
            [
                "Segoe UI",
                "Arial",
                "Calibri",
                "Tahoma"
            ]
        )

        layout.addWidget(
            self.ui_font
        )

        layout.addWidget(
            QLabel(
                self.lang.get("ui_font_size")
            )
        )

        self.ui_size = QSpinBox()

        self.ui_size.setRange(
            8,
            24
        )

        layout.addWidget(
            self.ui_size
        )

        self.line_numbers = QCheckBox(
            self.lang.get("show_line_numbers")
        )

        layout.addWidget(
            self.line_numbers
        )

        layout.addStretch()

        return page

    def terminal_page(self):

        page = QWidget()

        layout = QVBoxLayout(page)

        title = QLabel(
            self.lang.get("terminal")
        )

        title.setStyleSheet(
            """
            font-size:18px;
            font-weight:bold;
            """
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            QLabel(
                self.lang.get("terminal_font")
            )
        )

        self.terminal_font = QComboBox()

        self.terminal_font.addItems(
            [
                "Consolas",
                "Cascadia Code",
                "JetBrains Mono",
                "Fira Code",
                "Courier New"
            ]
        )

        layout.addWidget(
            self.terminal_font
        )

        layout.addWidget(
            QLabel(
                self.lang.get("terminal_font_size")
            )
        )

        self.terminal_size = QSpinBox()

        self.terminal_size.setRange(
            8,
            32
        )

        layout.addWidget(
            self.terminal_size
        )

        self.append_output = QCheckBox(
            self.lang.get("append_output")
        )

        self.auto_scroll = QCheckBox(
            self.lang.get("auto_scroll")
        )

        self.clear_before_run = QCheckBox(
            self.lang.get("clear_before_run")
        )

        layout.addWidget(
            self.append_output
        )

        layout.addWidget(
            self.auto_scroll
        )

        layout.addWidget(
            self.clear_before_run
        )

        layout.addWidget(
            QLabel(
                self.lang.get("max_lines")
            )
        )

        self.terminal_max_lines = QSpinBox()

        self.terminal_max_lines.setRange(
            100,
            100000
        )

        layout.addWidget(
            self.terminal_max_lines
        )

        self.timestamp = QCheckBox(
            self.lang.get("show_timestamp")
        )

        layout.addWidget(
            self.timestamp
        )

        layout.addWidget(
            QLabel(
                self.lang.get("colors")
            )
        )

        self.output_button = ColorButton()

        self.error_button = ColorButton()

        self.background_button = ColorButton()

        layout.addWidget(
            QLabel(
                self.lang.get("output")
            )
        )

        layout.addWidget(
            self.output_button
        )

        layout.addWidget(
            QLabel(
                self.lang.get("error")
            )
        )

        layout.addWidget(
            self.error_button
        )

        layout.addWidget(
            QLabel(
                self.lang.get("background")
            )
        )

        layout.addWidget(
            self.background_button
        )

        layout.addStretch()

        return page

    def files_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel(self.lang.get("files")))

        self.auto_save = QCheckBox(self.lang.get("auto_save"))
        self.smart_save = QCheckBox(self.lang.get("smart_save"))
        self.auto_save_interval = QSpinBox()
        self.auto_save_interval.setRange(1, 30)
        self.restore_tabs = QCheckBox(self.lang.get("restore_tabs"))
        self.restore_cursor = QCheckBox(self.lang.get("restore_cursor_positions"))

        self.auto_save.toggled.connect(
            lambda checked: self.smart_save.setChecked(False) if checked else None
        )
        self.smart_save.toggled.connect(
            lambda checked: self.auto_save.setChecked(False) if checked else None
        )

        layout.addWidget(self.auto_save)
        layout.addWidget(QLabel(self.lang.get("auto_save_interval")))
        layout.addWidget(self.auto_save_interval)
        layout.addWidget(self.smart_save)
        layout.addWidget(self.restore_tabs)
        layout.addWidget(self.restore_cursor)
        layout.addStretch()

        return page

    def python_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel(self.lang.get("python")))

        self.python_interpreter = QLineEdit()
        self.live_analysis = QCheckBox(self.lang.get("live_analysis"))
        self.warnings = QCheckBox(self.lang.get("show_warnings"))

        layout.addWidget(QLabel(self.lang.get("interpreter")))
        layout.addWidget(self.python_interpreter)
        layout.addWidget(self.live_analysis)
        layout.addWidget(self.warnings)
        layout.addStretch()

        return page

    def advanced_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel(self.lang.get("advanced")))

        self.developer_mode = QCheckBox(self.lang.get("developer_mode"))
        self.logging = QCheckBox(self.lang.get("enable_logging"))

        layout.addWidget(self.developer_mode)
        layout.addWidget(self.logging)
        layout.addStretch()

        return page

    def apply_settings(self):
        self.settings.language = self.language.currentData()
        self.settings.editor_font_family = self.editor_font.currentText()
        self.settings.editor_font_size = self.editor_size.value()
        self.settings.tab_size = self.tab_size.value()
        self.settings.syntax_highlighting = self.syntax.isChecked()
        self.settings.autocomplete = self.autocomplete.isChecked()
        self.settings.autocomplete_parentheses = (
            self.autocomplete_parentheses.isChecked()
        )
        self.settings.auto_brackets = self.auto_brackets.isChecked()
        self.settings.scroll_speed = self.scroll_speed.value()

        self.settings.theme = self.theme.currentText()
        self.settings.ui_font_family = self.ui_font.currentText()
        self.settings.ui_font_size = self.ui_size.value()
        self.settings.line_numbers = self.line_numbers.isChecked()

        self.settings.terminal_font_family = self.terminal_font.currentText()
        self.settings.terminal_font_size = self.terminal_size.value()
        self.settings.terminal_append_output = self.append_output.isChecked()
        self.settings.terminal_auto_scroll = self.auto_scroll.isChecked()
        self.settings.terminal_clear_before_run = self.clear_before_run.isChecked()
        self.settings.terminal_max_lines = self.terminal_max_lines.value()
        self.settings.terminal_timestamp = self.timestamp.isChecked()

        self.settings.terminal_output_color = self.output_button.value()
        self.settings.terminal_error_color = self.error_button.value()
        self.settings.terminal_background = self.background_button.value()

        self.settings.highlight_current_line = self.highlight_current_line.isChecked()
        self.settings.show_whitespace = self.show_whitespace.isChecked()
        self.settings.word_wrap = self.word_wrap.isChecked()
        self.settings.auto_indent = self.auto_indent.isChecked()
        self.settings.highlight_matching_brackets = self.highlight_matching_brackets.isChecked()
        self.settings.minimap = self.minimap.isChecked()

        smart_save = self.smart_save.isChecked()
        self.settings.auto_save = self.auto_save.isChecked() and not smart_save
        self.settings.auto_save_interval = self.auto_save_interval.value()
        self.settings.smart_save = smart_save
        self.settings.restore_tabs = self.restore_tabs.isChecked()
        self.settings.restore_cursor = self.restore_cursor.isChecked()

        self.settings.python_interpreter = self.python_interpreter.text()

        self.settings.live_analysis = self.live_analysis.isChecked()
        self.settings.python_warnings_enabled = self.warnings.isChecked()

        self.settings.developer_mode = self.developer_mode.isChecked()
        self.settings.logging = self.logging.isChecked()

        self.settings.save()
        self.accept()

    def load_settings(self):
        index = self.language.findData(self.settings.language)
        if index >= 0:
            self.language.setCurrentIndex(index)

        self.editor_font.setCurrentText(self.settings.editor_font_family)
        self.editor_size.setValue(self.settings.editor_font_size)
        self.tab_size.setValue(self.settings.tab_size)

        self.syntax.setChecked(self.settings.syntax_highlighting)
        self.autocomplete.setChecked(self.settings.autocomplete)
        self.autocomplete_parentheses.setChecked(
            self.settings.autocomplete_parentheses
        )
        self.auto_brackets.setChecked(self.settings.auto_brackets)
        self.scroll_speed.setValue(self.settings.scroll_speed)

        self.theme.setCurrentText(self.settings.theme)
        self.ui_font.setCurrentText(self.settings.ui_font_family)
        self.ui_size.setValue(self.settings.ui_font_size)
        self.line_numbers.setChecked(self.settings.line_numbers)

        self.terminal_font.setCurrentText(self.settings.terminal_font_family)
        self.terminal_size.setValue(self.settings.terminal_font_size)
        self.append_output.setChecked(self.settings.terminal_append_output)
        self.auto_scroll.setChecked(self.settings.terminal_auto_scroll)
        self.clear_before_run.setChecked(self.settings.terminal_clear_before_run)
        self.terminal_max_lines.setValue(self.settings.terminal_max_lines)
        self.timestamp.setChecked(self.settings.terminal_timestamp)

        self.highlight_current_line.setChecked(self.settings.highlight_current_line)
        self.show_whitespace.setChecked(self.settings.show_whitespace)
        self.word_wrap.setChecked(self.settings.word_wrap)
        self.auto_indent.setChecked(self.settings.auto_indent)
        self.highlight_matching_brackets.setChecked(self.settings.highlight_matching_brackets)
        self.minimap.setChecked(self.settings.minimap)

        smart_save = self.settings.smart_save
        self.auto_save.setChecked(self.settings.auto_save and not smart_save)
        self.auto_save_interval.setValue(self.settings.auto_save_interval)
        self.smart_save.setChecked(smart_save)
        self.restore_tabs.setChecked(self.settings.restore_tabs)
        self.restore_cursor.setChecked(self.settings.restore_cursor)

        self.python_interpreter.setText(self.settings.python_interpreter)
        self.live_analysis.setChecked(self.settings.live_analysis)
        self.warnings.setChecked(self.settings.python_warnings_enabled)

        self.developer_mode.setChecked(self.settings.developer_mode)
        self.logging.setChecked(self.settings.logging)

        colors = [
            (self.output_button, self.settings.terminal_output_color),
            (self.error_button, self.settings.terminal_error_color),
            (self.background_button, self.settings.terminal_background)
        ]

        for button, color in colors:
            button.set_value(color)