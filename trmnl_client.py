"""TRMNL webhook client for pushing plugin data."""

import requests


class TRMNLClient:
    def __init__(self, plugin_uuid: str):
        self.url = f"https://trmnl.com/api/custom_plugins/{plugin_uuid}"

    def push(self, merge_variables: dict) -> dict:
        resp = requests.post(
            self.url,
            json={"merge_variables": merge_variables},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()
