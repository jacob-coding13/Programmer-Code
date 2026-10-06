from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

def make_format(color, bold=False, italic=False):
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    fmt.setFontItalic(italic)
    return fmt

class PythonHighlighter(QSyntaxHighlighter):

    def __init__(self, document):
        super().__init__(document)

        self.keyword = make_format("#C586C0", bold=True)
        self.string = make_format("#CE9178")
        self.comment = make_format("#6A9955", italic=True)
        self.number = make_format("#B5CEA8")
        self.function = make_format("#DCDCAA")
        self.cls = make_format("#4EC9B0")
        self.decorator = make_format("#FFD700")
        self.builtin = make_format("#569CD6")
        self.self_format = make_format("#4FC1FF")
        self.todo = make_format("#FFD700", bold=True)

        self.rules = []

        keywords = [
            "False", "None", "True", "and", "as", "assert", "async", "await",
            "break", "case", "class", "continue", "def", "del", "elif", "else",
            "except", "finally", "for", "from", "global", "if", "import", "in",
            "is", "lambda", "match", "nonlocal", "not", "or", "pass", "raise",
            "return", "try", "while", "with", "yield"
        ]
        for word in keywords:
            self.rules.append((
                QRegularExpression(rf"\b{word}\b"),
                self.keyword
            ))

        builtins = [
            "print", "len", "range", "open", "int", "str", "float", "list",
            "dict", "set", "tuple", "type", "super", "isinstance", "enumerate",
            "zip", "sum", "min", "max", "abs", "input"
        ]
        for word in builtins:
            self.rules.append((
                QRegularExpression(rf"\b{word}\b"),
                self.builtin
            ))

        self.rules.append((QRegularExpression(r"\bself\b"), self.self_format))
        self.rules.append((QRegularExpression(r"@\w+"), self.decorator))

        self.rules.append((QRegularExpression(r"\bclass\s+([A-Za-z_]\w*)"), self.cls))
        self.rules.append((QRegularExpression(r"\bdef\s+([A-Za-z_]\w*)"), self.function))
        self.rules.append((QRegularExpression(r"\b[A-Za-z_]\w*(?=\()"), self.function))

        self.rules.append((QRegularExpression(r"\b\d+(\.\d+)?\b"), self.number))
        self.rules.append((QRegularExpression(r'"[^"\n]*"'), self.string))
        self.rules.append((QRegularExpression(r"'[^'\n]*'"), self.string))

        self.rules.append((QRegularExpression(r"#.*"), self.comment))
        self.rules.append((QRegularExpression(r"\b(TODO|FIXME|NOTE)\b"), self.todo))

        self.brackets = [
            QColor("#FFD700"),
            QColor("#4EC9B0"),
            QColor("#C586C0"),
            QColor("#569CD6"),
            QColor("#CE9178"),
        ]

        self.tri_double = QRegularExpression(r'"""')
        self.tri_single = QRegularExpression(r"'''")

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                if match.lastCapturedIndex() > 0:
                    start = match.capturedStart(1)
                    length = match.capturedLength(1)
                else:
                    start = match.capturedStart()
                    length = match.capturedLength()
                self.setFormat(start, length, fmt)

        self.setCurrentBlockState(0)

        in_multiline = False
        if self.previousBlockState() == 1:
            in_multiline = self.match_multiline(text, 0, self.tri_double, 1)
        elif self.previousBlockState() == 2:
            in_multiline = self.match_multiline(text, 0, self.tri_single, 2)
        else:
            d_start = self.tri_double.match(text)
            s_start = self.tri_single.match(text)

            if d_start.hasMatch() and (not s_start.hasMatch() or d_start.capturedStart() < s_start.capturedStart()):
                in_multiline = self.match_multiline(text, d_start.capturedStart(), self.tri_double, 1)
            elif s_start.hasMatch():
                in_multiline = self.match_multiline(text, s_start.capturedStart(), self.tri_single, 2)

        if not in_multiline:
            depth = 0
            for i, char in enumerate(text):
                current_fmt = self.format(i)
                if current_fmt == self.string or current_fmt == self.comment:
                    continue

                if char in "([{":
                    fmt = QTextCharFormat()
                    fmt.setForeground(self.brackets[depth % len(self.brackets)])
                    self.setFormat(i, 1, fmt)
                    depth += 1
                elif char in ")]}":
                    depth = max(depth - 1, 0)
                    fmt = QTextCharFormat()
                    fmt.setForeground(self.brackets[depth % len(self.brackets)])
                    self.setFormat(i, 1, fmt)

    def match_multiline(self, text, start, delimiter, in_state):
        match = delimiter.match(text, start + 3 if start == 0 and self.previousBlockState() == in_state else start + 3)
        if match.hasMatch():
            length = match.capturedStart() - start + 3
            self.setFormat(start, length, self.string)
            self.setCurrentBlockState(0)
            return False
        else:
            self.setFormat(start, len(text) - start, self.string)
            self.setCurrentBlockState(in_state)
            return True