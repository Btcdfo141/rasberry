"""Platform for sensor integration."""
from __future__ import annotations

from trello import TrelloClient

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_API_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BOARD_IDS, DOMAIN, Board, List
from .coordinator import TrelloDataUpdateCoordinator


class TrelloSensor(CoordinatorEntity[TrelloDataUpdateCoordinator], SensorEntity):
    """Representation of a TrelloSensor."""

    _attr_native_unit_of_measurement = "Cards"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self,
        board: Board,
        list_: List,
        coordinator: TrelloDataUpdateCoordinator,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.board = board
        self.list_id = list_.id
        self._attr_unique_id = f"list_{list_.id}".lower()
        self._attr_name = list_.name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, board.id)},
            name=board.name,
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Trello",
            model="Board",
        )

    @property
    def available(self) -> bool:
        """Determine if sensor is available."""
        board = self.coordinator.data[self.board.id]
        list_id = board.lists.get(self.list_id)
        return bool(board.lists and list_id)

    @property
    def native_value(self) -> int | None:
        """Return the card count of the sensor's list."""
        return self.coordinator.data[self.board.id].lists[self.list_id].card_count

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.available:
            board = self.coordinator.data[self.board.id]
            self._attr_name = board.lists[self.list_id].name
            self.async_write_ha_state()
        super()._handle_coordinator_update()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up trello sensors for config entries."""
    config_boards = config_entry.options[CONF_BOARD_IDS]
    config_data = config_entry.data
    trello_client = TrelloClient(
        api_key=config_data[CONF_API_KEY],
        api_secret=config_data[CONF_API_TOKEN],
    )
    coordinator = TrelloDataUpdateCoordinator(hass, trello_client, config_boards)
    await coordinator.async_config_entry_first_refresh()

    boards = coordinator.data.values()

    async_add_entities(
        [
            TrelloSensor(board, list_, coordinator)
            for board in boards
            for list_ in board.lists.values()
        ],
        True,
    )
