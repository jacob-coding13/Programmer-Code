import re
import ast

class VariableAnalyzer:

    def __init__(self):
        self.variables = {}

    def analyze(self, code):

        self.variables.clear()

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):

                if isinstance(node, ast.Assign):

                    for target in node.targets:

                        if isinstance(target, ast.Name):
                            self.variables[target.id] = "unknown"

            return

        except SyntaxError:
            pass

        for match in re.finditer(
            r"([A-Za-z_]\w*)\s*=",
            code
        ):
            self.variables[match.group(1)] = "unknown"

    def completions(self):
        return list(self.variables.keys())