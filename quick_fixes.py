from __future__ import annotations

import ast
import difflib
import io
import re
import tokenize
from dataclasses import dataclass

@dataclass(frozen=True)
class QuickFix:
    title: str
    start: int
    end: int
    replacement: str
    description: str = ""
    priority: int = 50

    def preview(self, code):
        start = max(0, min(self.start, len(code)))
        end = max(start, min(self.end, len(code)))
        return {
            "title": self.title,
            "description": self.description,
            "before": code[start:end],
            "after": self.replacement,
            "start": start,
            "end": end,
        }

    def apply(self, editor):
        text_length = len(editor.toPlainText())
        start = max(0, min(self.start, text_length))
        end = max(start, min(self.end, text_length))
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        cursor.setPosition(start)
        cursor.setPosition(end, cursor.MoveMode.KeepAnchor)
        cursor.insertText(self.replacement)
        cursor.endEditBlock()
        editor.setTextCursor(cursor)
        editor.setFocus()


class QuickFixProvider:

    def __init__(self, language_manager=None):
        self.language_manager = language_manager

    def get_fixes(self, code, language, errors, warnings):
        language_id = self._language_id(language)
        diagnostics = list(errors or []) + list(warnings or [])
        if language_id == "python":
            fixes = self._python_fixes(code, diagnostics)
        elif language_id == "java":
            fixes = self._java_fixes(code, diagnostics)
        else:
            fixes = []
        unique = {}
        for fix in fixes:
            unique[(fix.title, fix.start, fix.end, fix.replacement)] = fix
        return sorted(unique.values(), key=lambda f: (f.priority, f.start, f.title))

    def _language_id(self, language):
        if isinstance(language, dict):
            language = language.get("id") or language.get("name")
        value = str(language or "").lower().strip()
        if value in {"python", "py"}:
            return "python"
        if value == "java":
            return "java"
        if self.language_manager:
            ext = value if value.startswith(".") else "." + value
            definition = self.language_manager.get_programming_language(ext)
            if definition:
                return str(definition.get("id", "")).lower()
        if value.endswith(".py"):
            return "python"
        if value.endswith(".java"):
            return "java"
        return None

    @staticmethod
    def _line_start(code, line):
        starts = [0]
        for match in re.finditer("\n", code):
            starts.append(match.end())
        return starts[line] if 0 <= line < len(starts) else None

    @classmethod
    def _pos(cls, code, line, column):
        start = cls._line_start(code, line)
        if start is None:
            return None
        end = code.find("\n", start)
        if end < 0:
            end = len(code)
        return min(start + max(0, column), end)

    @staticmethod
    def _parts(diagnostic):
        try:
            return (int(diagnostic[0]), int(diagnostic[1]),
                    int(diagnostic[2]), int(diagnostic[3]),
                    str(diagnostic[4]))
        except (TypeError, ValueError, IndexError):
            return None

    def _python_fixes(self, code, diagnostics):
        fixes = []
        lines = code.splitlines(keepends=True)
        names = self._python_names(code)

        for diagnostic in diagnostics:
            parts = self._parts(diagnostic)
            if not parts:
                continue
            line, column, end_line, end_column, message = parts
            if line < 0 or line >= len(lines):
                continue

            rule_match = re.match(r"\s*([A-Z]\d{3})\s*:", message)
            rule = rule_match.group(1) if rule_match else ""
            lower = message.lower()
            start = self._pos(code, line, column)
            end = self._pos(code, end_line, end_column)
            if start is None:
                continue
            if end is None or end < start:
                end = start

            # Ruff F821: Vorschläge für ähnlich geschriebene Namen.
            if rule == "F821" or "undefined name" in lower:
                # Ruff verwendet je nach Version einfache Anführungszeichen
                # oder Backticks um den unbekannten Namen.
                unknown_match = re.search(
                    r"(?:undefined name|name)\s*[`'\"]([^`'\"]+)[`'\"]",
                    message, re.I
                )
                if unknown_match:
                    unknown = unknown_match.group(1)
                    for candidate in difflib.get_close_matches(
                        unknown, [name for name in names if name != unknown],
                        n=3, cutoff=0.72
                    ):
                        occurrence = re.search(
                            rf"\b{re.escape(unknown)}\b", lines[line]
                        )
                        if occurrence:
                            a = self._pos(code, line, occurrence.start())
                            b = self._pos(code, line, occurrence.end())
                            fixes.append(QuickFix(
                                f"'{unknown}' durch '{candidate}' ersetzen",
                                a, b, candidate,
                                "Ähnlich geschriebener Name im Quelltext.", 10
                            ))
                    import_fix = self._python_import_fix(code, unknown)
                    if import_fix:
                        fixes.append(import_fix)

            # F401: unbenutzten Import entfernen.
            if rule == "F401" and re.match(
                r"\s*(import\s+|from\s+\S+\s+import\s+)", lines[line]
            ):
                a = sum(map(len, lines[:line]))
                fixes.append(QuickFix(
                    "Nicht verwendeten Import entfernen",
                    a, a + len(lines[line]), "",
                    "Ruff meldet einen nicht verwendeten Import.", 35
                ))

            # F841: nicht verwendete lokale Zuweisung entfernen.
            if rule == "F841" and re.match(
                r"\s*[A-Za-z_]\w*\s*=", lines[line]
            ):
                a = sum(map(len, lines[:line]))
                fixes.append(QuickFix(
                    "Nicht verwendete Zuweisung entfernen",
                    a, a + len(lines[line]), "",
                    "Ruff meldet eine nicht verwendete lokale Variable.", 60
                ))

            # E722: bare except vermeiden.
            if rule == "E722":
                match = re.search(r"\bexcept\s*:", lines[line])
                if match:
                    p = self._pos(code, line, match.end() - 1)
                    fixes.append(QuickFix(
                        "Exception ergänzen", p, p, " Exception",
                        "Fängt normale Exceptions statt BaseException ab.", 30
                    ))

            # Fehlender Doppelpunkt bei Block-Anweisungen.
            if ("expected ':'" in lower or "expected colon" in lower):
                source = lines[line].rstrip("\r\n")
                if re.match(
                    r"^\s*(if|elif|else|for|while|def|class|try|except|"
                    r"finally|with|match|case)\b", source
                ) and not source.rstrip().endswith(":"):
                    p = self._pos(code, line, len(source))
                    fixes.append(QuickFix(
                        "Doppelpunkt ergänzen", p, p, ":",
                        "Python-Blockanweisungen benötigen einen Doppelpunkt.", 5
                    ))

        # Token-basierte Korrekturen, unabhängig von Ruff-Diagnosepositionen.
        try:
            for token in tokenize.generate_tokens(io.StringIO(code).readline):
                replacements = {"true": "True", "false": "False", "null": "None"}
                if token.type == tokenize.NAME and token.string in replacements:
                    new = replacements[token.string]
                    p = self._pos(code, token.start[0] - 1, token.start[1])
                    fixes.append(QuickFix(
                        f"{token.string} zu {new} ändern",
                        p, p + len(token.string), new,
                        "Korrigiert eine häufige Verwechslung mit JSON/JavaScript.", 20
                    ))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass

        # Fehlende Klammer nur bei einer passenden EOF-/Syntaxdiagnose anbieten.
        if any(any(term in d[4].lower() for term in
                   ("never closed", "unexpected eof", "unexpected end"))
               for d in diagnostics if len(d) >= 5):
            stack = self._python_bracket_stack(code)
            if stack:
                closer = {"(": ")", "[": "]", "{": "}"}[stack[-1]]
                p = len(code.rstrip())
                fixes.append(QuickFix(
                    f"Schließende Klammer '{closer}' ergänzen",
                    p, p, closer, "Schließt die zuletzt geöffnete Klammer.", 5
                ))

        return fixes


    @staticmethod
    def _python_import_fix(code, unknown):
        """Erzeugt sichere Import-Fixes für bekannte Standardbibliotheksnamen."""
        imports = {
            "json": "import json", "re": "import re", "os": "import os",
            "sys": "import sys", "math": "import math", "random": "import random",
            "statistics": "import statistics", "Path": "from pathlib import Path", "datetime": "import datetime",
            "date": "from datetime import date", "timedelta": "from datetime import timedelta",
            "Counter": "from collections import Counter",
            "defaultdict": "from collections import defaultdict",
            "deque": "from collections import deque",
            "sqrt": "from math import sqrt", "pi": "from math import pi",
            "ceil": "from math import ceil", "floor": "from math import floor",
        }
        statement = imports.get(unknown)
        if not statement or re.search(
            rf"^\s*{re.escape(statement)}\s*$", code, re.M
        ):
            return None

        # Importposition: nach vorhandenen Imports, sonst vor dem ersten Code.
        lines = code.splitlines(keepends=True)
        import_line_indexes = [
            i for i, line in enumerate(lines)
            if re.match(r"^\s*(import\s+|from\s+\S+\s+import\s+)", line)
        ]
        if import_line_indexes:
            index = import_line_indexes[-1]
            position = sum(len(line) for line in lines[:index + 1])
            insertion = statement + "\n"
        else:
            # Shebang und Encoding-Kommentar müssen an erster Stelle bleiben.
            index = 0
            if lines and lines[0].startswith("#!"):
                index = 1
            if len(lines) > index and re.match(r"#.*coding[:=]", lines[index]):
                index += 1
            position = sum(len(line) for line in lines[:index])
            insertion = statement + "\n"
            if position and index < len(lines) and lines[index].strip():
                insertion += "\n"

        return QuickFix(
            f"Import '{unknown}' hinzufügen", position, position, insertion,
            f"Fügt den Standardbibliotheks-Import '{statement}' hinzu.", 12
        )

    @staticmethod
    def _python_names(code):
        names = {
            "print", "len", "range", "str", "int", "float", "bool",
            "list", "dict", "set", "tuple", "sum", "min", "max",
            "abs", "enumerate", "zip", "open", "input", "super",
            "isinstance", "type", "True", "False", "None"
        }
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return sorted(names)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    names.add(alias.asname or alias.name.split(".")[0])
        return sorted(names)

    @staticmethod
    def _python_bracket_stack(code):
        pairs = {"(": ")", "[": "]", "{": "}"}
        stack = []
        try:
            for token in tokenize.generate_tokens(io.StringIO(code).readline):
                if token.type != tokenize.OP:
                    continue
                if token.string in pairs:
                    stack.append(token.string)
                elif token.string in pairs.values():
                    if stack and pairs[stack[-1]] == token.string:
                        stack.pop()
        except (tokenize.TokenError, IndentationError, SyntaxError):
            pass
        return stack

    def _java_fixes(self, code, diagnostics):
        fixes = []
        lines = code.splitlines(keepends=True)

        for diagnostic in diagnostics:
            parts = self._parts(diagnostic)
            if not parts:
                continue
            line, column, _, _, message = parts
            if not 0 <= line < len(lines):
                continue
            source = lines[line]
            stripped = source.strip()
            lower = message.lower()

            # javac compiler.err.expected: ';'
            if "';'" in message and "expected" in lower and stripped:
                if not stripped.endswith((";", "{", "}", ":")):
                    p = self._pos(code, line, len(source.rstrip("\r\n")))
                    fixes.append(QuickFix(
                        "Semikolon ergänzen", p, p, ";",
                        "javac erwartet an dieser Stelle ein Semikolon.", 5
                    ))

            # javac erwartet eine schließende Klammer.
            for expected, closer in (("')'", ")"), ("']'", "]"), ("'}'", "}")):
                if expected in message and "expected" in lower:
                    p = self._pos(code, line, column)
                    fixes.append(QuickFix(
                        f"'{closer}' ergänzen", p, p, closer,
                        "Schließt die von javac erwartete Klammer.", 5
                    ))

            # Häufige Schreibfehler bei println/System.
            if "cannot find symbol" in lower or "compiler.err.cant.resolve" in lower:
                for wrong, right in (("printIn", "println"), ("system", "System")):
                    match = re.search(rf"\b{wrong}\b", source)
                    if match:
                        a = self._pos(code, line, match.start())
                        fixes.append(QuickFix(
                            f"{wrong} zu {right} korrigieren",
                            a, a + len(wrong), right,
                            "Korrigiert einen häufigen Java-Schreibfehler.", 10
                        ))

                import_fix = self._java_import_fix(code, message)
                if import_fix:
                    fixes.append(import_fix)

        if any("compiler.err.premature.eof" in str(d[4]).lower()
               for d in diagnostics if len(d) >= 5):
            missing = self._java_missing_closers(code)
            if missing:
                p = len(code.rstrip())
                fixes.append(QuickFix(
                    f"Fehlende Klammern ergänzen: {missing}",
                    p, p, "\n" + missing,
                    "Schließt offene Klammern am Dateiende.", 5
                ))
        return fixes

    @staticmethod
    def _java_missing_closers(code):
        pairs = {"(": ")", "[": "]", "{": "}"}
        stack = []
        state = "code"
        escaped = False
        i = 0
        while i < len(code):
            char = code[i]
            nxt = code[i + 1] if i + 1 < len(code) else ""
            if state == "line":
                if char == "\n":
                    state = "code"
                i += 1
                continue
            if state == "block":
                if char == "*" and nxt == "/":
                    state = "code"
                    i += 2
                else:
                    i += 1
                continue
            if state in {"string", "char"}:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif (state == "string" and char == '"') or (
                    state == "char" and char == "'"
                ):
                    state = "code"
                i += 1
                continue
            if char == "/" and nxt == "/":
                state = "line"
                i += 2
                continue
            if char == "/" and nxt == "*":
                state = "block"
                i += 2
                continue
            if char == '"':
                state = "string"
            elif char == "'":
                state = "char"
            elif char in pairs:
                stack.append(char)
            elif char in pairs.values() and stack and pairs[stack[-1]] == char:
                stack.pop()
            i += 1
        return "".join(pairs[item] for item in reversed(stack))

    @staticmethod
    def _java_import_fix(code, message):
        match = re.search(r"symbol:\s*class\s+([A-Za-z_]\w*)", message)
        if not match:
            return None
        symbol = match.group(1)
        known = {
            "ArrayList": "java.util.ArrayList", "HashMap": "java.util.HashMap",
            "HashSet": "java.util.HashSet", "List": "java.util.List",
            "Map": "java.util.Map", "Set": "java.util.Set",
            "Scanner": "java.util.Scanner", "Collections": "java.util.Collections",
            "LocalDate": "java.time.LocalDate",
            "LocalDateTime": "java.time.LocalDateTime",
            "Path": "java.nio.file.Path", "Files": "java.nio.file.Files"
        }
        qualified = known.get(symbol)
        if not qualified or re.search(
            rf"^\s*import\s+{re.escape(qualified)}\s*;", code, re.M
        ):
            return None
        imports = list(re.finditer(r"^\s*import\s+[^;]+;\s*$", code, re.M))
        package = re.search(r"^\s*package\s+[^;]+;", code, re.M)
        if imports:
            p = imports[-1].end()
            text = f"\nimport {qualified};"
        elif package:
            p = package.end()
            text = f"\n\nimport {qualified};"
        else:
            p = 0
            text = f"import {qualified};\n\n"
        return QuickFix(
            f"Import für {symbol} hinzufügen", p, p, text,
            f"Fügt {qualified} aus der Java-Standardbibliothek hinzu.", 12
        )