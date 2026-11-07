import re
from dataclasses import dataclass


@dataclass
class QuickFix:
    title: str
    start: int
    end: int
    replacement: str

    def apply(self, editor):
        cursor = editor.textCursor()

        cursor.beginEditBlock()

        cursor.setPosition(self.start)
        cursor.setPosition(
            self.end,
            cursor.MoveMode.KeepAnchor
        )

        cursor.insertText(self.replacement)

        cursor.endEditBlock()


class QuickFixProvider:

    def get_fixes(self, code, language, errors, warnings):
        fixes = []

        diagnostics = errors + warnings

        if language == "python":
            fixes.extend(
                self._python_fixes(code, diagnostics)
            )

        elif language == "java":
            fixes.extend(
                self._java_fixes(code, diagnostics)
            )

        return fixes

    def _line_position(self, code, line, column):
        lines = code.splitlines(keepends=True)

        if line < 0 or line >= len(lines):
            return None

        return sum(len(item) for item in lines[:line]) + column

    def _python_fixes(self, code, diagnostics):
        fixes = []

        for line, column, end_line, end_column, message in diagnostics:
            match = re.search(
                r"\binvalid syntax\b",
                message,
                re.IGNORECASE
            )

            if not match:
                continue

            position = self._line_position(
                code, line, column
            )

            if position is None:
                continue

            fixes.append(
                QuickFix(
                    "Python-Syntaxfehler untersuchen",
                    position,
                    position,
                    ""
                )
            )

        return fixes

    def _java_fixes(self, code, diagnostics):
        fixes = []
        lines = code.splitlines(keepends=True)

        for line, column, end_line, end_column, message in diagnostics:
            if line < 0 or line >= len(lines):
                continue

            source_line = lines[line]
            stripped = source_line.strip()

            if not stripped:
                continue

            if not re.search(
                    r"';' expected|expected.*semicolon",
                    message,
                    re.IGNORECASE
            ):
                continue

            if stripped.endswith((";", "{", "}", ":")):
                continue

            position = (
                self._line_position(code, line, len(source_line.rstrip("\r\n")))
            )

            if position is None:
                continue

            fixes.append(
                QuickFix(
                    "Semikolon hinzufügen",
                    position,
                    position,
                    ";"
                )
            )

        return fixes