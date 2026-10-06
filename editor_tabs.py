import json
from os import stat_result
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QMessageBox
from editor import Editor
from language_manager import LanguageManager

class EditorTabs(QTabWidget):

    run_requested = Signal()

    def __init__(self, settings):
        super().__init__()

        self.settings = settings
        self.lang = LanguageManager(self.settings.language)
        self.untitled_count = 0
        self.fold_states = {}

        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.close_tab)

    def open_file(self, path):
        path_str = str(Path(path).resolve())

        for i in range(self.count()):
            editor = self.widget(i)

            if editor.current_file == path_str:
                self.setCurrentIndex(i)
                return

        editor = Editor(self.settings)
        editor.load_file(path_str)

        editor.folding.analyze(editor.toPlainText())

        editor.restore_fold_state(
            self.fold_states.get(path_str, [])
        )

        filename = Path(path_str).name

        index = self.addTab(editor, filename)

        editor.modified_changed.connect(
            lambda changed, ed=editor:
            self.update_tab_by_editor(ed, changed)
        )

        editor.run_requested.connect(self.run_requested)

        self.setCurrentWidget(editor)

    def current_editor(self):
        return self.currentWidget()

    def close_tab(self, index):
        editor = self.widget(index)

        if editor is None:
            return

        if getattr(editor, "modified", False):
            answer = QMessageBox.question(
                self,
                self.lang.get("unsaved_changes"),
                self.lang.get("file_has_been_changed_save"),
                QMessageBox.Save |
                QMessageBox.Discard |
                QMessageBox.Cancel
            )

            if answer == QMessageBox.Save:
                if not editor.save_file():
                    return

            elif answer == QMessageBox.Cancel:
                return

        if editor.current_file:
            self.fold_states[editor.current_file] = (
                editor.get_fold_state()
            )

        self.removeTab(index)
        editor.deleteLater()

    def save_current(self):
        editor = self.current_editor()
        if editor:
            editor.save_file()

    def update_tab_by_editor(self, editor, changed):
        index = self.indexOf(editor)
        if index == -1:
            return

        filename = self.tabText(index)

        if changed:
            if not filename.endswith("*"):
                self.setTabText(index, filename + "*")
        else:
            self.setTabText(index, filename.replace("*", ""))

    def save_fold_states(self, path):
        data = {}

        for i in range(self.count()):
            editor = self.widget(i)

            if editor and editor.current_file:
                data[editor.current_file] = editor.get_fold_state()

        for file_path, state in self.fold_states.items():
            if file_path not in data:
                data[file_path] = state

        try:
            Path(path).write_text(
                json.dumps(data, indent=4),
                encoding="utf-8"
            )
        except OSError:
            pass

    def load_file_states(self, path):
        path = Path(path)

        if not path.is_file():
            return

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return

        if not isinstance(data, dict):
            return

        self.fold_states = {
            str(file_path): state
            for file_path, state in data.items()
            if isinstance(state, list)
        }

    def run_current(self, terminal):
        editor = self.current_editor()

        if editor is None:
            return

        if editor.modified:
            editor.save_file()

        if not editor.current_file:
            terminal.write(
                f"> {self.lang.get('save_file_before_run')}\n",
                error=True
            )
            return

        terminal.run(editor.current_file)

    def new_file(self):
        editor = Editor(self.settings)
        editor.new_file()

        if self.untitled_count == 0:
            name = self.lang.get("untitled")
        else:
            name = self.lang.get("untitled_number").format(
                number=self.untitled_count
            )

        self.untitled_count += 1

        index = self.addTab(editor, name)

        editor.modified_changed.connect(
            lambda changed, ed=editor: self.update_tab_by_editor(ed, changed)
        )
        editor.run_requested.connect(self.run_requested)

        self.setCurrentIndex(index)

    def reload_language(self):
        self.lang = LanguageManager(self.settings.language)
        for index in range(self.count()):
            editor = self.widget(index)
            editor.reload_language()