import json
import urllib.request

from version import VERSION


GITHUB_API_URL = (
    "https://api.github.com/repos/"
    "jacob-coding13/Programmer-Code/releases/latest"
)

UPDATE_ASSET_NAME = "Programmer-Code.zip"


class UpdateChecker:

    def __init__(self):
        self.latest_version = None
        self.download_url = None
        self.release_url = None

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
                    timeout=10
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

            tag = data.get("tag_name", "")

            if not tag:
                return False

            latest = tag.lstrip("v")

            self.latest_version = latest
            self.release_url = data.get("html_url")

            assets = data.get("assets", [])

            for asset in assets:
                if asset.get("name") == UPDATE_ASSET_NAME:
                    self.download_url = asset.get(
                        "browser_download_url"
                    )
                    break

            if not self.download_url:
                return False

            return self.is_newer(
                latest,
                VERSION
            )

        except Exception:
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