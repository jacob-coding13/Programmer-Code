import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

class PythonAnalyzer:
    def analyze(self, code):
        return self._analyze_python(code)

    def analyze_errors(self, code):
        errors, _ = self.analyze(code)
        return errors

    def analyze_warnings(self, code):
        _, warnings = self.analyze(code)
        return warnings

    def _analyze_python(self, code):
        errors = []
        warnings = []
        filename = None

        try:
            with tempfile.NamedTemporaryFile(
                    suffix=".py",
                    delete=False,
                    mode="w",
                    encoding="utf-8",
                    newline="\n",
            ) as file:
                file.write(code)
                filename = file.name

            command = self.get_ruff_command()

            if not command:
                warnings.append(
                    (0, 0, 0, 0, "Ruff wurde nicht gefunden.")
                )
                return errors, warnings

            result = subprocess.run(
                command + [
                    "check",
                    "--output-format=json",
                    "--stdin-filename",
                    filename,
                    "-",
                ],
                input=code,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
                )

            if result.returncode not in (0, 1):
                message = result.stderr.strip() or "Ruff-Analyse fehlgeschlagen."
                warnings.append((0, 0, 0, 0, message))
                return errors, warnings

            try:
                diagnostics = json.loads(result.stdout or "[]")
            except json.JSONDecodeError:
                warnings.append(
                    (0, 0, 0, 0, "Ungültige Antwort von Ruff.")
                )
                return errors, warnings

            for item in diagnostics:
                code_id = item.get("code") or "UNKNOWN"
                location = item.get("location") or {}
                end_location = item.get("end_location") or location

                diagnostic = (
                    max(0, location.get("row", 1) - 1),
                    max(0, location.get("column", 1) - 1),
                    max(0, end_location.get("row", 1) - 1),
                    max(0, end_location.get("column", 1) - 1),
                    f"{code_id}: {item.get('message', 'Unbekannter Fehler')}",
                )

                if self._is_error(item):
                    errors.append(diagnostic)
                else:
                    warnings.append(diagnostic)

        except subprocess.TimeoutExpired:
            warnings.append((0, 0, 0, 0, "Ruff-Analyse hat zu lange gedauert."))
        except OSError as exc:
            warnings.append((0, 0, 0, 0, f"Ruff konnte nicht gestartet werden: {exc}"))
        finally:
            if filename:
                try:
                    Path(filename).unlink(missing_ok=True)
                except OSError:
                    pass

        return errors, warnings

    def _is_error(self, diagnostic):
        code_id = diagnostic.get("code") or ""
        return (
                diagnostic.get("severity") == "error"
                or code_id == "invalid-syntax"
                or code_id == "F821"
                or code_id.startswith("E9")
        )

    def get_ruff_command(self):
        if not getattr(sys, "frozen", False):
            return [sys.executable, "-m", "ruff"]

        base_path = Path(sys.executable).parent
        candidates = [
            base_path / "ruff.exe",
            base_path / "_internal" / "ruff.exe",
            ]

        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "ruff.exe")

        for candidate in candidates:
            if candidate.is_file():
                return [str(candidate)]

        return None


class JavaAnalyzer:

    def __init__(self, checkstyle_jar=None, config_file=None):
        self.checkstyle_jar = (
            Path(checkstyle_jar) if checkstyle_jar else None
        )
        self.config_file = (
            Path(config_file) if config_file else None
        )

    def analyze(self, code):
        errors = []
        warnings = []

        java_errors, java_warnings = self._analyze_javac(code)

        errors.extend(java_errors)
        warnings.extend(java_warnings)

        checkstyle_errors, checkstyle_warnings = (
            self._analyze_checkstyle(code)
        )

        errors.extend(checkstyle_errors)
        warnings.extend(checkstyle_warnings)

        return errors, warnings

    def _analyze_javac(self, code):
        errors = []
        warnings = []

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir = Path(temp_dir)

                # Namen der öffentlichen Klasse ermitteln
                match = re.search(
                    r"\bpublic\s+(?:(?:abstract|final|sealed|"
                    r"non-sealed|strictfp)\s+)*"
                    r"(?:class|interface|enum|record)\s+"
                    r"([A-Za-z_$][\w$]*)",
                    code
                )

                class_name = match.group(1) if match else "Main"

                filename = temp_dir / f"{class_name}.java"

                filename.write_text(
                    code,
                    encoding="utf-8"
                )

                result = subprocess.run(
                    [
                        "javac",
                        "-XDrawDiagnostics",
                        "-proc:none",
                        "-d",
                        str(temp_dir),
                        str(filename)
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    check=False
                )

                output = (
                        (result.stdout or "")
                        + "\n"
                        + (result.stderr or "")
                )

                for line in output.splitlines():

                    match = re.search(
                        r"\.java:(\d+)(?::(\d+))?:\s*(.+)",
                        line
                    )

                    if not match:
                        continue

                    row = max(0, int(match.group(1)) - 1)

                    if match.group(2):
                        column = max(0, int(match.group(2)) - 1)
                    else:
                        column = 0

                    message = match.group(3)

                    diagnostic = (
                        row,
                        column,
                        row,
                        column + 1,
                        f"javac: {message}"
                    )

                    if ".warn." in message or message.startswith("compiler.warn"):
                        warnings.append(diagnostic)
                    else:
                        errors.append(diagnostic)

        except subprocess.TimeoutExpired:
            warnings.append((
                0, 0, 0, 0,
                "Java-Compiler hat zu lange gebraucht."
            ))

        except FileNotFoundError:
            warnings.append((
                0, 0, 0, 0,
                "javac wurde nicht gefunden. Ist das JDK installiert?"
            ))

        except OSError as exc:
            warnings.append((
                0, 0, 0, 0,
                f"Java-Compiler konnte nicht gestartet werden: {exc}"
            ))

        return errors, warnings

    def _analyze_checkstyle(self, code):
        errors = []
        warnings = []
        filename = None

        if not self.checkstyle_jar or not self.checkstyle_jar.is_file():
            warnings.append((
                0, 0, 0, 0,
                "Checkstyle-JAR fehlt."
            ))
            return errors, warnings

        if not self.config_file or not self.config_file.is_file():
            warnings.append((
                0, 0, 0, 0,
                "Checkstyle-Konfiguration fehlt."
            ))
            return errors, warnings

        try:
            with tempfile.NamedTemporaryFile(
                    suffix=".java",
                    delete=False,
                    mode="w",
                    encoding="utf-8",
                    newline="\n"
            ) as file:
                file.write(code)
                filename = file.name

            result = subprocess.run(
                [
                    "java",
                    "-jar",
                    str(self.checkstyle_jar),
                    "-c",
                    str(self.config_file),
                    filename
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                check=False
            )

            output = (
                    (result.stdout or "")
                    + "\n"
                    + (result.stderr or "")
            )

            source_lines = code.splitlines()

            for line in output.splitlines():
                text = line.strip()

                if not text.startswith("[ERROR]") and not text.startswith("[WARN]"):
                    continue

                match = re.search(
                    r"\[(ERROR|WARN)\]\s+.+?:(\d+)(?::(\d+))?:\s*(.+)",
                    text
                )

                if not match:
                    continue

                severity = match.group(1)
                row = max(0, int(match.group(2)) - 1)

                if match.group(3):
                    column = max(0, int(match.group(3)) - 1)
                else:
                    column = 0

                message = match.group(4)

                if "LineLength" in message and row < len(source_lines):
                    column = max(
                        0,
                        min(120, len(source_lines[row]) - 1)
                    )

                diagnostic = (
                    row,
                    column,
                    row,
                    column + 1,
                    f"Checkstyle: {message}"
                )

                if severity == "ERROR":
                    errors.append(diagnostic)
                else:
                    warnings.append(diagnostic)

            if result.returncode not in (0, 1) and not errors and not warnings:
                warnings.append((
                    0, 0, 0, 0,
                    "Checkstyle konnte die Java-Datei nicht analysieren."
                ))

        except subprocess.TimeoutExpired:
            warnings.append((
                0, 0, 0, 0,
                "Checkstyle-Analyse hat zu lange gedauert."
            ))

        except OSError as exc:
            warnings.append((
                0, 0, 0, 0,
                f"Checkstyle konnte nicht gestartet werden: {exc}"
            ))

        finally:
            if filename:
                try:
                    Path(filename).unlink(missing_ok=True)
                except OSError:
                    pass

        return errors, warnings

    def analyze_errors(self, code):
        errors, _ = self.analyze(code)
        return errors

    def analyze_warnings(self, code):
        _, warnings = self.analyze(code)
        return warnings