from __future__ import annotations

import json
import sys
from pathlib import Path


class LanguageManager:
    """Verwaltet UI-Übersetzungen und Programmiersprachen-Definitionen."""

    def __init__(self, language="en", base_path=None):
        self.language = language
        self.data = {}
        self.fallback_data = {}
        self.programming_languages = {}
        self.base_path = Path(base_path) if base_path else self._get_base_path()
        self.languages_path = self.base_path / "languages"
        self.ui_path = self.languages_path / "ui"
        self.programming_path = self.languages_path / "programming"
        self.load_ui_language(language)
        self.load_programming_languages()

    @staticmethod
    def _get_base_path():
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            internal = exe_dir / "_internal"
            if internal.is_dir():
                return internal
            meipass = getattr(sys, "_MEIPASS", None)
            return Path(meipass) if meipass else exe_dir
        return Path(__file__).resolve().parent

    @staticmethod
    def _read_json(path):
        try:
            with Path(path).open("r", encoding="utf-8") as file:
                value = json.load(file)
            return value if isinstance(value, dict) else {}
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}

    def load_ui_language(self, language=None):
        if language:
            self.language = language
        self.fallback_data = self._read_json(self.ui_path / "en.json")
        self.data = self._read_json(self.ui_path / f"{self.language}.json")
        return self.data

    def set_language(self, language):
        self.load_ui_language(language)

    def get(self, key, default=None, **format_values):
        value = self.data.get(
            key, self.fallback_data.get(
                key, default if default is not None else key
            )
        )
        if isinstance(value, str) and format_values:
            try:
                return value.format(**format_values)
            except (KeyError, ValueError):
                return value
        return value

    def load_programming_languages(self):
        self.programming_languages = {}
        if not self.programming_path.is_dir():
            return self.programming_languages

        for path in sorted(self.programming_path.glob("*.json")):
            definition = self._read_json(path)
            if not definition:
                continue
            language_id = str(definition.get("id") or path.stem).lower()
            name = str(definition.get("name") or path.stem)
            extensions = definition.get("extensions", [])
            if isinstance(extensions, str):
                extensions = [extensions]
            normalized = []
            for extension in extensions:
                extension = str(extension).strip().lower()
                if extension:
                    normalized.append(
                        extension if extension.startswith(".") else "." + extension
                    )
            definition.update({
                "id": language_id,
                "name": name,
                "extensions": normalized
            })
            self.programming_languages[language_id] = definition
            self.programming_languages[name.lower()] = definition
        return self.programming_languages

    def get_programming_language(self, extension):
        extension = str(extension or "").strip().lower()
        if not extension:
            return None
        if not extension.startswith("."):
            extension = "." + extension
        for definition in self.programming_languages.values():
            if extension in definition.get("extensions", []):
                return definition
        return None

    def get_language_id(self, extension):
        definition = self.get_programming_language(extension)
        return definition.get("id") if definition else None

    def get_language_name(self, extension):
        definition = self.get_programming_language(extension)
        return definition.get("name") if definition else None

    def get_supported_extensions(self):
        extensions = {
            ext
            for definition in self.programming_languages.values()
            for ext in definition.get("extensions", [])
        }
        return sorted(extensions)

    def is_supported(self, extension):
        return self.get_programming_language(extension) is not None

    def reload(self):
        self.load_ui_language(self.language)
        self.load_programming_languages()