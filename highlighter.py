from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat
)


def make_format(
        color,
        bold=False,
        italic=False
):

    fmt = QTextCharFormat()

    fmt.setForeground(
        QColor(color)
    )

    if bold:
        fmt.setFontWeight(
            QFont.Weight.Bold
        )

    fmt.setFontItalic(
        italic
    )

    return fmt


class LanguageHighlighter(
    QSyntaxHighlighter
):

    def __init__(
            self,
            document,
            settings,
            language
    ):

        super().__init__(document)

        self.settings = settings
        self.language = language

        self.update_formats()

    def update_formats(self):

        colors = self.settings.get(
            "editor.syntax_colors",
            {}
        )

        if not isinstance(colors, dict):
            colors = {}

        self.keyword = make_format(
            colors.get(
                "keyword",
                "#C586C0"
            )
        )

        self.string = make_format(
            colors.get(
                "string",
                "#CE9178"
            )
        )

        self.comment = make_format(
            colors.get(
                "comment",
                "#6A9955"
            )
        )

        self.number = make_format(
            colors.get(
                "number",
                "#B5CEA8"
            )
        )

        self.function = make_format(
            colors.get(
                "function",
                "#DCDCAA"
            )
        )

        self.cls = make_format(
            colors.get(
                "class",
                "#4EC9B0"
            )
        )

        self.decorator = make_format(
            colors.get(
                "decorator",
                "#FFD700"
            )
        )

        self.builtin = make_format(
            colors.get(
                "builtin",
                "#569CD6"
            )
        )

        self.self_format = make_format(
            colors.get(
                "self",
                "#4FC1FF"
            )
        )

        self.todo = make_format(
            colors.get(
                "todo",
                "#FFD700"
            )
        )

        self.brackets = [
            QColor(
                colors.get(
                    "brackets_1",
                    "#FFD700"
                )
            ),
            QColor(
                colors.get(
                    "brackets_2",
                    "#4EC9B0"
                )
            ),
            QColor(
                colors.get(
                    "brackets_3",
                    "#C586C0"
                )
            ),
            QColor(
                colors.get(
                    "brackets_4",
                    "#569CD6"
                )
            ),
            QColor(
                colors.get(
                    "brackets_5",
                    "#CE9178"
                )
            )
        ]

        self.build_rules()

    def build_rules(self):

        self.rules = []

        keywords = self.language.get(
            "keywords",
            []
        )

        for word in keywords:

            self.rules.append(
                (
                    QRegularExpression(
                        rf"\b{word}\b"
                    ),
                    self.keyword
                )
            )

        builtins = self.language.get(
            "builtins",
            []
        )

        for word in builtins:

            self.rules.append(
                (
                    QRegularExpression(
                        rf"\b{word}\b"
                    ),
                    self.builtin
                )
            )

        self.rules.append(
            (
                QRegularExpression(
                    r"\b\d+(\.\d+)?\b"
                ),
                self.number
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r'"[^"\n]*"'
                ),
                self.string
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"'[^'\n]*'"
                ),
                self.string
            )
        )

        line_comment = self.language.get(
            "line_comment",
            "#"
        )

        if line_comment:

            escaped_comment = (
                QRegularExpression.escape(
                    line_comment
                )
            )

            self.rules.append(
                (
                    QRegularExpression(
                        escaped_comment + ".*"
                    ),
                    self.comment
                )
            )

        self.rules.append(
            (
                QRegularExpression(
                    r"\b[A-Za-z_]\w*(?=\()"
                ),
                self.function
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"\b(TODO|FIXME|NOTE)\b"
                ),
                self.todo
            )
        )

    def highlightBlock(
            self,
            text
    ):

        for pattern, fmt in self.rules:

            expression = pattern.globalMatch(
                text
            )

            while expression.hasNext():

                match = expression.next()

                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    fmt
                )

        self.highlight_brackets(text)

    def highlight_brackets(
            self,
            text
    ):

        depth = 0

        bracket_map = {
            "(": ")",
            "[": "]",
            "{": "}"
        }

        opening = set(
            bracket_map.keys()
        )

        closing = set(
            bracket_map.values()
        )

        for index, char in enumerate(text):

            if char in opening:

                color = self.brackets[
                    depth % len(self.brackets)
                    ]

                self.setFormat(
                    index,
                    1,
                    make_format(
                        color.name()
                    )
                )

                depth += 1

            elif char in closing:

                depth = max(
                    0,
                    depth - 1
                )

                color = self.brackets[
                    depth % len(self.brackets)
                    ]

                self.setFormat(
                    index,
                    1,
                    make_format(
                        color.name()
                    )
                )

class PythonHighlighter(
    QSyntaxHighlighter
):

    def __init__(
            self,
            document,
            settings
    ):

        super().__init__(document)

        self.settings = settings

        self.tri_double = QRegularExpression(
            r'"""'
        )

        self.tri_single = QRegularExpression(
            r"'''"
        )

        self.update_formats()

    def update_formats(self):

        colors = self.settings.get(
            "editor.syntax_colors",
            {}
        )

        self.keyword = make_format(
            colors.get(
                "keyword",
                "#C586C0"
            )
        )

        self.string = make_format(
            colors.get(
                "string",
                "#CE9178"
            )
        )

        self.comment = make_format(
            colors.get(
                "comment",
                "#6A9955"
            )
        )

        self.number = make_format(
            colors.get(
                "number",
                "#B5CEA8"
            )
        )

        self.function = make_format(
            colors.get(
                "function",
                "#DCDCAA"
            )
        )

        self.cls = make_format(
            colors.get(
                "class",
                "#4EC9B0"
            )
        )

        self.decorator = make_format(
            colors.get(
                "decorator",
                "#FFD700"
            )
        )

        self.builtin = make_format(
            colors.get(
                "builtin",
                "#569CD6"
            )
        )

        self.self_format = make_format(
            colors.get(
                "self",
                "#4FC1FF"
            )
        )

        self.todo = make_format(
            colors.get(
                "todo",
                "#FFD700"
            )
        )

        self.brackets = [
            QColor(
                colors.get(
                    "brackets_1",
                    "#FFD700"
                )
            ),
            QColor(
                colors.get(
                    "brackets_2",
                    "#4EC9B0"
                )
            ),
            QColor(
                colors.get(
                    "brackets_3",
                    "#C586C0"
                )
            ),
            QColor(
                colors.get(
                    "brackets_4",
                    "#569CD6"
                )
            ),
            QColor(
                colors.get(
                    "brackets_5",
                    "#CE9178"
                )
            )
        ]

        self.build_rules()

    def build_rules(self):

        self.rules = []

        keywords = [
            "False",
            "None",
            "True",
            "and",
            "as",
            "assert",
            "async",
            "await",
            "break",
            "case",
            "class",
            "continue",
            "def",
            "del",
            "elif",
            "else",
            "except",
            "finally",
            "for",
            "from",
            "global",
            "if",
            "import",
            "in",
            "is",
            "lambda",
            "match",
            "nonlocal",
            "not",
            "or",
            "pass",
            "raise",
            "return",
            "try",
            "while",
            "with",
            "yield"
        ]

        for word in keywords:

            self.rules.append(
                (
                    QRegularExpression(
                        rf"\b{word}\b"
                    ),
                    self.keyword
                )
            )

        builtins = [
            "print",
            "len",
            "range",
            "open",
            "int",
            "str",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "type",
            "super",
            "isinstance",
            "enumerate",
            "zip",
            "sum",
            "min",
            "max",
            "abs",
            "input"
        ]

        for word in builtins:

            self.rules.append(
                (
                    QRegularExpression(
                        rf"\b{word}\b"
                    ),
                    self.builtin
                )
            )

        self.rules.append(
            (
                QRegularExpression(
                    r"\bself\b"
                ),
                self.self_format
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"@\w+"
                ),
                self.decorator
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"\bclass\s+([A-Za-z_]\w*)"
                ),
                self.cls
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"\bdef\s+([A-Za-z_]\w*)"
                ),
                self.function
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"\b[A-Za-z_]\w*(?=\()"
                ),
                self.function
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"\b\d+(\.\d+)?\b"
                ),
                self.number
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r'"[^"\n]*"'
                ),
                self.string
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"'[^'\n]*'"
                ),
                self.string
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"#.*"
                ),
                self.comment
            )
        )

        self.rules.append(
            (
                QRegularExpression(
                    r"\b(TODO|FIXME|NOTE)\b"
                ),
                self.todo
            )
        )

    def highlightBlock(
            self,
            text
    ):

        for pattern, fmt in self.rules:

            expression = pattern.globalMatch(
                text
            )

            while expression.hasNext():

                match = expression.next()

                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    fmt
                )

        self.match_multiline(
            text,
            self.tri_double,
            self.string
        )

        self.match_multiline(
            text,
            self.tri_single,
            self.string
        )

        self.highlight_brackets(
            text
        )

    def match_multiline(
            self,
            text,
            delimiter,
            style
    ):

        previous_state = self.previousBlockState()

        if previous_state == 1:

            start = 0

        else:

            match = delimiter.match(
                text
            )

            if not match.hasMatch():
                return

            start = match.capturedStart()

        while start >= 0:

            match = delimiter.match(
                text,
                start + 3
            )

            if match.hasMatch():

                end = match.capturedEnd()

                self.setFormat(
                    start,
                    end - start,
                    style
                )

                start = delimiter.match(
                    text,
                    end
                ).capturedStart()

            else:

                self.setFormat(
                    start,
                    len(text) - start,
                    style
                )

                self.setCurrentBlockState(
                    1
                )

                return

        self.setCurrentBlockState(
            0
        )

    def highlight_brackets(
            self,
            text
    ):

        depth = 0

        opening = {
            "(",
            "[",
            "{"
        }

        closing = {
            ")",
            "]",
            "}"
        }

        for index, char in enumerate(text):

            if char in opening:

                color = self.brackets[
                    depth % len(
                        self.brackets
                    )
                    ]

                self.setFormat(
                    index,
                    1,
                    make_format(
                        color.name()
                    )
                )

                depth += 1

            elif char in closing:

                depth = max(
                    0,
                    depth - 1
                )

                color = self.brackets[
                    depth % len(
                        self.brackets
                    )
                    ]

                self.setFormat(
                    index,
                    1,
                    make_format(
                        color.name()
                    )
                )