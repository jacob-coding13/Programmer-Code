import copy
import json
from pathlib import Path

class Settings:

    DEFAULTS = {
        "language": {"current": "en"},
        "appearance": {
            "theme": "Dark",
            "ui_font_family": "Segoe UI",
            "ui_font_size": 9,
            "ui_scale": 1.0,
            "animations": True,
        },
        "editor": {
            "scroll_speed": 1.0,
            "font_family": "Consolas",
            "font_size": 12,
            "tab_size": 4,
            "syntax_highlighting": True,
            "line_numbers": True,
            "autocomplete": True,
            "autocomplete_parentheses": True,
            "auto_brackets": True,
            "highlight_current_line": True,
            "show_whitespace": False,
            "word_wrap": False,
            "auto_indent": True,
            "highlight_matching_brackets": True,
            "highlight_selection": True,
            "show_indentation_guides": True,
            "error_underline_width": 1,
            "warning_underline_width": 1,
            "minimap": True,
        },
        "terminal": {
            "font_family": "Consolas",
            "font_size": 11,
            "append_output": True,
            "background": "#1e1e1e",
            "foreground": "#ffffff",
            "output_color": "#ffffff",
            "error_color": "#ff5555",
            "success_color": "#55ff55",
            "warning_color": "#ffcc00",
            "auto_scroll": True,
            "clear_before_run": False,
            "max_lines": 10000,
            "timestamp": False,
            "show_runtime": True,
            "show_exit_code": True,
        },
        "files": {
            "auto_save": True,
            "auto_save_interval": 30,
            "smart_save": False,
            "restore_tabs": True,
            "restore_cursor": True,
        },
        "python": {
            "interpreter": "python",
            "analysis_enabled": True,
            "warnings_enabled": True,
            "live_analysis": True,
        },
        "session": {
            "open_tabs": [],
            "current_tab": 0,
            "cursor_positions": {},
        },
        "advanced": {
            "developer_mode": False,
            "logging": False,
        },
    }

    _COMPATIBILITY = {
        "language": "language.current",
        "theme": "appearance.theme",
        "ui_font_family": "appearance.ui_font_family",
        "ui_font_size": "appearance.ui_font_size",
        "ui_scale": "appearance.ui_scale",
        "animations": "appearance.animations",
        "scroll_speed": "editor.scroll_speed",
        "editor_font_family": "editor.font_family",
        "editor_font_size": "editor.font_size",
        "tab_size": "editor.tab_size",
        "syntax_highlighting": "editor.syntax_highlighting",
        "line_numbers": "editor.line_numbers",
        "autocomplete": "editor.autocomplete",
        "autocomplete_parentheses": "editor.autocomplete_parentheses",
        "auto_brackets": "editor.auto_brackets",
        "live_analysis": "python.live_analysis",
        "highlight_current_line": "editor.highlight_current_line",
        "show_whitespace": "editor.show_whitespace",
        "word_wrap": "editor.word_wrap",
        "auto_indent": "editor.auto_indent",
        "highlight_matching_brackets": "editor.highlight_matching_brackets",
        "highlight_selection": "editor.highlight_selection",
        "show_indentation_guides": "editor.show_indentation_guides",
        "minimap": "editor.minimap",
        "terminal_font_family": "terminal.font_family",
        "terminal_font_size": "terminal.font_size",
        "terminal_append_output": "terminal.append_output",
        "terminal_background": "terminal.background",
        "terminal_foreground": "terminal.foreground",
        "terminal_output_color": "terminal.output_color",
        "terminal_error_color": "terminal.error_color",
        "terminal_success_color": "terminal.success_color",
        "terminal_warning_color": "terminal.warning_color",
        "terminal_auto_scroll": "terminal.auto_scroll",
        "terminal_clear_before_run": "terminal.clear_before_run",
        "terminal_max_lines": "terminal.max_lines",
        "terminal_timestamp": "terminal.timestamp",
        "auto_save": "files.auto_save",
        "auto_save_interval": "files.auto_save_interval",
        "smart_save": "files.smart_save",
        "restore_tabs": "files.restore_tabs",
        "restore_cursor": "files.restore_cursor",
        "python_interpreter": "python.interpreter",
        "python_analysis_enabled": "python.analysis_enabled",
        "python_warnings_enabled": "python.warnings_enabled",
        "open_tabs": "session.open_tabs",
        "current_tab": "session.current_tab",
        "cursor_positions": "session.cursor_positions",
        "developer_mode": "advanced.developer_mode",
        "logging": "advanced.logging",
    }

    def __init__(self, path=None):
        self.path = Path(path) if path else Path(__file__).parent / "settings_ProgrammerCode.json"
        self.data = copy.deepcopy(self.DEFAULTS)
        self.load()

    def get(self, key, default=None):
        keys = key.split(".")
        curr = self.data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return default
        return curr

    def set(self, key, value, save_immediately=True):
        keys = key.split(".")
        curr = self.data

        for k in keys[:-1]:
            if k not in curr or not isinstance(curr[k], dict):
                curr[k] = {}
            curr = curr[k]

        if key == "language.current":
            if hasattr(value, "code"):
                value = str(value.code)
            elif hasattr(value, "name"):
                value = str(value.name).lower()
            else:
                value = str(value).lower()

        curr[keys[-1]] = value

        if save_immediately:
            self.save()

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as file:
                json.dump(self.data, file, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Settings Error] Fehler beim Speichern: {e}")

    def load(self):
        if not self.path.exists():
            self.save()
            return

        try:
            with open(self.path, "r", encoding="utf-8") as file:
                loaded = json.load(file)
                self._merge_dicts(self.data, loaded)
        except Exception as e:
            print(f"[Settings Error] Fehler beim Laden: {e}")
            self.save()

    def _merge_dicts(self, target, source):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dicts(target[key], value)
            else:
                target[key] = value

    def __getattr__(self, name):
        if name in self._COMPATIBILITY:
            return self.get(self._COMPATIBILITY[name])
        if "data" in self.__dict__ and name in self.data:
            return self.data[name]
        raise AttributeError(f"'Settings' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name in {"path", "data", "DEFAULTS", "_COMPATIBILITY"} or "data" not in self.__dict__:
            object.__setattr__(self, name, value)
            return

        if name in self._COMPATIBILITY:
            self.set(self._COMPATIBILITY[name], value, save_immediately=True)
            return

        object.__setattr__(self, name, value)