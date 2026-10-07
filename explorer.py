import sys
from pathlib import Path

from PySide6.QtCore import Signal, QItemSelectionModel, QDir
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFileSystemModel,
    QTreeView,
    QFileIconProvider,
)


class ProgrammerCodeIconProvider(QFileIconProvider):

    def __init__(self):
        super().__init__()

        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent / "_internal"
        else:
            base_dir = Path(__file__).parent

        icon_path = (
                base_dir
                / "resources"
                / "icons"
                / "programmer_code.png"
        )

        self.programmer_icon = QIcon(str(icon_path))

    def icon(self, info):
        if info.isFile():
            if info.suffix().lower() == "py":
                return self.programmer_icon

        return super().icon(info)

class Explorer(QTreeView):

    file_opened = Signal(str)

    def __init__(self):
        super().__init__()

        self.file_model = QFileSystemModel()

        self.file_model.setFilter(
            QDir.AllEntries | QDir.NoDotAndDotDot
        )

        self.file_model.setIconProvider(
            ProgrammerCodeIconProvider()
        )

        self.file_model.directoryLoaded.connect(
            self._on_directory_loaded
        )

        self.setModel(self.file_model)

        self.setColumnHidden(1, True)
        self.setColumnHidden(2, True)
        self.setColumnHidden(3, True)
        self.setHeaderHidden(True)

        self.doubleClicked.connect(
            self.on_double_clicked
        )

        self._current_path = ""

    def set_folder(self, path):
        abs_path = str(Path(path).resolve())
        self._current_path = abs_path

        root_index = self.file_model.setRootPath(
            abs_path
        )

        if root_index.isValid():
            self.setRootIndex(root_index)

    def _on_directory_loaded(self, path):
        if (
                self._current_path
                and Path(path) == Path(self._current_path)
        ):
            index = self.file_model.index(
                self._current_path
            )

            if index.isValid():
                self.setRootIndex(index)

    def on_double_clicked(self, index):
        path = Path(
            self.file_model.filePath(index)
        )

        if path.is_file():
            self.file_opened.emit(str(path))

    def select_file(self, path):
        path_str = str(
            Path(path).resolve()
        )

        index = self.file_model.index(path_str)

        if not index.isValid():
            return

        self.setCurrentIndex(index)

        self.selectionModel().select(
            index,
            QItemSelectionModel.ClearAndSelect
            | QItemSelectionModel.Rows
        )

        self.scrollTo(index)