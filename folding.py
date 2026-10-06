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

        structure_pattern = re.compile(
            r"^(\s*)(?:async\s+def|def|class)\b"
        )

        block_pattern = re.compile(
            r"^(\s*)(?:if|elif|else|for|while|try|except|finally|with|"
            r"async\s+for|async\s+with)\b.*:\s*(?:#.*)?$"
        )

        headers = []

        for index, line in enumerate(lines):
            if not line.strip():
                continue

            match = structure_pattern.match(line)

            if not match:
                match = block_pattern.match(line)

            if not match:
                continue

            indentation = len(match.group(1).replace("\t", "    "))

            headers.append(
                (
                    index + 1,
                    indentation,
                    line.strip()
                )
            )

        for position, (start, indentation, text) in enumerate(headers):

            end = len(lines)

            for next_start, next_indent, next_text in headers[position + 1:]:

                if next_indent <= indentation:
                    end = next_start - 1
                    break

            if end <= start:
                continue

            fold = (start, end)

            if re.match(
                    r"^(?:async\s+)?def\b",
                    text
            ):
                name_match = re.match(
                    r"^(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)",
                    text
                )

                if name_match:
                    fold_id = f"def:{name_match.group(1)}"
                else:
                    fold_id = f"def:{start}"

            elif re.match(r"^class\b", text):
                name_match = re.match(
                    r"^class\s+([A-Za-z_][A-Za-z0-9_]*)",
                    text
                )

                if name_match:
                    fold_id = f"class:{name_match.group(1)}"
                else:
                    fold_id = f"class:{start}"

            else:
                fold_id = f"block:{start}"

            self.folds.append(fold)
            self.fold_ids[fold] = fold_id

        self.folds.sort(
            key=lambda item: (item[0], -item[1])
        )

        return self.folds