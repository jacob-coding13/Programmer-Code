import urllib.request
import json

from version import VERSION


GITHUB_API_URL = (
    "https://api.github.com/repos/"
    "jacob-coding13/Programmer-Code/releases/latest"
)


class UpdateChecker:

    def __init__(self):
        self.latest_version = None
        self.download_url = None

    def check(self):
        try:
            request = urllib.request.Request(
                GITHUB_API_URL,
                headers={
                    "User-Agent": "Programmer-Code"
                }
            )

            with urllib.request.urlopen(
                    request,
                    timeout=5
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

            tag = data.get("tag_name", "")

            if not tag:
                return False

            latest = tag.lstrip("v")

            self.latest_version = latest

            if self.is_newer(latest, VERSION):
                assets = data.get("assets", [])

                if assets:
                    self.download_url = assets[0].get(
                        "browser_download_url"
                    )

                return True

        except Exception:
            pass

        return False

    def is_newer(self, latest, current):
        try:
            latest_parts = tuple(
                int(part)
                for part in latest.split(".")
            )

            current_parts = tuple(
                int(part)
                for part in current.split(".")
            )

            return latest_parts > current_parts

        except (ValueError, TypeError):
            return False