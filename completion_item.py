class CompletionItem:
    def __init__(self, text, kind="Variable"):
        self.text = text
        self.kind = kind

    def __str__(self):
        return self.text