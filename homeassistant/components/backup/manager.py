"""Backup manager for the Backup integration."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from securetar import SecureTarFile, atomic_contents_add

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import json as json_util
from homeassistant.util.dt import now

from .const import EXCLUDE_FROM_BACKUP, LOGGER, VERSION


@dataclass
class Backup:
    """Backup class."""

    slug: str
    name: str
    date: str
    path: Path
    size: float

    def as_dict(self) -> dict:
        """Return a dict representation of this backup."""
        return {**asdict(self), "path": self.path.as_posix()}


class BackupManager:
    """Backup manager for the Backup integration."""

    _backups: dict[str, Backup] | None = None

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the backup manager."""
        self.hass = hass
        self.backup_dir = Path(hass.config.path("backups"))
        self.backing_up = False

    @property
    def backups(self) -> dict[str, Backup] | None:
        """Return a dict of backups."""
        return self._backups

    def load_backups(self) -> None:
        """Load data of stored backup files."""
        backups = {}

        def _read_backup_info(backup_path: Path) -> None:
            with SecureTarFile(backup_path, "r", gzip=False) as backup_file:
                if data_file := backup_file.extractfile("./backup.json"):
                    data = json.loads(data_file.read())
                    backup = Backup(
                        slug=data["slug"],
                        name=data["name"],
                        date=data["date"],
                        path=backup_path,
                        size=round(backup_path.stat().st_size / 1_048_576, 2),
                    )
                    backups[backup.slug] = backup

        for backup_path in self.backup_dir.glob("*.tar"):
            _read_backup_info(backup_path)

        LOGGER.debug("Loaded %s backups", len(backups))
        self._backups = backups

    def get_backup(self, slug: str) -> Backup | None:
        """Return a backup."""
        return None if self._backups is None else self._backups.get(slug)

    def remove_backup(self, slug: str) -> None:
        """Remove a backup."""
        LOGGER.error(self._backups)
        if self._backups is None or (backup := self.get_backup(slug)) is None:
            return
        backup.path.unlink(missing_ok=True)
        LOGGER.debug("Removed backup located at %s", backup.path)
        self._backups.pop(slug)

    async def generate_backup(self) -> Backup:
        """Generate a backup."""
        if self.backing_up:
            raise HomeAssistantError("Backup already in progress")

        if self._backups is None:
            self._backups = {}

        try:
            self.backing_up = True
            backup_name = f"Core {VERSION}"
            date_str = now().isoformat()
            slug = _generate_slug(date_str, backup_name)

            backup_data = {
                "slug": slug,
                "name": backup_name,
                "date": date_str,
                "type": "partial",
                "folders": ["homeassistant"],
                "homeassistant": {} if VERSION.dev else {"version": VERSION},
                "compressed": True,
            }
            tar_file_path = Path(self.backup_dir, f"{slug}.tar")

            if not self.backup_dir.exists():
                LOGGER.debug("Creating backup directory")
                self.hass.async_add_executor_job(self.backup_dir.mkdir)

            def _create_backup() -> None:
                with TemporaryDirectory() as tmp_dir:
                    tmp_dir_path = Path(tmp_dir)
                    json_util.save_json(
                        tmp_dir_path.joinpath("backup.json").as_posix(),
                        backup_data,
                    )
                    with SecureTarFile(
                        tmp_dir_path.joinpath("data.tar"), "w"
                    ) as tar_file:
                        atomic_contents_add(
                            tar_file=tar_file,
                            origin_path=Path(self.hass.config.path()),
                            excludes=EXCLUDE_FROM_BACKUP,
                            arcname="data",
                        )

                    with SecureTarFile(tar_file_path, "w") as tar_file:
                        atomic_contents_add(
                            tar_file=tar_file,
                            origin_path=tmp_dir_path,
                            excludes=EXCLUDE_FROM_BACKUP,
                            arcname="homeassistant",
                        )

            await self.hass.async_add_executor_job(_create_backup)
            backup = Backup(
                slug=slug,
                name=backup_name,
                date=date_str,
                path=tar_file_path,
                size=round(tar_file_path.stat().st_size / 1_048_576, 2),
            )
            self._backups[slug] = backup
            LOGGER.debug("Generated new backup with slug %s", slug)
            return backup
        finally:
            self.backing_up = False


def _generate_slug(date: str, name: str) -> str:
    """Generate a backup slug."""
    return hashlib.sha1(f"{date} - {name}".lower().encode()).hexdigest()[:8]
