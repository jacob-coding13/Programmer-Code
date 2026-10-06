import ast

class Breadcrumb:

    def __init__(self):
        self.path = []

    def update(self, editor):
        code = editor.toPlainText()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            self.path.clear()
            return

        visible_block = editor.firstVisibleBlock()
        current_line = visible_block.blockNumber() + 1

        self.path.clear()

        def visit(node):
            if not hasattr(node, "lineno"):
                return

            end_line = getattr(
                node,
                "end_lineno",
                node.lineno
            )

            if not (node.lineno <= current_line <= end_line):
                return

            if isinstance(node,
                          (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                self.path.append(node.name)

            for child in ast.iter_child_nodes(node):
                visit(child)

        for node in tree.body:
            visit(node)