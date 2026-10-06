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
        self.variables.add(name)

    def add_context_words(self, words):
        self.context_words.clear()

        for word in words:
            if isinstance(word, str) and word:
                self.context_words.add(word)

    def search(self, prefix):
        prefix = prefix.lower()

        if self.context_words:
            results = [
                word
                for word in self.context_words
                if word.lower().startswith(prefix)
            ]

            results.sort(key=lambda w: (len(w), w.lower()))
            return results

        results = []

        for word in self.variables | self.words:
            if word.lower().startswith(prefix):
                results.append(word)

        results.sort(
            key=lambda w: (
                not (w in self.variables),
                len(w),
                w.lower()
            )
        )

        return results

    def methods_for_type(self, type_name):
        return self.type_methods.get(type_name, [])