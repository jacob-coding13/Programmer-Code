import json
from pathlib import Path

class LanguageManager:

    def __init__(self, language="en"):
        self.language = language
        self.data = {}
        self.fallback_data = {}

        base_dir = Path(__file__).parent / "languages"

        fallback_path = base_dir / "en.json"
        if fallback_path.is_file():
            try:
                self.fallback_data = json.loads(
                    fallback_path.read_text(encoding="utf-8")
                )
            except json.JSONDecodeError:
                self.fallback_data = {}

        lang_path = base_dir / f"{language}.json"
        if lang_path.is_file():
            try:
                self.data = json.loads(lang_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self.data = {}
        else:
            self.data = self.fallback_data

    def get(self, key):
        return self.data.get(key, self.fallback_data.get(key, key))