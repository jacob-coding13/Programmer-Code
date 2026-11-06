import json
import sys
from pathlib import Path


class LanguageManager:

    def __init__(self, language="en"):

        self.language = language
        self.data = {}
        self.fallback_data = {}
        self.programming_languages = {}

        if getattr(sys, "frozen", False):
            self.base_path = (
                    Path(sys.executable).parent / "_internal"
            )
        else:
            self.base_path = Path(__file__).parent

        # UI-Übersetzungen laden
        ui_path = self.base_path / "languages" / "ui"

        fallback_path = ui_path / "en.json"

        if fallback_path.is_file():
            try:
                self.fallback_data = json.loads(
                    fallback_path.read_text(
                        encoding="utf-8"
                    )
                )
            except (json.JSONDecodeError, OSError):
                self.fallback_data = {}

        lang_path = ui_path / f"{language}.json"

        if lang_path.is_file():
            try:
                self.data = json.loads(
                    lang_path.read_text(
                        encoding="utf-8"
                    )
                )
            except (json.JSONDecodeError, OSError):
                self.data = {}
        else:
            self.data = self.fallback_data

        # Programmiersprachen separat laden
        self.load_programming_languages()

    def get(self, key):

        return self.data.get(
            key,
            self.fallback_data.get(
                key,
                key
            )
        )

    def get_programming_language(self, extension):

        extension = extension.lower()

        if not extension.startswith("."):
            extension = "." + extension

        for language in self.programming_languages.values():

            extensions = language.get(
                "extensions",
                []
            )

            if extension in extensions:
                return language

        return None

    def load_programming_languages(self):

        self.programming_languages = {}

        languages_path = (
                self.base_path
                / "languages"
                / "programming"
        )

        if not languages_path.is_dir():
            return

        for file in languages_path.glob("*.json"):

            try:
                language = json.loads(
                    file.read_text(
                        encoding="utf-8"
                    )
                )

                name = language.get(
                    "name",
                    file.stem
                )

                self.programming_languages[name] = language

            except (json.JSONDecodeError, OSError):
                continue