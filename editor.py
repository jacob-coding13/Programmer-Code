import ast
from pathlib import Path
import re
import io
import tokenize

from PySide6.QtCore import (
    QRect,
    Qt,
    QTimer,
    Signal,
    QPoint,
    QPointF,
    QRunnable,
    QThreadPool,
    QObject
)

from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
    QTextOption, QTextDocument,
)

from PySide6.QtWidgets import (
    QApplication,
    QPlainTextEdit,
    QTextEdit,
    QToolButton,
    QMenu,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QInputDialog,
    QMessageBox
)

from analyzer import PythonAnalyzer, JavaAnalyzer
from breadcrumb import Breadcrumb
from completion_model import CompletionModel
from completion_popup import CompletionPopup
from folding import FoldingAnalyzer
from highlighter import (
    PythonHighlighter,
    LanguageHighlighter
)
from quick_fixes import QuickFixProvider
from language_manager import LanguageManager
from line_number_area import LineNumberArea
from minimap import Minimap
from theme_manager import get_app_style
from themes import THEMES
from variable_analyzer import VariableAnalyzer
from python_completion import PythonCompletion


class AnalysisSignals(QObject):
    
    finished = Signal(int, str, str, object, object)


class AnalysisWorker(QRunnable):
    def __init__(self, request_id, filename, code, analyzer, signals):        
        super().__init__()

        self.request_id = request_id
        self.filename = filename
        self.code = code
        self.analyzer = analyzer
        self.signals = signals

    def run(self):
        errors = []
        warnings = []

        try:
            errors, warnings = self.analyzer.analyze(self.code)

        except Exception as error:
            errors = [
                (0, 0, 0, 0, f"Analysefehler: {error}")
            ]

        try:
            self.signals.finished.emit(
                self.request_id,
                self.filename,
                self.code,
                errors,
                warnings
            )
        except RuntimeError:
            pass


class Editor(QPlainTextEdit):

    modified_changed = Signal(bool)
    run_requested = Signal()
    breadcrumb_changed = Signal()

    def __init__(self, settings):
        super().__init__()

        self.settings = settings
        self.lang = LanguageManager(
            self.settings.language
        )
        self.language_manager = self.lang

        self.minimap_width = 80
        self.minimap = Minimap(self)
        self.minimap.setParent(self)

        self.folding = FoldingAnalyzer()
        self.breadcrumb = Breadcrumb()
        self.folded_ranges = set()

        self.python_completion = PythonCompletion()

        self.current_file = None
        self.modified = False

        self.run_button = QToolButton(self.viewport())
        self.run_button.setText("▶")
        self.run_button.setFixedSize(34, 30)
        self.run_button.clicked.connect(self.run_requested.emit)
        self.run_button.raise_()

        self.verticalScrollBar().setSingleStep(int(20 * self.settings.ui_scale))

        self.errors = []
        self.warnings = []
        self.bracket_selections = []
        self.word_selections = []
        self.string_comment_ranges = []

        self.opening_pairs = {
            "(": ")",
            "[": "]",
            "{": "}",
        }

        self.closing_pairs = {
            ")": "(",
            "]": "[",
            "}": "{",
        }

        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setPlaceholderText(self.lang.get("start_typing_python"))

        self.highlighter = None
        if self.settings.syntax_highlighting:
            self.highlighter = None

        self.line_number_area = LineNumberArea(self)
        self.model = CompletionModel()
        self.python_analyzer = PythonAnalyzer()

        base_dir = Path(__file__).resolve().parent

        self.java_analyzer = JavaAnalyzer(
            checkstyle_jar=base_dir / "tools" / "checkstyle-14.4.0-all.jar",
            config_file=base_dir / "tools" / "checkstyle.xml"
        )

        self.completion = CompletionPopup()
        self.completion.completed.connect(self.insert_completion)
        self.variable_analyzer = VariableAnalyzer()
        self.quick_fix_provider = QuickFixProvider(
            language_manager=self.language_manager
        )

        self.quick_fix_popup = QFrame(self, Qt.Popup)
        self.quick_fix_popup.setObjectName("quickFixPopup")

        self.quick_fix_layout = QVBoxLayout(self.quick_fix_popup)
        self.quick_fix_layout.setContentsMargins(10, 8, 10, 8)
        self.quick_fix_layout.setSpacing(5)

        self.quick_fix_label = QLabel()
        self.quick_fix_layout.addWidget(self.quick_fix_label)

        self.quick_fix_popup.setStyleSheet("""
            QFrame#quickFixPopup {
                background-color: #252526;
                border: 1px solid #555555;
                border-radius: 6px;
            }
        
            QLabel {
                color: white;
                padding: 3px;
            }
        
            QPushButton {
                color: white;
                background-color: #333333;
                border: none;
                padding: 6px;
                text-align: left;
                border-radius: 4px;
            }
        
            QPushButton:hover {
                background-color: #454545;
            }
        """)

        self.current_quick_fix_diagnostic = None

        self.setMouseTracking(True)

        self.analysis_timer = QTimer(self)
        self.analysis_timer.setSingleShot(True)
        self.analysis_timer.setInterval(700)
        self.analysis_timer.timeout.connect(self.run_analysis)

        self.smart_save_timer = QTimer(self)
        self.smart_save_timer.setSingleShot(True)
        self.smart_save_timer.setInterval(500)
        self.smart_save_timer.timeout.connect(self.smart_save)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.updateRequest.connect(self.minimap.update)

        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.cursorPositionChanged.connect(self.highlight_matching_brackets)
        self.cursorPositionChanged.connect(self.update_breadcrumb)
        self.verticalScrollBar().valueChanged.connect(
            self.update_sticky_lines
        )

        self.verticalScrollBar().valueChanged.connect(
            lambda: self.viewport().update()
        )

        self.string_comment_timer = QTimer(self)
        self.string_comment_timer.setSingleShot(True)
        self.string_comment_timer.timeout.connect(
            self.update_string_comment_ranges
        )

        self.textChanged.connect(self.document_changed)
        self.variables_timer = QTimer(self)
        self.variables_timer.setSingleShot(True)
        self.variables_timer.setInterval(400)
        self.variables_timer.timeout.connect(self.update_variables)

        self.textChanged.connect(
            lambda: self.variables_timer.start()
        )

        self.textChanged.connect(
            lambda: self.comment_timer.start()
        )

        self.textChanged.connect(
            lambda: self.string_comment_timer.start(200)
        )

        self.update_string_comment_ranges()

        self.update_line_number_area_width()
        self.setup_autocomplete()
        self.apply_settings()
        self.position_run_button()

        self.analysis_pool = QThreadPool.globalInstance()
        self.analysis_request_id = 0
        self.analysis_workers = {}
        self.analysis_signals = {}

        self.variables_timer = QTimer(self)
        self.variables_timer.setSingleShot(True)
        self.variables_timer.setInterval(400)
        self.variables_timer.timeout.connect(self.update_variables)

        self.comment_timer = QTimer(self)
        self.comment_timer.setSingleShot(True)
        self.comment_timer.setInterval(200)
        self.comment_timer.timeout.connect(self.update_comment_ranges)

        self.comment_ranges = []

        self.callable_words = {
            "print",
            "input",
            "len",
            "range",
            "open",
            "str",
            "int",
            "float",
            "complex",
            "bool",
            "bytes",
            "bytearray",
            "memoryview",

            "list",
            "dict",
            "tuple",
            "set",
            "frozenset",

            "enumerate",
            "zip",
            "map",
            "filter",
            "reversed",
            "iter",
            "next",

            "sorted",
            "sum",
            "min",
            "max",
            "abs",
            "round",
            "pow",

            "all",
            "any",

            "hex",
            "oct",
            "bin",
            "ord",
            "chr",

            "id",
            "type",
            "isinstance",
            "issubclass",
            "callable",
            "hasattr",
            "getattr",
            "setattr",
            "delattr",

            "vars",
            "dir",
            "help",

            "repr",
            "ascii",
            "format",

            "hash",
            "object",
            "super",

            "property",
            "staticmethod",
            "classmethod",

            "exec",
            "eval",
            "compile",

            "globals",
            "locals",

            "breakpoint",
        }

    def rename_symbol(self):
        cursor = self.textCursor()
        old_name = cursor.selectedText().strip() if cursor.hasSelection() else self.current_word()
        if not old_name or not old_name.isidentifier():
            QMessageBox.information(
                self, "Umbenennen", "Markiere zuerst einen gültigen Variablennamen oder Methodennamen."
            )
            return

        new_name, accepted = QInputDialog.getText(
            self, "Symbol umbenennen", f"Neuer Name für '{old_name}':"
        )
        if not accepted:
            return
        new_name = new_name.strip()
        if not new_name or not new_name.isidentifier():
            QMessageBox.warning(self, "Ungültiger Name", "Der neue Name ist kein gültiger Bezeichner.")
            return
        if new_name == old_name:
            return

        code = self.toPlainText()
        matches = list(re.finditer(rf"(?<!\w){re.escape(old_name)}(?!\w)", code))
        if not matches:
            return

        # Rückwärts ersetzen, damit sich die zuvor ermittelten Offsets nicht verschieben.
        edit = QTextCursor(self.document())
        edit.beginEditBlock()
        for match in reversed(matches):
            edit.setPosition(match.start())
            edit.setPosition(match.end(), QTextCursor.KeepAnchor)
            edit.insertText(new_name)
        edit.endEditBlock()
        self.setTextCursor(edit)
        self.setFocus()

    def extract_method(self):
        if not self.current_file or Path(str(self.current_file)).suffix.lower() != ".py":
            QMessageBox.information(
                self, "Methode extrahieren", "Das Extrahieren wird derzeit nur für gespeicherte Python-Dateien unterstützt."
            )
            return

        cursor = self.textCursor()
        if not cursor.hasSelection():
            QMessageBox.information(
                self, "Methode extrahieren", "Markiere zuerst einen oder mehrere vollständige Code-Abschnitte."
            )
            return

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        start_cursor = QTextCursor(self.document())
        start_cursor.setPosition(start)
        end_cursor = QTextCursor(self.document())
        end_cursor.setPosition(end)
        start_block = start_cursor.block()
        end_block = end_cursor.block()

        if start_cursor.positionInBlock() != 0:
            QMessageBox.warning(self, "Auswahl unvollständig", "Die Auswahl muss am Anfang einer Zeile beginnen.")
            return
        if end_cursor.positionInBlock() not in (0, len(end_block.text())):
            QMessageBox.warning(self, "Auswahl unvollständig", "Die Auswahl muss am Ende einer Zeile enden.")
            return

        selected_lines = self.toPlainText()[start:end].splitlines()
        if not selected_lines:
            return
        if any(line.startswith((" ", "\t")) for line in selected_lines if line.strip()):
            QMessageBox.warning(
                self, "Verschachtelter Code", "Bitte wähle aktuell nur Code auf oberster Einrückungsebene aus."
            )
            return

        method_name, accepted = QInputDialog.getText(
            self, "Methode extrahieren", "Name der neuen Funktion:", text="extracted_method"
        )
        if not accepted:
            return
        method_name = method_name.strip()
        if not method_name.isidentifier():
            QMessageBox.warning(self, "Ungültiger Name", "Der Funktionsname ist ungültig.")
            return

        parameters, accepted = QInputDialog.getText(
            self, "Parameter", "Parameter (kommagetrennt, falls benötigt):"
        )
        if not accepted:
            return
        params = [part.strip() for part in parameters.split(",") if part.strip()]
        if any(not name.isidentifier() for name in params) or len(set(params)) != len(params):
            QMessageBox.warning(self, "Ungültige Parameter", "Bitte gib gültige, eindeutige Parameternamen ein.")
            return

        body = "\n".join(selected_lines).rstrip()
        if not body.strip():
            return
        indented_body = "\n".join("    " + line if line else "" for line in body.split("\n"))
        call = f"{method_name}({', '.join(params)})"
        original = self.toPlainText()
        replacement = call
        new_code = original[:start] + replacement + original[end:]
        if new_code and not new_code.endswith("\n"):
            new_code += "\n"
        function_text = f"\n\ndef {method_name}({', '.join(params)}):\n{indented_body}\n"
        new_code += function_text

        warning = (
            "Die Auswahl wird in eine neue Funktion auf Modulebene verschoben. "
            "Prüfe danach insbesondere lokale Variablen und return-Anweisungen.\n\n"
            "Neue Funktion:\n" + function_text.strip()
        )
        answer = QMessageBox.question(
            self, "Extraktion prüfen", warning,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if answer != QMessageBox.Yes:
            return

        self.setPlainText(new_code)
        new_cursor = self.textCursor()
        new_cursor.setPosition(start)
        self.setTextCursor(new_cursor)
        self.setFocus()

    def show_quick_fixes(self):
        code = self.toPlainText()

        filename = (
            str(self.current_file)
            if self.current_file is not None
            else ""
        )

        language = (
            "java"
            if filename.lower().endswith(".java")
            else "python"
        )

        fixes = self.quick_fix_provider.get_fixes(
            code,
            language,
            self.errors,
            self.warnings
        )

        if not fixes:
            return

        menu = QMenu(self)

        for fix in fixes:
            action = menu.addAction(fix.title)
            action.triggered.connect(
                lambda checked=False, current_fix=fix:
                self.apply_quick_fix(current_fix)
            )

        menu.exec(
            self.mapToGlobal(self.cursorRect().bottomRight())
        )

    def show_diagnostic_popup(self, diagnostic, global_position):
        line, column, end_line, end_column, message = diagnostic

        fixes = self.quick_fix_provider.get_fixes(
            self.toPlainText(),
            "java" if (
                    self.current_file
                    and str(self.current_file).lower().endswith(".java")
            ) else "python",
            [diagnostic],
            []
        )

        if (
                self.quick_fix_popup.isVisible()
                and self.current_quick_fix_diagnostic == diagnostic
        ):
            return

        self.current_quick_fix_diagnostic = diagnostic

        while self.quick_fix_layout.count() > 1:
            item = self.quick_fix_layout.takeAt(1)

            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.quick_fix_label.setText(message)

        for fix in fixes:
            button = QPushButton(fix.title)

            button.clicked.connect(
                lambda checked=False, current_fix=fix:
                self.apply_quick_fix(current_fix)
            )

            self.quick_fix_layout.addWidget(button)

        self.quick_fix_popup.adjustSize()
        self.quick_fix_popup.move(global_position + QPoint(12, 16))
        self.quick_fix_popup.show()

    def apply_quick_fix(self, fix):
        self.quick_fix_popup.hide()
        self.current_quick_fix_diagnostic = None

        preview = fix.preview(self.toPlainText())
        before = preview["before"] or "(nichts)"
        after = preview["after"] or "(wird entfernt)"
        details = (
            f"{preview['title']}\n\n"
            f"Beschreibung: {preview['description'] or 'Keine Beschreibung'}\n\n"
            f"Vorher:\n{before}\n\nNachher:\n{after}\n\n"
            "Änderung anwenden?"
        )
        answer = QMessageBox.question(
            self,
            "Quick-Fix-Vorschau",
            details,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            fix.apply(self)
            self.setFocus()

    def is_in_comment(self, position):
        return any(
            start <= position < end
            for start, end in self.comment_ranges
        )

    def keyPressEvent(self, event: QKeyEvent):

        if event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_R:
            self.rename_symbol()
            return

        if event.modifiers() == (Qt.ControlModifier | Qt.AltModifier) and event.key() == Qt.Key_M:
            self.extract_method()
            return

        if (
                event.key() == Qt.Key_Return
                and event.modifiers() == Qt.AltModifier
        ):
            self.show_quick_fixes()
            return

        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_Z:
                self.undo()
                return
            if event.key() == Qt.Key_Y:
                self.redo()
                return

        if self.completion.isVisible():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                word = self.completion.complete_current()
                if word:
                    self.insert_completion(word)
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self.smart_save()
                return

            if event.key() == Qt.Key_Escape:
                self.completion.hide()
                return

            if event.key() == Qt.Key_Up:
                self.completion.move_up()
                return

            if event.key() == Qt.Key_Down:
                self.completion.move_down()
                return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            line = cursor.block().text()
            text = self.toPlainText()
            position = cursor.position()
            column = position - cursor.block().position()

            # Einrückung der aktuellen Zeile übernehmen.
            base_indent = ""
            if self.settings.auto_indent:
                for char in line:
                    if char in (" ", "\t"):
                        base_indent += char
                    else:
                        break

            indent_unit = " " * max(1, self.settings.tab_size)

            # Bei { | } eine echte Blockstruktur erzeugen:
            # öffnende Klammer, eingerückte Leerzeile, schließende Klammer.
            inside_empty_braces = (
                not cursor.hasSelection()
                and position > 0
                and position < len(text)
                and text[position - 1] == "{"
                and text[position] == "}"
            )

            cursor.beginEditBlock()
            if inside_empty_braces:
                inner_indent = base_indent + indent_unit
                insertion_start = cursor.position()
                cursor.insertText("\n" + inner_indent + "\n" + base_indent)
                cursor.setPosition(insertion_start + 1 + len(inner_indent))
            else:
                before_cursor = line[:column]
                stripped_before_cursor = before_cursor.rstrip()
                indent = base_indent

                # Nach Blocköffnern eine Ebene einrücken. Das gilt unter
                # anderem für class, if, for, while und Methoden in Java.
                opens_block = stripped_before_cursor.endswith(("{", "(", ":"))
                if self.settings.auto_indent and opens_block:
                    indent += indent_unit

                # Wenn der Cursor direkt vor einer schließenden Klammer steht,
                # bleibt die neue Zeile auf der Ebene des aktuellen Blocks.
                cursor.insertText("\n" + indent)
            cursor.endEditBlock()

            self.setTextCursor(cursor)
            self.smart_save()
            return

        if event.key() == Qt.Key_Tab:
            cursor = self.textCursor()
            if cursor.hasSelection():
                cursor.beginEditBlock()
                start = cursor.selectionStart()
                end = cursor.selectionEnd()
                cursor.setPosition(start)
                cursor.movePosition(QTextCursor.StartOfBlock)

                lines = []
                while True:
                    lines.append(cursor.blockNumber())
                    if cursor.position() >= end:
                        break
                    if not cursor.movePosition(QTextCursor.NextBlock):
                        break

                for line in reversed(lines):
                    block = self.document().findBlockByNumber(line)
                    cursor.setPosition(block.position())
                    cursor.insertText(" " * self.settings.tab_size)

                cursor.endEditBlock()
                return

        # Bereits automatisch eingefügte schließende Klammern überspringen,
        # statt sie beim Tippen ein zweites Mal einzufügen.
        if event.text() in self.closing_pairs:
            cursor = self.textCursor()
            if not cursor.hasSelection() and cursor.position() < len(self.toPlainText()):
                if self.toPlainText()[cursor.position()] == event.text():
                    cursor.movePosition(QTextCursor.Right)
                    self.setTextCursor(cursor)
                    return

        if event.text() in self.opening_pairs or event.text() in ("'", '"'):
            cursor = self.textCursor()
            position = cursor.position()

            if (
                    not self.is_in_comment(position)
                    and not self.is_bracket_in_string_or_comment(position)
            ):
                if event.text() in self.opening_pairs:
                    closing = self.opening_pairs[event.text()]
                else:
                    closing = event.text()

                cursor.insertText(event.text() + closing)
                cursor.movePosition(
                    QTextCursor.Left,
                    QTextCursor.MoveAnchor
                )
                self.setTextCursor(cursor)

                return

        if event.key() == Qt.Key_Backspace:
            cursor = self.textCursor()
            line = cursor.block().text()

            if not line.strip() and cursor.blockNumber() > 0:
                cursor.beginEditBlock()

                cursor.movePosition(QTextCursor.StartOfBlock)
                cursor.movePosition(QTextCursor.PreviousBlock)
                cursor.movePosition(QTextCursor.EndOfBlock)

                cursor.deleteChar()

                cursor.endEditBlock()

                self.setTextCursor(cursor)
                return

        super().keyPressEvent(event)

        text = event.text()

        if (
                self.settings.autocomplete
                and text
                and (text.isalnum() or text in "_.")
                and not self.is_in_comment(
            self.textCursor().position()
        )
                and not self.is_bracket_in_string_or_comment(
            self.textCursor().position()
        )
        ):
            self.show_completion()
        else:
            self.completion.hide()

    def highlight_matching_words(self):
        self.word_selections = []

        cursor = self.textCursor()

        if not cursor.hasSelection():
            self.update_error_marks()
            return

        word = cursor.selectedText().strip()

        if not word or not word.isidentifier():
            self.update_error_marks()
            return

        document_cursor = QTextCursor(self.document())

        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#665c00"))
        fmt.setForeground(QColor("#ffffff"))

        while True:
            document_cursor = self.document().find(
                word,
                document_cursor,
                QTextDocument.FindCaseSensitively
            )

            if document_cursor.isNull():
                break

            selection = QTextEdit.ExtraSelection()
            selection.cursor = QTextCursor(document_cursor)
            selection.format = fmt

            self.word_selections.append(selection)

        self.update_error_marks()

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        theme = THEMES[self.settings.theme]

        painter.fillRect(
            event.rect(),
            QColor(theme["line"])
        )

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()

        top = self.blockBoundingGeometry(
            block
        ).translated(
            self.contentOffset()
        ).top()

        while block.isValid() and top <= event.rect().bottom():

            bottom = top + self.blockBoundingRect(block).height()

            if block.isVisible():

                painter.setPen(QColor(theme["line_number"]))

                painter.drawText(
                    QRect(
                        14,
                        int(top),
                        self.line_number_area.width() - 20,
                        int(bottom - top)
                    ),
                    Qt.AlignRight | Qt.AlignVCenter,
                    str(block_number + 1)
                )

                for start, end in self.folding.folds:
                    if start == block_number + 1:

                        key = (start, end)

                        center_x = 8
                        center_y = int((top + bottom) / 2)

                        size = 5

                        if key in self.folded_ranges:
                            points = [
                                QPoint(center_x - 2, center_y - size),
                                QPoint(center_x - 2, center_y + size),
                                QPoint(center_x + size, center_y)
                            ]
                        else:
                            points = [
                                QPoint(center_x - size, center_y - 2),
                                QPoint(center_x + size, center_y - 2),
                                QPoint(center_x, center_y + size)
                            ]

                        painter.setBrush(
                            QColor(theme["line_number"])
                        )
                        painter.setPen(Qt.NoPen)
                        painter.drawPolygon(points)

            block = block.next()
            block_number += 1
            top = bottom

    def highlight_current_line(self):
        self.update_error_marks()

    def highlight_matching_brackets(self):
        self.clear_bracket_selections()

        cursor = self.textCursor()

        block = cursor.block()
        column = cursor.positionInBlock()

        if column <= 0:
            return

        index = column - 1
        char = block.text()[index]

        bracket_position = block.position() + index

        if self.is_bracket_in_string_or_comment(bracket_position):
            return

        if char in self.opening_pairs:
            opening = True
            target = self.opening_pairs[char]

        elif char in self.closing_pairs:
            opening = False
            target = self.closing_pairs[char]

        else:
            return

        current_block = block
        current_index = index
        stack = []

        while current_block.isValid():
            text = current_block.text()

            if opening:
                start = current_index + 1
                end = len(text)
                step = 1
            else:
                start = current_index - 1
                end = -1
                step = -1

            for i in range(start, end, step):
                current = text[i]
                current_position = current_block.position() + i

                if (
                        current in "()[]{}"
                        and self.is_bracket_in_string_or_comment(current_position)
                ):
                    continue

                if opening:
                    if current in "([{":
                        stack.append(current)

                    elif current in ")]}":
                        if not stack:
                            if current == target:
                                self.mark_bracket(current_position)
                                self.mark_bracket(bracket_position)
                            return

                        expected = self.opening_pairs[stack[-1]]

                        if current != expected:
                            continue

                        stack.pop()

                        if current == target and not stack:
                            self.mark_bracket(current_position)
                            self.mark_bracket(bracket_position)
                            return

                else:
                    if current in ")]}":
                        stack.append(current)

                    elif current in "([{":
                        if not stack:
                            if current == target:
                                self.mark_bracket(current_position)
                                self.mark_bracket(bracket_position)
                            return

                        expected = self.closing_pairs[stack[-1]]

                        if current != expected:
                            continue

                        stack.pop()

                        if current == target and not stack:
                            self.mark_bracket(current_position)
                            self.mark_bracket(bracket_position)
                            return

            current_block = (
                current_block.next()
                if opening
                else current_block.previous()
            )

            if current_block.isValid():
                if opening:
                    current_index = -1
                else:
                    current_index = len(current_block.text())

    def is_bracket_in_string_or_comment(self, position):
        return any(
            start <= position < end
            for start, end in self.string_comment_ranges
        )

    def update_string_comment_ranges(self):

        self.string_comment_ranges = []

        try:
            tokens = tokenize.generate_tokens(
                io.StringIO(self.toPlainText()).readline
            )

            for token in tokens:
                if token.type not in (
                        tokenize.STRING,
                        tokenize.COMMENT,
                ):
                    continue

                start_line, start_column = token.start
                end_line, end_column = token.end

                start_block = self.document().findBlockByNumber(
                    start_line - 1
                )
                end_block = self.document().findBlockByNumber(
                    end_line - 1
                )

                if not start_block.isValid() or not end_block.isValid():
                    continue

                start_position = (
                        start_block.position() + start_column
                )
                end_position = (
                        end_block.position() + end_column
                )

                self.string_comment_ranges.append(
                    (start_position, end_position)
                )

        except (
                tokenize.TokenError,
                IndentationError,
                SyntaxError,
        ):
            return

    def clear_bracket_selections(self):
        if not self.bracket_selections:
            return

        selections = [
            selection
            for selection in self.extraSelections()
            if selection not in self.bracket_selections
        ]

        self.bracket_selections = []
        self.setExtraSelections(selections)

    def mark_bracket(self, position):
        selection = QTextEdit.ExtraSelection()

        selection.cursor = self.textCursor()
        selection.cursor.setPosition(position)
        selection.cursor.movePosition(
            QTextCursor.NextCharacter,
            QTextCursor.KeepAnchor
        )

        selection.format.setBackground(
            QColor("#4444aa")
        )
        selection.format.setProperty(
            QTextFormat.FullWidthSelection,
            False
        )

        self.bracket_selections.append(selection)

        self.setExtraSelections(
            self.extraSelections() + [selection]
        )

    def toggle_fold(self, line):
        fold = None

        for start, end in self.folding.folds:
            if start == line:
                fold = (start, end)
                break

        if fold is None:
            return

        if fold in self.folded_ranges:
            self.folded_ranges.remove(fold)
        else:
            self.folded_ranges.add(fold)

        self.apply_fold_visibility()

    def apply_fold_visibility(self):
        block = self.document().begin()

        while block.isValid():
            block.setVisible(True)
            block.setLineCount(1)
            block = block.next()

        for start, end in self.folded_ranges:
            for number in range(start + 1, end + 1):
                block = self.document().findBlockByNumber(number - 1)

                if block.isValid():
                    block.setVisible(False)
                    block.setLineCount(0)

        self.document().markContentsDirty(
            0, self.document().characterCount()
        )

        self.document().documentLayout().requestUpdate()

        self.update_sticky_lines()
        self.viewport().update()
        self.line_number_area.update()

    def update_breadcrumb(self):
        self.update_sticky_lines()
        self.viewport().update()
        self.breadcrumb_changed.emit()

    def update_sticky_lines(self):
        self.sticky_lines = []

        scrollbar = self.verticalScrollBar()

        if scrollbar.value() <= 0:
            return

        viewport_top = self.viewport().rect().top()

        current_block = self.document().begin()

        while current_block.isValid():
            if current_block.isVisible():
                rect = self.blockBoundingGeometry(
                    current_block
                ).translated(
                    self.contentOffset()
                )

                if rect.bottom() >= viewport_top:
                    break

            current_block = current_block.next()

        if not current_block.isValid():
            return

        current_line = current_block.blockNumber() + 1

        code = self.toPlainText()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if not isinstance(
                    node,
                    (
                            ast.FunctionDef,
                            ast.AsyncFunctionDef,
                            ast.ClassDef,
                    )
            ):
                continue

            start = getattr(node, "lineno", None)
            end = getattr(node, "end_lineno", None)

            if start is None or end is None:
                continue

            if start < current_line <= end:
                self.sticky_lines.append(start)

        self.sticky_lines.sort()

    def paint_sticky_lines(self, painter):
        if not self.sticky_lines:
            return

        theme = THEMES[self.settings.theme]
        line_height = self.fontMetrics().height()

        painter.save()

        for index, line_number in enumerate(self.sticky_lines):
            block = self.document().findBlockByLineNumber(
                line_number - 1
            )

            if not block.isValid():
                continue

            y = index * line_height

            painter.fillRect(
                0,
                y,
                self.viewport().width(),
                line_height,
                QColor(theme["background"])
            )

            layout = block.layout()

            if layout is None:
                continue

            painter.save()

            painter.translate(
                0,
                y
            )

            painter.setClipRect(
                0,
                0,
                self.viewport().width(),
                line_height
            )

            painter.setPen(
                QColor(theme["foreground"])
            )

            layout.draw(
                painter,
                QPointF(0, 0)
            )

            painter.restore()

            painter.setPen(
                QColor(theme["line"])
            )

            painter.drawLine(
                0,
                y + line_height - 1,
                self.viewport().width(),
                y + line_height - 1
            )

        painter.restore()

    def get_fold_state(self):
        state = []

        for fold in self.folded_ranges:
            fold_id = self.folding.fold_ids.get(fold)

            if fold_id:
                state.append(fold_id)

        return state

    def restore_fold_state(self, state):

        self.folded_ranges.clear()

        for fold, fold_id in self.folding.fold_ids.items():

            if fold_id in state:
                self.folded_ranges.add(fold)

        self.apply_fold_visibility()

    def apply_settings(self):
        self.run_button.setToolTip(self.lang.get("run"))
        self.minimap.setVisible(self.settings.minimap)

        font = QFont(
            self.settings.editor_font_family,
            int(self.settings.editor_font_size * self.settings.ui_scale)
        )
        self.setFont(font)

        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * self.settings.tab_size)

        self.setLineWrapMode(
            QPlainTextEdit.WidgetWidth if self.settings.word_wrap else QPlainTextEdit.NoWrap
        )

        if self.settings.syntax_highlighting:

            if self.current_file:
                self.update_language(
                    self.current_file
                )

            elif self.highlighter is None:
                self.highlighter = PythonHighlighter(
                    self.document(),
                    self.settings
                )

            else:
                self.highlighter.update_formats()
                self.highlighter.rehighlight()

        else:

            if self.highlighter:
                self.highlighter.setDocument(None)
                self.highlighter = None

        if self.settings.line_numbers:
            self.line_number_area.show()
        else:
            self.line_number_area.hide()

        option = self.document().defaultTextOption()
        if self.settings.show_whitespace:
            option.setFlags(option.flags() | QTextOption.ShowTabsAndSpaces)
        else:
            option.setFlags(option.flags() & ~QTextOption.ShowTabsAndSpaces)
        self.document().setDefaultTextOption(option)

        QApplication.instance().setStyleSheet(get_app_style(self.settings))

        self.apply_theme()
        self.highlight_current_line()

        if self.settings.highlight_matching_brackets:
            self.highlight_matching_brackets()

        self.update_line_number_area_width()
        self.viewport().update()

    def reload_language(self):
        self.lang = LanguageManager(self.settings.language)
        self.setPlaceholderText(self.lang.get("start_typing_python"))
        self.run_button.setToolTip(self.lang.get("run"))

    def jump_to_line(self, line_no):
        try:
            line = int(line_no)
        except (TypeError, ValueError):
            return

        if line < 1:
            line = 1

        max_line = max(1, self.blockCount())
        if line > max_line:
            line = max_line

        block = self.document().findBlockByLineNumber(line - 1)
        if not block.isValid():
            return

        cursor = QTextCursor(block)
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
        self.centerCursor()

    def position_run_button(self):
        self.run_button.move(
            self.viewport().width() - self.run_button.width() - 8,
            8
        )
        self.run_button.raise_()

    def apply_theme(self):
        theme = THEMES.get(self.settings.theme, THEMES["Dark"])

        self.setStyleSheet(
            f"""
            QPlainTextEdit {{
                background: {theme["background"]};
                color: {theme["foreground"]};
                selection-background-color: {theme["selection"]};
                font-family: {self.settings.editor_font_family};
                font-size: {int(self.settings.editor_font_size * self.settings.ui_scale)}pt;
            }}
            """
        )

    def _analysis_finished(
            self,
            request_id,
            filename,
            code,
            errors,
            warnings
    ):
        self.analysis_workers.pop(request_id, None)
        self.analysis_signals.pop(request_id, None)

        if request_id != self.analysis_request_id:
            return

        current_filename = (
            str(self.current_file)
            if self.current_file is not None
            else ""
        )

        if filename != current_filename:
            return

        if code != self.toPlainText():
            return

        self.errors = errors
        self.warnings = warnings

        is_java = filename.lower().endswith(".java")

        if not is_java:
            try:
                old_fold_state = self.get_fold_state()

                self.folding.analyze(code)

                self.restore_fold_state(old_fold_state)

            except Exception:
                pass

            try:
                self.breadcrumb.update(self)
            except Exception:
                pass

        else:
            self.model.variables.clear()
            self.sticky_lines = []

        self.update_error_marks()
        self.minimap.update()

    def run_analysis(self):
        text = self.toPlainText()

        filename = (
            str(self.current_file)
            if self.current_file is not None
            else ""
        )

        is_java = filename.lower().endswith(".java")

        analyzer = (
            self.java_analyzer
            if is_java
            else self.python_analyzer
        )

        self.analysis_request_id += 1
        request_id = self.analysis_request_id

        signals = AnalysisSignals()
        signals.finished.connect(self._analysis_finished)

        worker = AnalysisWorker(
            request_id,
            filename,
            text,
            analyzer,
            signals
        )

        self.analysis_workers[request_id] = worker
        self.analysis_signals[request_id] = signals

        self.analysis_pool.start(worker)

    def update_line_number_area_width(self):
        minimap_width = self.minimap_width if self.settings.minimap else 0

        self.setViewportMargins(
            self.line_number_area_width(),
            0,
            minimap_width,
            0
        )

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0,
                rect.y(),
                self.line_number_area.width(),
                rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

        self.minimap.update()

    def document_changed(self):
        if not self.modified:
            self.modified = True
            self.modified_changed.emit(True)

        self.analysis_timer.start(200)

        if self.settings.smart_save:
            self.smart_save_timer.start()

    def smart_save(self):
        if not self.settings.smart_save:
            return

        self.smart_save_timer.stop()
        if self.modified and self.current_file:
            self.save_file()

    def update_variables(self):
        code = self.toPlainText()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        self.model.variables.clear()

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.model.add_variable(target.id)

    def update_comment_ranges(self):
        self.comment_ranges = []

        code = self.toPlainText()

        try:
            tokens = tokenize.generate_tokens(
                io.StringIO(code).readline
            )

            for token in tokens:
                if token.type != tokenize.COMMENT:
                    continue

                start_line, start_column = token.start
                end_line, end_column = token.end

                start_block = self.document().findBlockByNumber(
                    start_line - 1
                )

                end_block = self.document().findBlockByNumber(
                    end_line - 1
                )

                if not start_block.isValid() or not end_block.isValid():
                    continue

                start_position = (
                        start_block.position() + start_column
                )

                end_position = (
                        end_block.position() + end_column
                )

                self.comment_ranges.append(
                    (start_position, end_position)
                )

        except (
                tokenize.TokenError,
                IndentationError,
                SyntaxError
        ):
            pass

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))

        return (
                24
                + self.fontMetrics().horizontalAdvance("9") * digits
        )

    def update_error_marks(self):
        selections = []

        if self.settings.highlight_current_line:
            theme = THEMES[self.settings.theme]

            current = QTextEdit.ExtraSelection()
            current.format.setBackground(QColor(theme["current_line"]))
            current.format.setProperty(
                QTextFormat.FullWidthSelection,
                True
            )

            current.cursor = self.textCursor()
            current.cursor.clearSelection()

            selections.append(current)

        def add_marks(diagnostics, color):
            for line, column, end_line, end_column, message in diagnostics:

                if line == 0 and column == 0 and end_line == 0 and end_column == 0:
                    continue

                block = self.document().findBlockByNumber(line)

                if not block.isValid():
                    continue

                block_end = block.position() + block.length() - 1
                start = min(block.position() + column, block_end)

                end_block = self.document().findBlockByNumber(end_line)

                if not end_block.isValid():
                    continue

                end_block_end = end_block.position() + end_block.length() - 1
                end = min(end_block.position() + end_column, end_block_end)

                if end <= start:
                    end = min(start + 1, block_end)

                if end <= start:
                    continue

                cursor = QTextCursor(self.document())
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.KeepAnchor)

                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor

                fmt = QTextCharFormat()
                fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
                fmt.setUnderlineColor(QColor(color))

                selection.format = fmt
                selections.append(selection)

        add_marks(self.errors, "#ff3333")

        add_marks(self.warnings, "#ffcc00")

        selections.extend(self.word_selections)
        selections.extend(self.bracket_selections)

        self.setExtraSelections(selections)

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        position = cursor.position()
        block = cursor.block()

        if not block.isValid():
            self.quick_fix_popup.hide()
            self.current_quick_fix_diagnostic = None
            super().mouseMoveEvent(event)
            return

        line = block.blockNumber()
        column = position - block.position()

        for diagnostics in (self.errors, self.warnings):
            for diagnostic in diagnostics:
                start_line, start_column, end_line, end_column, message = diagnostic

                if start_line == 0 and start_column == 0:
                    continue

                if start_line == end_line == line:
                    if start_column <= column <= max(end_column, start_column + 1):
                        self.show_diagnostic_popup(
                            diagnostic,
                            event.globalPosition().toPoint()
                        )
                        return

        self.quick_fix_popup.hide()
        self.current_quick_fix_diagnostic = None

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.setToolTip("")

        if not self.quick_fix_popup.isVisible():
            self.current_quick_fix_diagnostic = None

        super().leaveEvent(event)

    def get_completion_context(self):
        cursor = self.textCursor()
        line = cursor.block().text()
        pos = cursor.positionInBlock()

        before = line[:pos]

        match = re.search(
            r"""
            (?:
                (["'])(?:\\.|(?!\1).)*\1
                |
                (?:print|str|input)\([^()\n]*\)
                |
                ([A-Za-z_][A-Za-z0-9_]*)
            )
            \.(\w*)$
            """,
            before,
            re.VERBOSE
        )

        if not match:
            return None, ""

        prefix = match.group(3)

        if match.group(1):
            return str, prefix

        function_call = match.group(0)

        if re.search(r"print\([^()\n]*\)\.", function_call):
            return None, prefix

        if re.search(r"(?:str|input)\([^()\n]*\)\.", function_call):
            return str, prefix

        name = match.group(2)

        builtin_types = {
            "str": str,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
        }

        if name in builtin_types:
            return builtin_types[name], prefix

        return None, prefix

    def show_completion(self):

        if self.is_cursor_in_comment_or_string():
            self.completion.hide()
            return

        cursor = self.textCursor()

        context_type, context_prefix = self.get_completion_context()

        if context_type:

            methods = self.model.methods_for_type(context_type)

            results = [
                method
                for method in methods
                if method.lower().startswith(context_prefix.lower())
            ]

            if results:
                self.completion.show_items(
                    results,
                    self.cursorRect(),
                    self
                )
            else:
                self.completion.hide()

            return

        if self.current_file and self.current_file.endswith(".py"):

            results = self.get_jedi_completions()

            if results:
                self.completion.show_items(
                    results,
                    self.cursorRect(),
                    self
                )
                return

        prefix = self.current_word()

        if not prefix:
            self.completion.hide()
            return

        self.variable_analyzer.analyze(
            self.toPlainText()
        )

        self.model.variables.clear()

        for variable in self.variable_analyzer.variables:
            self.model.add_variable(variable)
    
        results = self.model.search(prefix)

        if results:
            self.completion.show_items(
                results,
                self.cursorRect(),
                self
            )
        else:
            self.completion.hide()

    def setup_autocomplete(self):
        suffix = (
            Path(self.current_file).suffix.lower()
            if self.current_file
            else ".py"
        )

        java_words = [
            "abstract", "assert", "boolean", "break",
            "byte", "case", "catch", "char", "class",
            "const", "continue", "default", "do",
            "double", "else", "enum", "extends",
            "final", "finally", "float", "for",
            "if", "implements", "import", "instanceof",
            "int", "interface", "long", "native",
            "new", "package", "private", "protected",
            "public", "return", "short", "static",
            "strictfp", "super", "switch", "synchronized",
            "this", "throw", "throws", "transient",
            "try", "void", "volatile", "while",

            "String", "System", "Object", "Integer",
            "Double", "Boolean", "Character",
            "Math", "Scanner", "ArrayList",
            "HashMap", "HashSet", "List", "Map",
            "Set", "Collections",

            "println", "print", "printf",
            "length", "equals", "toString",
            "charAt", "substring", "contains",
            "add", "remove", "size", "get", "set",

            "sout", "psvm", "serr"
        ]

        python_words = [
            "False", "None", "True", "and", "as",
            "assert", "async", "await", "break",
            "class", "continue", "def", "del",
            "elif", "else", "except", "finally",
            "for", "from", "global", "if", "import",
            "in", "is", "lambda", "nonlocal", "not",
            "or", "pass", "raise", "return", "try",
            "while", "with", "yield", "print", "input",
            "len", "range", "open", "list", "dict",
            "tuple", "set", "int", "float", "str",
            "bool", "enumerate", "zip", "map",
            "filter", "sorted", "sum", "min", "max",
            "abs", "QWidget", "QMainWindow", "QDialog",
            "QPushButton", "QLabel", "QLineEdit",
            "QVBoxLayout", "QHBoxLayout",
            "QGridLayout", "QTimer", "Signal",
            "self", "__init__"
        ]

        if suffix == ".java":
            words = java_words
        else:
            words = python_words

        self.model.add_words(words)

    def insert_completion(self, word):
        prefix = self.current_word()
        cursor = self.textCursor()

        for _ in range(len(prefix)):
            cursor.deletePreviousChar()

        is_java = (
                self.current_file
                and self.current_file.endswith(".java")
        )

        if is_java and word in ("sout", "serr"):
            if word == "sout":
                output = "System.out.println();"
            elif word == "serr":
                output = "System.err.println();"

            cursor.insertText(output)
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor)
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor)

        elif is_java and word == "psvm":
            line = cursor.block().text()
            base_indent = line[:len(line) - len(line.lstrip(" \t"))]
            inner_indent = base_indent + (" " * max(1, self.settings.tab_size))
            signature = "public static void main(String[] args) {"
            insertion_start = cursor.position()

            # Die Methodenkammer wird auf der aktuellen Ebene geschlossen;
            # der Cursor landet in der eingerückten, leeren Methoden-Zeile.
            cursor.insertText(
                signature + "\n" + inner_indent + "\n" + base_indent + "}"
            )
            cursor.setPosition(
                insertion_start + len(signature) + 1 + len(inner_indent)
            )

        else:
            cursor.insertText(word)

            if (
                    getattr(self.settings, "autocomplete_parentheses", True)
                    and word in self.callable_words
            ):
                cursor.insertText("()")
                cursor.movePosition(QTextCursor.Left)

        self.setTextCursor(cursor)
        self.completion.hide()

    def get_jedi_completions(self):

        cursor = self.textCursor()

        source = self.toPlainText()

        line = cursor.blockNumber() + 1
        column = cursor.positionInBlock()

        path = self.current_file

        return self.python_completion.get_completions(
            source=source,
            line=line,
            column=column,
            path=path
        )

    def current_word(self):
        cursor = self.textCursor()
        pos = cursor.position()
        text = self.toPlainText()

        start = pos
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "_"):
            start -= 1

        return text[start:pos]

    def load_file(self, path):
        path = Path(path)

        if not path.is_file():
            return

        text = path.read_text(encoding="utf-8")

        self.blockSignals(True)
        self.setPlainText(text)
        self.blockSignals(False)

        self.current_file = str(path)

        self.update_language(self.current_file)
        self.run_analysis()

        self.modified = False
        self.modified_changed.emit(False)

        words = re.findall(
            r"[A-Za-z_][A-Za-z0-9_]*",
            text
        )

        self.model.words.clear()
        self.setup_autocomplete()
        self.model.add_words(words)

        self.update_variables()

    def save_file(self):
        if not self.current_file:
            return

        try:
            Path(self.current_file).write_text(
                self.toPlainText(),
                encoding="utf-8"
            )
        except OSError:
            return False

        self.modified = False
        self.modified_changed.emit(False)

        return True

    def new_file(self):
        self.clear()
        self.current_file = None
        self.modified = False

        self.model.variables.clear()

        self.modified_changed.emit(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        rect = self.contentsRect()

        self.line_number_area.setGeometry(
            QRect(
                rect.left(),
                rect.top(),
                self.line_number_area_width(),
                rect.height()
            )
        )

        if self.settings.minimap:
            self.minimap.resize(self.minimap_width, self.height())
            self.minimap.move(self.width() - self.minimap_width, 0)
        self.position_run_button()

    def wheelEvent(self, event):
        speed = float(getattr(self.settings, "scroll_speed", 1.0))

        delta = event.angleDelta().y()

        if delta:
            scrollbar = self.verticalScrollBar()
            steps = max(1, round(abs(delta) / 120 * speed))

            if delta > 0:
                scrollbar.setValue(scrollbar.value() - steps)
            else:
                scrollbar.setValue(scrollbar.value() + steps)

            event.accept()
            return

        super().wheelEvent(event)

    def paintEvent(self, event):

        super().paintEvent(event)

        painter = QPainter(self.viewport())
    
        self.paint_sticky_lines(painter)

        painter.setPen(
            QColor(THEMES[self.settings.theme]["foreground"])
        )

        for start, end in self.folded_ranges:

            block = self.document().findBlockByNumber(start - 1)

            if not block.isValid() or not block.isVisible():
                continue

            rect = self.blockBoundingGeometry(
                block
            ).translated(
                self.contentOffset()
            )

            if not rect.intersects(self.viewport().rect()):
                continue

            layout = block.layout()

            if layout is None:
                continue

            line_text = block.text()

            text_width = self.fontMetrics().horizontalAdvance(
                line_text
            )

            x = text_width + 8
            y = rect.top() + self.fontMetrics().ascent()

            painter.drawText(
                int(x),
                int(y),
                "..."
            )

    def update_language(self, file_path=None):

        suffix = (
            Path(file_path).suffix.lower()
            if file_path
            else ".py"
        )

        language = self.language_manager.get_programming_language(suffix)

        if self.highlighter is not None:
            self.highlighter.setDocument(None)
            self.highlighter = None

        if suffix == ".py":
            self.highlighter = PythonHighlighter(
                self.document(),
                self.settings
            )

        elif language is not None:
            self.highlighter = LanguageHighlighter(
                self.document(),
                self.settings,
                language
            )

        if self.highlighter is not None:
            self.highlighter.rehighlight()