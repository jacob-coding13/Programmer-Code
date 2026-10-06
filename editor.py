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
    QPointF
)

from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
    QTextOption,
)

from PySide6.QtWidgets import (
    QApplication,
    QPlainTextEdit,
    QTextEdit,
    QToolButton,
)

from analyzer import PythonAnalyzer
from breadcrumb import Breadcrumb
from completion_model import CompletionModel
from completion_popup import CompletionPopup
from folding import FoldingAnalyzer
from highlighter import PythonHighlighter
from language_manager import LanguageManager
from line_number_area import LineNumberArea
from minimap import Minimap
from theme_manager import get_app_style
from themes import THEMES
from variable_analyzer import VariableAnalyzer


class Editor(QPlainTextEdit):

    modified_changed = Signal(bool)
    run_requested = Signal()
    breadcrumb_changed = Signal()

    def __init__(self, settings):
        super().__init__()

        self.settings = settings
        self.lang = LanguageManager(self.settings.language)

        self.minimap_width = 80
        self.minimap = Minimap(self)
        self.minimap.setParent(self)

        self.folding = FoldingAnalyzer()
        self.breadcrumb = Breadcrumb()
        self.folded_ranges = set()

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
            self.highlighter = PythonHighlighter(self.document())

        self.line_number_area = LineNumberArea(self)
        self.model = CompletionModel()
        self.analyzer = PythonAnalyzer()
        self.completion = CompletionPopup()
        self.completion.completed.connect(self.insert_completion)
        self.variable_analyzer = VariableAnalyzer()

        self.setMouseTracking(True)

        self.analysis_timer = QTimer(self)
        self.analysis_timer.setSingleShot(True)
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
        self.textChanged.connect(self.update_variables)
        self.textChanged.connect(
            lambda: self.string_comment_timer.start(200)
        )
        self.textChanged.connect(self.run_analysis)
        self.update_string_comment_ranges()

        self.update_line_number_area_width()
        self.setup_autocomplete()
        self.apply_settings()
        self.position_run_button()

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

    def is_in_comment(self, position):
        try:
            tokens = tokenize.generate_tokens(
                io.StringIO(self.toPlainText()).readline
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

                if start_position <= position < end_position:
                    return True

        except (
                tokenize.TokenError,
                IndentationError,
                SyntaxError,
        ):
            pass

        return False

    def keyPressEvent(self, event: QKeyEvent):
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
            indent = ""

            if self.settings.auto_indent:
                for c in line:
                    if c in (" ", "\t"):
                        indent += c
                    else:
                        break

                if line.rstrip().endswith(":"):
                    indent += " " * self.settings.tab_size

            cursor.beginEditBlock()
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

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        theme = THEMES[self.settings.theme]

        painter.fillRect(event.rect(), QColor(theme["line"]))

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
                painter.setPen(
                    QColor(theme["line_number"])
                )

                for start, end in self.folding.folds:
                    if start == block_number + 1:
                        key = (start, end)

                        center_x = 8

                        center_y = int(
                            top + self.fontMetrics().height() * 1.75
                        )

                        size = 5

                        if key in self.folded_ranges:
                            points = [
                                QPoint(
                                    center_x - 2,
                                    center_y - size
                                ),
                                QPoint(
                                    center_x - 2,
                                    center_y + size
                                ),
                                QPoint(
                                    center_x + size,
                                    center_y
                                )
                            ]
                        else:
                            points = [
                                QPoint(
                                    center_x - size,
                                    center_y - 2
                                ),
                                QPoint(
                                    center_x + size,
                                    center_y - 2
                                ),
                                QPoint(
                                    center_x,
                                    center_y + size
                                )
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

        start, end = fold

        if fold in self.folded_ranges:

            self.folded_ranges.remove(fold)

            for number in range(start + 1, end + 1):
                block = self.document().findBlockByNumber(number - 1)

                if block.isValid():
                    block.setVisible(True)
                    block.setLineCount(1)

        else:

            self.folded_ranges.add(fold)

            for number in range(start + 1, end + 1):
                block = self.document().findBlockByNumber(number - 1)

                if block.isValid():
                    block.setVisible(False)
                    block.setLineCount(0)

        self.document().markContentsDirty(
            0,
            self.document().characterCount()
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

        block = self.document().begin()

        while block.isValid():
            block.setVisible(True)
            block.setLineCount(1)
            block = block.next()

        for fold, fold_id in self.folding.fold_ids.items():
            if fold_id not in state:
                continue

            self.folded_ranges.add(fold)

            start, end = fold

            for block_number in range(start, end):
                block = self.document().findBlockByNumber(
                    block_number
                )

                if block.isValid():
                    block.setVisible(False)
                    block.setLineCount(0)

        self.document().markContentsDirty(
            0,
            self.document().characterCount()
        )

        self.update_sticky_lines()
        self.viewport().update()
        self.line_number_area.update()

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
            if self.highlighter is None:
                self.highlighter = PythonHighlighter(self.document())
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

    def run_analysis(self):
        text = self.toPlainText()

        try:
            self.errors, self.warnings = self.analyzer.analyze(text)

        except Exception as e:
            self.errors = []
            self.warnings = []

        try:
            self.folding.analyze(text)
            valid_folds = set(self.folding.folds)

            self.folded_ranges = {
                fold
                for fold in self.folded_ranges
                if fold in valid_folds
            }
        except Exception:
            pass

        try:
            self.breadcrumb.update(self)
        except Exception:
            pass

        self.update_error_marks()
        self.minimap.update()

    def update_line_number_area_width(self):
        minimap_width = self.minimap_width if self.settings.minimap else 0

        self.setViewportMargins(
            self.line_number_area_width(),
            28,
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

        try:
            self.folding.analyze(self.toPlainText())
        except Exception:
            pass

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

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_error_marks(self):
        selections = []

        for line, column, end_line, end_column, message in self.errors:
            block = self.document().findBlockByNumber(line)

            if not block.isValid():
                continue

            cursor = QTextCursor(block)

            start = block.position() + column

            if end_line == line:
                end = block.position() + end_column
            else:
                end_block = self.document().findBlockByNumber(end_line)

                if end_block.isValid():
                    end = end_block.position() + end_column
                else:
                    end = start + 1

            cursor.setPosition(start)
            cursor.setPosition(
                max(start + 1, end),
                QTextCursor.KeepAnchor
            )

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor

            fmt = QTextCharFormat()
            fmt.setUnderlineStyle(
                QTextCharFormat.SpellCheckUnderline
            )
            fmt.setUnderlineColor(
                QColor("#ff3333")
            )

            selection.format = fmt
            selections.append(selection)

        for line, column, end_line, end_column, message in self.warnings:
            block = self.document().findBlockByNumber(line)

            if not block.isValid():
                continue

            cursor = QTextCursor(block)

            start = block.position() + column

            if end_line == line:
                end = block.position() + end_column
            else:
                end_block = self.document().findBlockByNumber(end_line)

                if end_block.isValid():
                    end = end_block.position() + end_column
                else:
                    end = start + 1

            cursor.setPosition(start)
            cursor.setPosition(
                max(start + 1, end),
                QTextCursor.KeepAnchor
            )

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor

            fmt = QTextCharFormat()
            fmt.setUnderlineStyle(
                QTextCharFormat.SpellCheckUnderline
            )
            fmt.setUnderlineColor(
                QColor("#ffcc00")
            )

            selection.format = fmt
            selections.append(selection)

        if self.settings.highlight_current_line:
            theme = THEMES[self.settings.theme]

            current = QTextEdit.ExtraSelection()
            current.format.setBackground(
                QColor(theme["current_line"])
            )
            current.format.setProperty(
                QTextFormat.FullWidthSelection,
                True
            )
            current.cursor = self.textCursor()
            current.cursor.clearSelection()

            selections.append(current)

        selections.extend(self.bracket_selections)

        self.setExtraSelections(selections)

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
        cursor = self.textCursor()
        line = cursor.block().text()
        pos = cursor.positionInBlock()
        before = line[:pos]

        context_type, context_prefix = self.get_completion_context()

        if context_type:
            type_name = None

            for name, value in {
                "str": str,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
            }.items():
                if value is context_type:
                    type_name = name
                    break

            if type_name:
                words = self.model.methods_for_type(type_name)

                words = [
                    word
                    for word in words
                    if word.lower().startswith(context_prefix.lower())
                ]

                if not words:
                    self.completion.hide()
                    return

                self.completion.show_items(
                    words,
                    self.cursorRect(),
                    self
                )
                return

        if before.count('"') % 2 == 1 or before.count("'") % 2 == 1:
            self.completion.hide()
            return

        prefix = self.current_word()

        self.variable_analyzer.analyze(self.toPlainText())
        self.model.variables.clear()

        for variable in self.variable_analyzer.completions():
            self.model.add_variable(variable)

        words = self.model.search(prefix)

        if not words:
            self.completion.hide()
            return

        self.completion.show_items(words, self.cursorRect(), self)

    def setup_autocomplete(self):
        words = [
            "False", "None", "True", "and", "as", "assert", "async",
            "await", "break", "class", "continue", "def", "del",
            "elif", "else", "except", "finally", "for", "from",
            "global", "if", "import", "in", "is", "lambda",
            "nonlocal", "not", "or", "pass", "raise", "return",
            "try", "while", "with", "yield", "print", "input",
            "len", "range", "open", "list", "dict", "tuple",
            "set", "int", "float", "str", "bool", "enumerate",
            "zip", "map", "filter", "sorted", "sum", "min",
            "max", "abs", "QWidget", "QMainWindow", "QDialog",
            "QPushButton", "QLabel", "QLineEdit", "QVBoxLayout",
            "QHBoxLayout", "QGridLayout", "QTimer", "Signal",
            "self", "__init__"
        ]

        self.model.add_words(words)

    def insert_completion(self, word):
        prefix = self.current_word()
        cursor = self.textCursor()

        for _ in range(len(prefix)):
            cursor.deletePreviousChar()

        cursor.insertText(word)

        if (
                getattr(self.settings, "autocomplete_parentheses", True)
                and word in self.callable_words
        ):
            cursor.insertText("()")
            cursor.movePosition(
                QTextCursor.Left,
                QTextCursor.MoveAnchor
            )

        self.setTextCursor(cursor)
        self.completion.hide()

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

        self.run_analysis()

        self.current_file = str(path)
        self.modified = False
        self.modified_changed.emit(False)

        words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)
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