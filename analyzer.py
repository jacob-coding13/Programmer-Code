import json
import subprocess
import sys
import tempfile
from pathlib import Path

class PythonAnalyzer:

    def analyze(self, code):
        errors = []
        warnings = []
        filename = None

        try:
            with tempfile.NamedTemporaryFile(
                    suffix=".py",
                    delete=False,
                    mode="w",
                    encoding="utf-8",
            ) as file:
                file.write(code)
                filename = file.name

            ruff_command = self.get_ruff_command()

            if not ruff_command:
                return errors, warnings

            result = subprocess.run(
                ruff_command + [
                    "check",
                    filename,
                    "--output-format=json",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if not result.stdout.strip():
                return errors, warnings

            try:
                diagnostics = json.loads(result.stdout)
            except json.JSONDecodeError:
                return errors, warnings

            for item in diagnostics:
                rule_code = item.get("code", "")

                if rule_code == "F401":
                    continue
                location = item.get("location", {})
                end_location = item.get("end_location", {})

                row = location.get("row", 1)
                column = location.get("column", 1)

                end_row = end_location.get("row", row)
                end_column = end_location.get("column", column)

                line = max(0, row - 1)
                column = max(0, column - 1)

                end_line = max(0, end_row - 1)
                end_column = max(0, end_column - 1)

                message = item.get(
                    "message",
                    "Unbekannter Ruff-Fehler"
                )

                rule_code = item.get("code", "")

                diagnostic = (
                    line,
                    column,
                    end_line,
                    end_column,
                    f"{rule_code}: {message}",
                )

                if self._is_error(rule_code):
                    errors.append(diagnostic)
                else:
                    warnings.append(diagnostic)

        except Exception:
            pass

        finally:
            if filename:
                Path(filename).unlink(missing_ok=True)

        return errors, warnings

    def _is_error(self, rule_code):
        return (
                rule_code == "invalid-syntax"
                or rule_code == "F821"
                or rule_code.startswith("E9")
        )

    def analyze_errors(self, code):
        errors, _ = self.analyze(code)
        return errors

    def analyze_warnings(self, code):
        _, warnings = self.analyze(code)
        return warnings

    def get_ruff_command(self):
        if getattr(sys, "frozen", False):
            base_path = Path(sys.executable).parent
            ruff = base_path / "ruff.exe"

            if ruff.exists():
                return [str(ruff)]

            meipass = getattr(sys, "_MEIPASS", None)

            if meipass:
                ruff = Path(meipass) / "ruff.exe"

                if ruff.exists():
                    return [str(ruff)]

            return None

        return [
            sys.executable,
            "-m",
            "ruff",
        ]