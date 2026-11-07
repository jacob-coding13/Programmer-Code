import re

class FoldingAnalyzer:

    def __init__(self):
        self.folds = []
        self.fold_ids = {}

    def analyze(self, code):
        self.folds.clear()
        self.fold_ids.clear()

        lines = code.splitlines()

        if not lines:
            return self.folds

        java_pattern = re.compile(
            r"^\s*(?:"
            r"package\s+[\w.]+\s*;"
            r"|import\s+(?:static\s+)?[\w.*]+\s*;"
            r"|(?:public|private|protected)\s+"
            r"(?:(?:abstract|final|static)\s+)*"
            r"(?:class|interface|enum|record)\b"
            r"|(?:class|interface|enum|record)\s+\w+"
            r"(?:\s+extends\b|\s+implements\b|\s*\{)"
            r")",
            re.MULTILINE
        )

        is_java = bool(java_pattern.search(code))

        if is_java:
            self._analyze_java(lines)
        else:
            self._analyze_python(lines)

        self.folds.sort(
            key=lambda item: (item[0], -item[1])
        )

        return self.folds

    def _analyze_python(self, lines):

        structure_pattern = re.compile(
            r"^(?:async\s+)?(?:def|class)\b"
        )

        block_pattern = re.compile(
            r"^(?:if|elif|else|for|while|try|except|finally|with|"
            r"async\s+for|async\s+with|match|case)\b"
        )

        for index, line in enumerate(lines):

            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("#"):
                continue

            indentation = self._indentation(
                line[:len(line) - len(line.lstrip())]
            )

            if stripped.startswith("@"):
                continue

            is_structure = bool(structure_pattern.match(stripped))
            is_block = bool(block_pattern.match(stripped))

            if not is_structure and not is_block:
                continue

            header_lines = [stripped]

            bracket_count = (
                    stripped.count("(")
                    + stripped.count("[")
                    + stripped.count("{")
                    - stripped.count(")")
                    - stripped.count("]")
                    - stripped.count("}")
            )

            current_index = index

            while bracket_count > 0 and current_index + 1 < len(lines):

                current_index += 1
                next_line = lines[current_index].strip()

                header_lines.append(next_line)

                bracket_count += (
                        next_line.count("(")
                        + next_line.count("[")
                        + next_line.count("{")
                        - next_line.count(")")
                        - next_line.count("]")
                        - next_line.count("}")
                )

            full_header = " ".join(header_lines)

            if not full_header.rstrip().endswith(":"):
                continue

            last_code_line = current_index

            for line_index in range(current_index + 1, len(lines)):

                current_line = lines[line_index]

                if not current_line.strip():
                    continue

                if current_line.lstrip().startswith("#"):
                    continue

                current_indent = self._indentation(
                    current_line[:len(current_line) - len(current_line.lstrip())]
                )

                if current_indent <= indentation:
                    break

                last_code_line = line_index

            end = last_code_line + 1

            if end <= index + 1:
                continue

            if is_structure:

                name_match = re.search(
                    r"\b(?:async\s+)?(def|class)\s+(\w+)",
                    full_header
                )

                if name_match:
                    kind = name_match.group(1)
                    name = name_match.group(2)

                    fold_id = f"{kind}:{name}:{index + 1}"

                else:
                    fold_id = f"structure:{index + 1}"

            else:
                fold_id = f"block:{index + 1}"

            self._add_fold(
                index + 1,
                end,
                fold_id
            )

    def _analyze_java(self, lines):

        brace_stack = []

        in_block_comment = False

        for line_index, line in enumerate(lines):

            cleaned = ""
            in_string = None
            escaped = False
            i = 0

            while i < len(line):

                char = line[i]
                next_char = line[i + 1] if i + 1 < len(line) else ""

                if in_block_comment:
                    if char == "*" and next_char == "/":
                        in_block_comment = False
                        i += 2
                        continue

                    i += 1
                    continue

                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == in_string:
                        in_string = None

                    i += 1
                    continue

                if char == "/" and next_char == "/":
                    break

                if char == "/" and next_char == "*":
                    in_block_comment = True
                    i += 2
                    continue

                if char in ('"', "'"):
                    in_string = char
                    i += 1
                    continue

                cleaned += char
                i += 1

            for char in cleaned:

                if char == "{":

                    brace_stack.append(line_index + 1)

                elif char == "}":

                    if not brace_stack:
                        continue

                    start = brace_stack.pop()

                    if lines[start - 1].strip() == "{":
                        start -= 1
                    end = line_index + 1

                    if end > start:
                        header = lines[start - 1].strip()

                        name_match = re.search(
                            r"\b(class|interface|enum|record)\s+(\w+)",
                            header
                        )

                        if name_match:
                            fold_id = (
                                f"{name_match.group(1)}:"
                                f"{name_match.group(2)}:{start}"
                            )
                        else:
                            fold_id = f"java:block:{start}"

                        self._add_fold(start, end, fold_id)

    def _add_fold(self, start, end, fold_id):

        fold = (start, end)

        if fold not in self.folds:
            self.folds.append(fold)
            self.fold_ids[fold] = fold_id

    @staticmethod
    def _indentation(text):

        return len(
            text.expandtabs(4)
        )