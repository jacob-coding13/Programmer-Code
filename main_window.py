from pathlib import Path
from sys import path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QToolBar
)

from editor_tabs import EditorTabs
from explorer import Explorer
from find_dialog import FindDialog
from language_manager import LanguageManager
from outline import Outline
from project import Project
from developer_mode import is_developer_machine
from settings_dialog import SettingsDialog
from terminal import Terminal
from theme_manager import get_app_style

class MainWindow(QMainWindow):

    def __init__(self, settings):
        super().__init__()

        self.settings = settings
        self.lang = LanguageManager(self.settings.language)
        self.project = Project()

        self.editor_tabs = EditorTabs(self.settings)

        self.explorer = Explorer()
        self.outline = Outline(self.settings)
        self.terminal = Terminal(self.settings)

        default_project_dir = Path(__file__).parent.resolve()
        self.project.open(str(default_project_dir))
        self.editor_tabs.load_file_states(
            self.project.path / ".programmer_code_folds.json"
        )

        self.setWindowTitle(f"Programmer Code - {self.project.name}")
        self.explorer.set_folder(str(self.project.path))

        self.setup_signals()

        self.create_menu()
        self.create_toolbar()
        self.create_statusbar()
        self.setup_layout()
        self.restore_tabs()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.auto_save_files)

        if self.settings.auto_save and not self.settings.smart_save:
            self.timer.start(self.settings.auto_save_interval * 1000)

        self.showMaximized()

        QTimer.singleShot(
            100,
            self.update_all_sticky_lines
        )

    def setup_signals(self):
        self.outline.item_clicked.connect(self.jump_to_line)
        self.terminal.finished.connect(self.program_finished)
        self.explorer.file_opened.connect(self.open_file)
        self.editor_tabs.currentChanged.connect(self.current_tab_changed)
        self.editor_tabs.run_requested.connect(self.run_current_file)

    def setup_layout(self):
        left = QSplitter(Qt.Vertical)
        left.addWidget(self.explorer)
        left.addWidget(self.outline)
        left.setSizes([500, 300])

        horizontal = QSplitter(Qt.Horizontal)
        horizontal.addWidget(left)
        horizontal.addWidget(self.editor_tabs)
        horizontal.setSizes([250, 700, 250])

        vertical = QSplitter(Qt.Vertical)
        vertical.addWidget(horizontal)
        vertical.addWidget(self.terminal)
        vertical.setSizes([600, 200])

        self.setCentralWidget(vertical)

    def auto_save_files(self):
        if not self.settings.auto_save or self.settings.smart_save:
            return

        editor = self.editor_tabs.current_editor()
        if editor and getattr(editor, "modified", False) and getattr(editor, "current_file", None):
            editor.save_file()
            self.statusBar().showMessage(self.lang.get("auto_saved"), 1500)

    def create_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu(self.lang.get("file"))

        new_file_act = file_menu.addAction(self.lang.get("new_file"))
        new_file_act.setShortcut(QKeySequence.New)
        new_file_act.triggered.connect(self.editor_tabs.new_file)

        new_project_act = file_menu.addAction(self.lang.get("new_project"))
        new_project_act.triggered.connect(self.new_project)

        open_act = file_menu.addAction(self.lang.get("open"))
        open_act.setShortcut(QKeySequence.Open)
        open_act.triggered.connect(self.open_file_dialog)

        save_act = file_menu.addAction(self.lang.get("save"))
        save_act.setShortcut(QKeySequence.Save)
        save_act.triggered.connect(self.save_file)

        save_as_act = file_menu.addAction(self.lang.get("save_as"))
        save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_act.triggered.connect(self.save_as)

        file_menu.addSeparator()

        settings_act = file_menu.addAction(self.lang.get("settings"))
        settings_act.triggered.connect(self.show_settings)

        file_menu.addSeparator()

        exit_act = file_menu.addAction(self.lang.get("exit"))
        exit_act.setShortcut(QKeySequence.Quit)
        exit_act.triggered.connect(self.close)

        if is_developer_machine():
            developer_menu = menu.addMenu("Developer")

            developer_menu.addAction(
                "Developer Mode",
                self.show_developer_info
            )

            developer_menu.addSeparator()

            developer_menu.addAction(
                "Update veröffentlichen",
                self.publish_update
            )

    def create_toolbar(self):
        toolbar = QToolBar(self.lang.get("main_toolbar"))
        self.addToolBar(toolbar)

        toolbar.addAction(self.lang.get("new"), self.editor_tabs.new_file)
        toolbar.addAction(self.lang.get("project"), self.new_project)
        toolbar.addSeparator()
        toolbar.addAction(self.lang.get("open"), self.open_file_dialog)
        toolbar.addAction(self.lang.get("save"), self.save_file)
        toolbar.addSeparator()

        run_str = self.lang.get("run")
        toolbar.addAction(f"▶ {run_str}", self.run_current_file)
        toolbar.addSeparator()

        settings_str = self.lang.get("settings")
        toolbar.addAction(f"\u2699\uFE0E {settings_str}", self.show_settings)

    def create_statusbar(self):
        self.statusBar().showMessage(self.lang.get("ready"))

    def open_file(self, path):
        self.editor_tabs.open_file(path)
        self.outline.load_file(path)
        editor = self.editor_tabs.current_editor()

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, self.lang.get("open_file"))
        if path:
            self.open_file(path)

    def save_file(self):
        self.editor_tabs.save_current()
        self.statusBar().showMessage(self.lang.get("file_saved"), 2000)

    def save_as(self):
        editor = self.editor_tabs.current_editor()
        if editor is None:
            return

        start_path = str(self.project.path)
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.lang.get("save_file_as"),
            f"{start_path}/untitled.py",
            "Python Files (*.py);;All Files (*)"
        )

        if not path:
            return

        editor.current_file = path
        editor.save_file()

        index = self.editor_tabs.currentIndex()
        self.editor_tabs.setTabText(index, Path(path).name)
        self.statusBar().showMessage(self.lang.get("file_saved"), 2000)

    def new_project(self):
        name, ok = QInputDialog.getText(
            self,
            self.lang.get("new_project"),
            self.lang.get("project_name")
        )

        if not ok or not name.strip():
            return

        parent = Path.home() / "Programmer_Code_Projects"
        parent.mkdir(parents=True, exist_ok=True)

        self.project.create(str(parent), name.strip())
        self.open_project(str(self.project.path))

    def open_project(self, path):
        self.project.open(path)
        self.explorer.set_folder(str(self.project.path))
        self.setWindowTitle(f"PythonX - {self.project.name}")

    def run_current_file(self):
        self.editor_tabs.run_current(self.terminal)

    def program_finished(self):
        self.statusBar().showMessage(self.lang.get("finished"), 3000)

    def jump_to_line(self, line):
        editor = self.editor_tabs.current_editor()
        if editor:
            editor.jump_to_line(line)

    def show_settings(self):
        old_language = self.settings.language
        dialog = SettingsDialog(self.settings)

        if dialog.exec():
            self.settings.save()
            self.apply_settings()

            if old_language != self.settings.language:
                self.reload_language()

            self.statusBar().showMessage(self.lang.get("settings_updated"), 2000)

    def apply_settings(self):
        font = QFont(
            self.settings.editor_font_family,
            int(self.settings.editor_font_size * self.settings.ui_scale)
        )
        self.setFont(font)

        QApplication.instance().setStyleSheet(get_app_style(self.settings))

        for i in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(i)
            if editor:
                editor.settings = self.settings
                editor.apply_settings()

        self.terminal.settings = self.settings
        self.terminal.apply_settings()

        self.explorer.update()
        self.outline.update()

        self.timer.stop()
        if self.settings.auto_save and not self.settings.smart_save:
            self.timer.start(self.settings.auto_save_interval * 1000)

        self.update()

    def save_open_tabs_state(self):
        self.settings.open_tabs = []
        self.settings.cursor_positions = {}

        for i in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(i)
            if getattr(editor, "current_file", None):
                path = editor.current_file
                self.settings.open_tabs.append(path)
                self.settings.cursor_positions[path] = {
                    "cursor": editor.textCursor().position(),
                    "scroll": editor.verticalScrollBar().value()
                }

        self.settings.current_tab = self.editor_tabs.currentIndex()

    def update_all_sticky_lines(self):
        for i in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(i)

            if editor:
                editor.update_sticky_lines()
                editor.viewport().update()

    def restore_tabs(self):
        for path in self.settings.open_tabs:
            if not Path(path).exists():
                continue

            self.editor_tabs.open_file(path)
            editor = self.editor_tabs.current_editor()

            if (
                    self.settings.restore_cursor
                    and path in self.settings.cursor_positions
                    and editor
            ):
                data = self.settings.cursor_positions[path]

                cursor = editor.textCursor()
                cursor.setPosition(data["cursor"])
                editor.setTextCursor(cursor)

                editor.verticalScrollBar().setValue(data["scroll"])

                QTimer.singleShot(
                    0,
                    editor.update_sticky_lines
                )

                QTimer.singleShot(
                    0,
                    editor.viewport().update
                )

        if self.editor_tabs.count() > 0:
            index = min(
                self.settings.current_tab,
                self.editor_tabs.count() - 1
            )
            self.editor_tabs.setCurrentIndex(max(0, index))

    def closeEvent(self, event):
        for i in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(i)

            if not editor or not getattr(editor, "modified", False):
                continue

            self.editor_tabs.setCurrentIndex(i)

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
                    event.ignore()
                    return

            elif answer == QMessageBox.Cancel:
                event.ignore()
                return

        if self.settings.restore_tabs:
            self.save_open_tabs_state()

        self.editor_tabs.save_fold_states(
            self.project.path / ".programmer_code_folds.json"
        )

        self.settings.save()
        event.accept()

    def reload_language(self):
        self.lang = LanguageManager(self.settings.language)
        self.menuBar().clear()
        self.create_menu()

        for toolbar in self.findChildren(QToolBar):
            self.removeToolBar(toolbar)
            toolbar.deleteLater()

        self.create_toolbar()
        self.setWindowTitle(f"Programmer Code - {self.project.name}")
        self.statusBar().showMessage(self.lang.get("ready"))

        self.terminal.reload_language()
        self.editor_tabs.reload_language()
        self.outline.reload_language()
        self.current_tab_changed()

    def current_tab_changed(self):
        editor = self.editor_tabs.current_editor()

        if editor is None:
            return

        if getattr(editor, "current_file", None):
            self.explorer.select_file(editor.current_file)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_P:
            try:
                from command_palette import CommandPalette
                cmds = [
                    self.lang.get("run_file"),
                    self.lang.get("save"),
                    self.lang.get("search"),
                    self.lang.get("optimize"),
                    self.lang.get("find_bugs")
                ]
                dialog = CommandPalette(cmds, self.lang)
                dialog.exec()
            except ImportError:
                pass
            return
        super().keyPressEvent(event)

    def show_developer_info(self):
        QMessageBox.information(
            self,
            "Developer Mode",
            "Dieser Rechner ist als Entwickler-Rechner erkannt."
        )

    def publish_update(self):
        QMessageBox.information(
            self,
            "Update",
            "Update-System wird vorbereitet."
        )