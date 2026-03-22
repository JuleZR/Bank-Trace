"""Persistence helpers for the local application configuration."""

from __future__ import annotations

import json
from typing import Any

from bank_trace.config.settings import CONFIG_FILE


class StorageService:
    """Load and save the user configuration file."""

    def load_config(self) -> dict[str, Any]:
        """Load persisted UI configuration with safe defaults.

        :returns: Configuration dictionary merged with default keys.
        """

        if not CONFIG_FILE.exists():
            return self._default_config()

        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError):
            return self._default_config()

        default = self._default_config()
        default.update(data)
        return default

    def save_config(
        self,
        folder: str,
        contract_numbers: list[str],
        output_file: str,
    ) -> None:
        """Persist the current UI configuration to disk.

        :param folder: Selected PDF folder path.
        :param contract_numbers: Contract numbers entered by the user.
        :param output_file: Output report path.
        """

        payload = {
            "folder": folder,
            "contract_numbers": contract_numbers,
            "output_file": output_file,
        }

        with CONFIG_FILE.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    @staticmethod
    def _default_config() -> dict[str, Any]:
        """Return the default configuration structure.

        :returns: Empty configuration values for first startup or recovery.
        """

        return {
            "folder": "",
            "contract_numbers": [],
            "output_file": "",
        }
