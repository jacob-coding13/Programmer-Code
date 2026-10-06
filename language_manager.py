import json
import sys
from pathlib import Path
class LanguageManager:

    def __init__(self, language="en"):
        self.language = language
        self.data = {}
        self.fallback_data = {}

        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent

        languages_dir = base_dir / "languages"

        fallback_path = languages_dir / "en.json"

        if fallback_path.is_file():
            try:
                self.fallback_data = json.loads(
                    fallback_path.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                    json.JSONDecodeError,
                    OSError,
            ):
                self.fallback_data = {}

        lang_path = languages_dir / f"{language}.json"

        if lang_path.is_file():
            try:
                self.data = json.loads(
                    lang_path.read_text(
                        encoding="utf-8"
                    )
                )
            except (
                    json.JSONDecodeError,
                    OSError,
            ):
                self.data = {}
        else:
            self.data = self.fallback_data

    def get(self, key):
        return self.data.get(
            key,
            self.fallback_data.get(key, key)
        )