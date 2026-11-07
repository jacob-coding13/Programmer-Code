class CompletionModel:

    def __init__(self):
        self.words = set()
        self.variables = set()
        self.context_words = set()

        self.type_methods = {
            "str": [
                "capitalize", "casefold", "center", "count",
                "encode", "endswith", "find", "format",
                "index", "isalnum", "isalpha", "isdigit",
                "islower", "isspace", "istitle", "isupper",
                "join", "lower", "lstrip", "replace", "rfind",
                "rindex", "rstrip", "split", "splitlines",
                "startswith", "strip", "swapcase", "title",
                "upper", "zfill",
            ],

            "list": [
                "append", "clear", "copy", "count", "extend",
                "index", "insert", "pop", "remove", "reverse",
                "sort",
            ],

            "dict": [
                "clear", "copy", "fromkeys", "get", "items",
                "keys", "pop", "popitem", "setdefault",
                "update", "values",
            ],

            "set": [
                "add", "clear", "copy", "difference",
                "discard", "intersection", "isdisjoint",
                "issubset", "issuperset", "pop", "remove",
                "symmetric_difference", "union", "update",
            ],

            "tuple": [
                "count", "index",
            ],
        }

    def add_words(self, words):
        for word in words:
            if isinstance(word, str) and word:
                self.words.add(word)

    def add_variable(self, name):
        if isinstance(name, str) and name:
            self.variables.add(name)

    def add_context_words(self, words):
        self.context_words.clear()

        for word in words:
            if isinstance(word, str) and word:
                self.context_words.add(word)

    def clear_variables(self):
        self.variables.clear()

    def clear_context_words(self):
        self.context_words.clear()

    def search(self, prefix):
        prefix = str(prefix)

        if not prefix:
            return []

        if self.context_words:
            candidates = self.context_words

        else:
            candidates = self.words | self.variables

        prefix_lower = prefix.lower()

        results = [
            word
            for word in candidates
            if word.lower().startswith(prefix_lower)
        ]

        def ranking(word):
            return (
                word.lower() != prefix_lower,
                not word.startswith(prefix),
                word not in self.variables,
                len(word),
                word.lower()
            )

        results.sort(key=ranking)

        return results

    def methods_for_type(self, type_name):
        return self.type_methods.get(type_name, [])