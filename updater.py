import shutil
import subprocess
import sys
import time
from pathlib import Path


def update_application(
        old_directory,
        new_directory,
        executable_name
):
    old_directory = Path(old_directory)
    new_directory = Path(new_directory)

    executable_name = Path(executable_name).name

    backup_directory = old_directory.parent / (
            old_directory.name + "_old"
    )

    user_files = old_directory / "ProgrammerCodeFiles"

    # Alte Installation umbenennen
    for _ in range(30):
        try:
            old_directory.rename(backup_directory)
            break

        except PermissionError:
            time.sleep(1)

    else:
        return

    try:
        # Neue Programmdateien an die Stelle der alten Installation setzen
        new_directory.rename(old_directory)

        # Benutzerdateien aus der alten Installation zurückholen
        if user_files.exists():
            target = old_directory / "ProgrammerCodeFiles"

            if not target.exists():
                user_files.rename(target)

        executable = old_directory / executable_name

        subprocess.Popen(
            [str(executable)],
            cwd=str(old_directory)
        )

        time.sleep(2)

        # Alte Installation löschen
        shutil.rmtree(
            backup_directory,
            ignore_errors=True
        )

    except Exception:
        # Falls etwas schiefgeht: alte Installation wiederherstellen
        try:
            if old_directory.exists():
                shutil.rmtree(
                    old_directory,
                    ignore_errors=True
                )

            backup_directory.rename(
                old_directory
            )

        except Exception:
            pass


if __name__ == "__main__":

    if len(sys.argv) != 4:
        sys.exit(1)

    update_application(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3]
    )