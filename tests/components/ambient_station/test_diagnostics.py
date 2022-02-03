"""Test Ambient PWS diagnostics."""
from homeassistant.components.ambient_station import DOMAIN
from homeassistant.components.diagnostics import REDACTED

from tests.components.diagnostics import get_diagnostics_for_config_entry


async def test_entry_diagnostics(
    hass, config_entry, hass_client, setup_ambient_station, station_data
):
    """Test config entry diagnostics."""
    ambient = hass.data[DOMAIN][config_entry.entry_id]
    ambient.stations = station_data
    assert await get_diagnostics_for_config_entry(hass, hass_client, config_entry) == {
        "entry": {
            "data": {"api_key": REDACTED, "app_key": REDACTED},
            "title": "Mock Title",
        },
        "stations": {
            "devices": [
                {
                    "apiKey": REDACTED,
                    "info": {"location": REDACTED, "name": "Side Yard"},
                    "lastData": {
                        "baromabsin": 25.016,
                        "baromrelin": 29.953,
                        "batt_co2": 1,
                        "dailyrainin": 0,
                        "date": "2022-01-19T22:38:00.000Z",
                        "dateutc": 1642631880000,
                        "deviceId": REDACTED,
                        "dewPoint": 17.75,
                        "dewPointin": 37,
                        "eventrainin": 0,
                        "feelsLike": 21,
                        "feelsLikein": 69.1,
                        "hourlyrainin": 0,
                        "humidity": 87,
                        "humidityin": 29,
                        "lastRain": "2022-01-07T19:45:00.000Z",
                        "maxdailygust": 9.2,
                        "monthlyrainin": 0.409,
                        "solarradiation": 11.62,
                        "tempf": 21,
                        "tempinf": 70.9,
                        "totalrainin": 35.398,
                        "tz": REDACTED,
                        "uv": 0,
                        "weeklyrainin": 0,
                        "winddir": 25,
                        "windgustmph": 1.1,
                        "windspeedmph": 0.2,
                    },
                    "macAddress": REDACTED,
                }
            ],
            "method": "subscribe",
        },
    }
