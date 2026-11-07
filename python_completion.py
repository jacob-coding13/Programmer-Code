import jedi

class PythonCompletion:

    def __init__(self):
        self.enabled = True

    def get_completions(self, source, line, column, path=None):

        if not self.enabled:
            return []

        try:
            script = jedi.Script(
                code=source,
                path=path
            )

            completions = script.complete(
                line=line,
                column=column
            )

            results = []

            for completion in completions:
                name = completion.name

                if name and name not in results:
                    results.append(name)

            return results

        except Exception as error:
            print("Jedi error:", error)
            return []