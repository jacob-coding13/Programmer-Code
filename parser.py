import ast

class PythonParser:

    def __init__(self):
        self.tree = None

    def parse(self, path):

        with open(
                path,
                "r",
                encoding="utf-8"
        ) as file:

            source = file.read()

        self.tree = ast.parse(source)

        return self.extract()

    def extract(self):
        result = []

        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                class_item = {
                    "type": "class",
                    "name": node.name,
                    "line": node.lineno,
                    "children": []
                }

                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        class_item["children"].append({
                            "type": "function",
                            "name": child.name,
                            "line": child.lineno
                        })

                result.append(class_item)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result.append({
                    "type": "function",
                    "name": node.name,
                    "line": node.lineno
                })

        return result