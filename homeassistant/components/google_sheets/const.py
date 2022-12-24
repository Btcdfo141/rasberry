"""Constants for Google Sheets integration."""
from __future__ import annotations

from typing import Final

from homeassistant.backports.enum import StrEnum

DOMAIN = "google_sheets"

CONF_SHEETS_ACCESS = "sheets_access"
DATA = "data"
DATA_CONFIG_ENTRY: Final = "config_entry"
DEFAULT_NAME = "Google Sheets"
DOCUMENT_ID = "document_id"
WORKSHEET = "worksheet"

SERVICE_APPEND_SHEET = "append_sheet"
SERVICE_EDIT_SHEET = "edit_sheet"


class FeatureAccess(StrEnum):
    """Class to represent different access scopes."""

    read_write = "https://www.googleapis.com/auth/spreadsheets"
    read_only = "https://www.googleapis.com/auth/spreadsheets.readonly"
    file = "https://www.googleapis.com/auth/drive.file"


DEFAULT_ACCESS = [FeatureAccess.file, FeatureAccess.read_only]
