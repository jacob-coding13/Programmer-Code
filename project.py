from pathlib import Path

class Project:

    def __init__(self, settings=None, lang_manager=None):
        self.path = None
        self.settings = settings
        self.lang = lang_manager

    def open(self, path):
        p = Path(path)
        if p.exists() and p.is_dir():
            self.path = p
            return True
        return False

    def create(self, parent, name):
        project_path = Path(parent) / name
        project_path.mkdir(parents=True, exist_ok=True)

        main_file = project_path / "main.py"
        if not main_file.exists():
            main_file.write_text('print("Hello ProgrammerCode!")\n', encoding="utf-8")

        readme_file = project_path / "README.md"
        if not readme_file.exists():
            readme_file.write_text(f"# {name}\n", encoding="utf-8")

        (project_path / ".proco").mkdir(exist_ok=True)

        self.path = project_path
        return self.path

    @property
    def name(self):
        if self.path:
            return self.path.name
        if self.lang:
            return self.lang.get("no_project")
        return "Unbenanntes Projekt"