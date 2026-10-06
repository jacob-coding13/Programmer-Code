import sys

from PySide6.QtCore import QProcess, Signal, Qt
from PySide6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat, QKeyEvent
from PySide6.QtWidgets import QPlainTextEdit

from language_manager import LanguageManager

class Terminal(QPlainTextEdit):

    finished = Signal()

    def __init__(self, settings):
        super().__init__()

        self.settings = settings
        self.lang = LanguageManager(self.settings.language)

        self.setReadOnly(True)

        self.process = QProcess(self)
        self.input_start = 0
        self.user_has_input = False
        self.process.readyReadStandardOutput.connect(self.read_stdout)
        self.process.readyReadStandardError.connect(self.read_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.errorOccurred.connect(self.process_error)

        self.apply_settings()

    def apply_settings(self):
        try:
            base_size = float(getattr(self.settings, "terminal_font_size", 10))
            scale = float(getattr(self.settings, "ui_scale", 1.0))
            font_size = max(1, round(base_size * scale))
        except (ValueError, TypeError):
            font_size = 10

        font_family = getattr(self.settings, "terminal_font_family", "Monospace")
        self.setFont(QFont(font_family, font_size))

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {getattr(self.settings, 'terminal_background', '#1e1e1e')};
                color: {getattr(self.settings, 'terminal_foreground', '#d4d4d4')};
            }}
        """)

        self.success_color = QColor(getattr(self.settings, "terminal_success_color", "#4ec9b0"))
        self.warning_color = QColor(getattr(self.settings, "terminal_warning_color", "#ce9178"))
        self.error_color = QColor(getattr(self.settings, "terminal_error_color", "#f44747"))
        self.output_color = QColor(getattr(self.settings, "terminal_output_color", "#d4d4d4"))

        self.auto_scroll_enabled = getattr(self.settings, "terminal_auto_scroll", True)

    def write(self, text, error=False):
        if not text:
            return

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()

        if error:
            fmt.setForeground(self.error_color)
        elif "warning" in text.lower():
            fmt.setForeground(self.warning_color)
        elif "success" in text.lower():
            fmt.setForeground(self.success_color)
        else:
            fmt.setForeground(self.output_color)

        cursor.setCharFormat(fmt)
        cursor.insertText(text)
        self.setTextCursor(cursor)

        if self.auto_scroll_enabled:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def clear_output(self):
        if not getattr(self.settings, "terminal_append_output", False):
            self.clear()

    def run(self, file):
        if not file:
            self.write(
                f"> {self.lang.get('no_saved_file_to_run')}\n",
                error=True
            )
            return

        if self.process.state() != QProcess.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)

        self.clear_output()

        running = self.lang.get("running")
        self.write(f"> {running} {file}...\n")

        interpreter = getattr(self.settings, "python_interpreter", None) or sys.executable
        self.setReadOnly(False)
        self.input_start = self.document().characterCount() - 1
        self.user_has_input = False
        self.process.start(interpreter, ["-u", file])

    def read_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode("utf-8", errors="replace")
        self.write(text)
        if not self.user_has_input:
            self.input_start = self.document().characterCount() - 1

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() == Qt.Key_C:
                self.copy()
                return

        if self.process.state() == QProcess.NotRunning:
            return

        cursor = self.textCursor()
        if cursor.position() < self.input_start:
            cursor.clearSelection()
            cursor.setPosition(self.document().characterCount() - 1)
            self.setTextCursor(cursor)

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            text = self.toPlainText()[self.input_start:]
            self.process.write((text + "\n").encode("utf-8"))
            self.write("\n")
            self.input_start = self.document().characterCount() - 1
            self.user_has_input = False
            return

        if event.key() == Qt.Key_Backspace and cursor.position() <= self.input_start:
            return

        if event.key() == Qt.Key_Home:
            cursor.setPosition(self.input_start)
            self.setTextCursor(cursor)
            return

        if event.text() and not event.modifiers() & Qt.ControlModifier:
            self.user_has_input = True

        super().keyPressEvent(event)

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.setReadOnly(True)
            self.write(
                f"\n> {self.lang.get('process_start_failed').format(error=self.process.errorString())}\n",
                error=True
            )

    def read_stderr(self):
        data = self.process.readAllStandardError()
        text = bytes(data).decode("utf-8", errors="replace")
        self.write(text, error=True)
        if not self.user_has_input:
            self.input_start = self.document().characterCount() - 1

    def process_finished(self):
        msg = self.lang.get("process_finished")
        self.setReadOnly(True)
        self.user_has_input = False
        self.write(f"\n> {msg}\n", error=False)
        self.input_start = self.document().characterCount() - 1
        self.finished.emit()

    def reload_language(self):
        self.lang = LanguageManager(self.settings.language)