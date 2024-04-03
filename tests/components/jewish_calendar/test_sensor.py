"""The tests for the Jewish calendar sensors."""

from datetime import datetime as dt, timedelta

import pytest

from homeassistant.components import jewish_calendar
from homeassistant.components.binary_sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import homeassistant.util.dt as dt_util

from . import alter_time, make_jerusalem_test_params, make_nyc_test_params

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_jewish_calendar_min_config(hass: HomeAssistant) -> None:
    """Test minimum jewish calendar configuration."""
    entry = MockConfigEntry(domain=jewish_calendar.DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.jewish_calendar_date") is not None


async def test_jewish_calendar_hebrew(hass: HomeAssistant) -> None:
    """Test jewish calendar sensor with language set to hebrew."""
    entry = MockConfigEntry(domain=jewish_calendar.DOMAIN, data={"language": "hebrew"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.jewish_calendar_date") is not None


TEST_PARAMS = [
    (dt(2018, 9, 3), "UTC", 31.778, 35.235, "english", "date", False, "23 Elul 5778"),
    (
        dt(2018, 9, 3),
        "UTC",
        31.778,
        35.235,
        "hebrew",
        "date",
        False,
        'כ"ג אלול ה\' תשע"ח',
    ),
    (dt(2018, 9, 10), "UTC", 31.778, 35.235, "hebrew", "holiday", False, "א' ראש השנה"),
    (
        dt(2018, 9, 10),
        "UTC",
        31.778,
        35.235,
        "english",
        "holiday",
        False,
        "Rosh Hashana I",
    ),
    (
        dt(2018, 9, 8),
        "UTC",
        31.778,
        35.235,
        "hebrew",
        "weekly_portion",
        False,
        "נצבים",
    ),
    (
        dt(2018, 9, 8),
        "America/New_York",
        40.7128,
        -74.0060,
        "hebrew",
        "first_stars",
        True,
        dt(2018, 9, 8, 19, 45),
    ),
    (
        dt(2018, 9, 8),
        "Asia/Jerusalem",
        31.778,
        35.235,
        "hebrew",
        "first_stars",
        False,
        dt(2018, 9, 8, 19, 19),
    ),
    (
        dt(2018, 10, 14),
        "Asia/Jerusalem",
        31.778,
        35.235,
        "hebrew",
        "weekly_portion",
        False,
        "לך לך",
    ),
    (
        dt(2018, 10, 14, 17, 0, 0),
        "Asia/Jerusalem",
        31.778,
        35.235,
        "hebrew",
        "date",
        False,
        "ה' מרחשוון ה' תשע\"ט",
    ),
    (
        dt(2018, 10, 14, 19, 0, 0),
        "Asia/Jerusalem",
        31.778,
        35.235,
        "hebrew",
        "date",
        False,
        "ו' מרחשוון ה' תשע\"ט",
    ),
]

TEST_IDS = [
    "date_output",
    "date_output_hebrew",
    "holiday",
    "holiday_english",
    "torah_reading",
    "first_stars_ny",
    "first_stars_jerusalem",
    "torah_reading_weekday",
    "date_before_sunset",
    "date_after_sunset",
]


@pytest.mark.parametrize(
    (
        "now",
        "tzname",
        "latitude",
        "longitude",
        "language",
        "sensor",
        "diaspora",
        "result",
    ),
    TEST_PARAMS,
    ids=TEST_IDS,
)
async def test_jewish_calendar_sensor(
    hass: HomeAssistant,
    now,
    tzname,
    latitude,
    longitude,
    language,
    sensor,
    diaspora,
    result,
) -> None:
    """Test Jewish calendar sensor output."""
    time_zone = dt_util.get_time_zone(tzname)
    test_time = now.replace(tzinfo=time_zone)

    hass.config.set_time_zone(tzname)
    hass.config.latitude = latitude
    hass.config.longitude = longitude

    with alter_time(test_time):
        entry = MockConfigEntry(
            domain=jewish_calendar.DOMAIN,
            data={
                "name": "test",
                "language": language,
                "diaspora": diaspora,
            },
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        future = dt_util.utcnow() + timedelta(seconds=30)
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()

    result = (
        dt_util.as_utc(result.replace(tzinfo=time_zone)).isoformat()
        if isinstance(result, dt)
        else result
    )

    sensor_object = hass.states.get(f"sensor.jewish_calendar_{sensor}")
    assert sensor_object.state == result

    if sensor == "holiday":
        assert sensor_object.attributes.get("id") == "rosh_hashana_i"
        assert sensor_object.attributes.get("type") == "YOM_TOV"
        assert sensor_object.attributes.get("type_id") == 1


SHABBAT_PARAMS = [
    make_nyc_test_params(
        dt(2018, 9, 1, 16, 0),
        {
            "english_upcoming_candle_lighting": dt(2018, 8, 31, 19, 12),
            "english_upcoming_havdalah": dt(2018, 9, 1, 20, 10),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 8, 31, 19, 12),
            "english_upcoming_shabbat_havdalah": dt(2018, 9, 1, 20, 10),
            "english_weekly_portion": "Ki Tavo",
            "hebrew_weekly_portion": "כי תבוא",
        },
    ),
    make_nyc_test_params(
        dt(2018, 9, 1, 16, 0),
        {
            "english_upcoming_candle_lighting": dt(2018, 8, 31, 19, 12),
            "english_upcoming_havdalah": dt(2018, 9, 1, 20, 18),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 8, 31, 19, 12),
            "english_upcoming_shabbat_havdalah": dt(2018, 9, 1, 20, 18),
            "english_weekly_portion": "Ki Tavo",
            "hebrew_weekly_portion": "כי תבוא",
        },
        havdalah_offset=50,
    ),
    make_nyc_test_params(
        dt(2018, 9, 1, 20, 0),
        {
            "english_upcoming_shabbat_candle_lighting": dt(2018, 8, 31, 19, 12),
            "english_upcoming_shabbat_havdalah": dt(2018, 9, 1, 20, 10),
            "english_upcoming_candle_lighting": dt(2018, 8, 31, 19, 12),
            "english_upcoming_havdalah": dt(2018, 9, 1, 20, 10),
            "english_weekly_portion": "Ki Tavo",
            "hebrew_weekly_portion": "כי תבוא",
        },
    ),
    make_nyc_test_params(
        dt(2018, 9, 1, 20, 21),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 7, 19),
            "english_upcoming_havdalah": dt(2018, 9, 8, 19, 58),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 9, 7, 19),
            "english_upcoming_shabbat_havdalah": dt(2018, 9, 8, 19, 58),
            "english_weekly_portion": "Nitzavim",
            "hebrew_weekly_portion": "נצבים",
        },
    ),
    make_nyc_test_params(
        dt(2018, 9, 7, 13, 1),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 7, 19),
            "english_upcoming_havdalah": dt(2018, 9, 8, 19, 58),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 9, 7, 19),
            "english_upcoming_shabbat_havdalah": dt(2018, 9, 8, 19, 58),
            "english_weekly_portion": "Nitzavim",
            "hebrew_weekly_portion": "נצבים",
        },
    ),
    make_nyc_test_params(
        dt(2018, 9, 8, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 9, 18, 57),
            "english_upcoming_havdalah": dt(2018, 9, 11, 19, 53),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 9, 14, 18, 48),
            "english_upcoming_shabbat_havdalah": dt(2018, 9, 15, 19, 46),
            "english_weekly_portion": "Vayeilech",
            "hebrew_weekly_portion": "וילך",
            "english_holiday": "Erev Rosh Hashana",
            "hebrew_holiday": "ערב ראש השנה",
        },
    ),
    make_nyc_test_params(
        dt(2018, 9, 9, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 9, 18, 57),
            "english_upcoming_havdalah": dt(2018, 9, 11, 19, 53),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 9, 14, 18, 48),
            "english_upcoming_shabbat_havdalah": dt(2018, 9, 15, 19, 46),
            "english_weekly_portion": "Vayeilech",
            "hebrew_weekly_portion": "וילך",
            "english_holiday": "Rosh Hashana I",
            "hebrew_holiday": "א' ראש השנה",
        },
    ),
    make_nyc_test_params(
        dt(2018, 9, 10, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 9, 18, 57),
            "english_upcoming_havdalah": dt(2018, 9, 11, 19, 53),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 9, 14, 18, 48),
            "english_upcoming_shabbat_havdalah": dt(2018, 9, 15, 19, 46),
            "english_weekly_portion": "Vayeilech",
            "hebrew_weekly_portion": "וילך",
            "english_holiday": "Rosh Hashana II",
            "hebrew_holiday": "ב' ראש השנה",
        },
    ),
    make_nyc_test_params(
        dt(2018, 9, 28, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 28, 18, 25),
            "english_upcoming_havdalah": dt(2018, 9, 29, 19, 22),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 9, 28, 18, 25),
            "english_upcoming_shabbat_havdalah": dt(2018, 9, 29, 19, 22),
            "english_weekly_portion": "none",
            "hebrew_weekly_portion": "none",
        },
    ),
    make_nyc_test_params(
        dt(2018, 9, 29, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 30, 18, 22),
            "english_upcoming_havdalah": dt(2018, 10, 2, 19, 17),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 10, 5, 18, 13),
            "english_upcoming_shabbat_havdalah": dt(2018, 10, 6, 19, 11),
            "english_weekly_portion": "Bereshit",
            "hebrew_weekly_portion": "בראשית",
            "english_holiday": "Hoshana Raba",
            "hebrew_holiday": "הושענא רבה",
        },
    ),
    make_nyc_test_params(
        dt(2018, 9, 30, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 30, 18, 22),
            "english_upcoming_havdalah": dt(2018, 10, 2, 19, 17),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 10, 5, 18, 13),
            "english_upcoming_shabbat_havdalah": dt(2018, 10, 6, 19, 11),
            "english_weekly_portion": "Bereshit",
            "hebrew_weekly_portion": "בראשית",
            "english_holiday": "Shmini Atzeret",
            "hebrew_holiday": "שמיני עצרת",
        },
    ),
    make_nyc_test_params(
        dt(2018, 10, 1, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 30, 18, 22),
            "english_upcoming_havdalah": dt(2018, 10, 2, 19, 17),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 10, 5, 18, 13),
            "english_upcoming_shabbat_havdalah": dt(2018, 10, 6, 19, 11),
            "english_weekly_portion": "Bereshit",
            "hebrew_weekly_portion": "בראשית",
            "english_holiday": "Simchat Torah",
            "hebrew_holiday": "שמחת תורה",
        },
    ),
    make_jerusalem_test_params(
        dt(2018, 9, 29, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 30, 18, 7),
            "english_upcoming_havdalah": dt(2018, 10, 1, 19, 1),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 10, 5, 18, 1),
            "english_upcoming_shabbat_havdalah": dt(2018, 10, 6, 18, 54),
            "english_weekly_portion": "Bereshit",
            "hebrew_weekly_portion": "בראשית",
            "english_holiday": "Hoshana Raba",
            "hebrew_holiday": "הושענא רבה",
        },
    ),
    make_jerusalem_test_params(
        dt(2018, 9, 30, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 9, 30, 18, 7),
            "english_upcoming_havdalah": dt(2018, 10, 1, 19, 1),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 10, 5, 18, 1),
            "english_upcoming_shabbat_havdalah": dt(2018, 10, 6, 18, 54),
            "english_weekly_portion": "Bereshit",
            "hebrew_weekly_portion": "בראשית",
            "english_holiday": "Shmini Atzeret",
            "hebrew_holiday": "שמיני עצרת",
        },
    ),
    make_jerusalem_test_params(
        dt(2018, 10, 1, 21, 25),
        {
            "english_upcoming_candle_lighting": dt(2018, 10, 5, 18, 1),
            "english_upcoming_havdalah": dt(2018, 10, 6, 18, 54),
            "english_upcoming_shabbat_candle_lighting": dt(2018, 10, 5, 18, 1),
            "english_upcoming_shabbat_havdalah": dt(2018, 10, 6, 18, 54),
            "english_weekly_portion": "Bereshit",
            "hebrew_weekly_portion": "בראשית",
        },
    ),
    make_nyc_test_params(
        dt(2016, 6, 11, 8, 25),
        {
            "english_upcoming_candle_lighting": dt(2016, 6, 10, 20, 9),
            "english_upcoming_havdalah": dt(2016, 6, 13, 21, 19),
            "english_upcoming_shabbat_candle_lighting": dt(2016, 6, 10, 20, 9),
            "english_upcoming_shabbat_havdalah": "unknown",
            "english_weekly_portion": "Bamidbar",
            "hebrew_weekly_portion": "במדבר",
            "english_holiday": "Erev Shavuot",
            "hebrew_holiday": "ערב שבועות",
        },
    ),
    make_nyc_test_params(
        dt(2016, 6, 12, 8, 25),
        {
            "english_upcoming_candle_lighting": dt(2016, 6, 10, 20, 9),
            "english_upcoming_havdalah": dt(2016, 6, 13, 21, 19),
            "english_upcoming_shabbat_candle_lighting": dt(2016, 6, 17, 20, 12),
            "english_upcoming_shabbat_havdalah": dt(2016, 6, 18, 21, 21),
            "english_weekly_portion": "Nasso",
            "hebrew_weekly_portion": "נשא",
            "english_holiday": "Shavuot",
            "hebrew_holiday": "שבועות",
        },
    ),
    make_jerusalem_test_params(
        dt(2017, 9, 21, 8, 25),
        {
            "english_upcoming_candle_lighting": dt(2017, 9, 20, 18, 20),
            "english_upcoming_havdalah": dt(2017, 9, 23, 19, 11),
            "english_upcoming_shabbat_candle_lighting": dt(2017, 9, 22, 19, 12),
            "english_upcoming_shabbat_havdalah": dt(2017, 9, 23, 19, 11),
            "english_weekly_portion": "Ha'Azinu",
            "hebrew_weekly_portion": "האזינו",
            "english_holiday": "Rosh Hashana I",
            "hebrew_holiday": "א' ראש השנה",
        },
    ),
    make_jerusalem_test_params(
        dt(2017, 9, 22, 8, 25),
        {
            "english_upcoming_candle_lighting": dt(2017, 9, 20, 18, 20),
            "english_upcoming_havdalah": dt(2017, 9, 23, 19, 11),
            "english_upcoming_shabbat_candle_lighting": dt(2017, 9, 22, 19, 12),
            "english_upcoming_shabbat_havdalah": dt(2017, 9, 23, 19, 11),
            "english_weekly_portion": "Ha'Azinu",
            "hebrew_weekly_portion": "האזינו",
            "english_holiday": "Rosh Hashana II",
            "hebrew_holiday": "ב' ראש השנה",
        },
    ),
    make_jerusalem_test_params(
        dt(2017, 9, 23, 8, 25),
        {
            "english_upcoming_candle_lighting": dt(2017, 9, 20, 18, 20),
            "english_upcoming_havdalah": dt(2017, 9, 23, 19, 11),
            "english_upcoming_shabbat_candle_lighting": dt(2017, 9, 22, 19, 12),
            "english_upcoming_shabbat_havdalah": dt(2017, 9, 23, 19, 11),
            "english_weekly_portion": "Ha'Azinu",
            "hebrew_weekly_portion": "האזינו",
            "english_holiday": "",
            "hebrew_holiday": "",
        },
    ),
]

SHABBAT_TEST_IDS = [
    "currently_first_shabbat",
    "currently_first_shabbat_with_havdalah_offset",
    "currently_first_shabbat_bein_hashmashot_lagging_date",
    "after_first_shabbat",
    "friday_upcoming_shabbat",
    "upcoming_rosh_hashana",
    "currently_rosh_hashana",
    "second_day_rosh_hashana",
    "currently_shabbat_chol_hamoed",
    "upcoming_two_day_yomtov_in_diaspora",
    "currently_first_day_of_two_day_yomtov_in_diaspora",
    "currently_second_day_of_two_day_yomtov_in_diaspora",
    "upcoming_one_day_yom_tov_in_israel",
    "currently_one_day_yom_tov_in_israel",
    "after_one_day_yom_tov_in_israel",
    # Type 1 = Sat/Sun/Mon
    "currently_first_day_of_three_day_type1_yomtov_in_diaspora",
    "currently_second_day_of_three_day_type1_yomtov_in_diaspora",
    # Type 2 = Thurs/Fri/Sat
    "currently_first_day_of_three_day_type2_yomtov_in_israel",
    "currently_second_day_of_three_day_type2_yomtov_in_israel",
    "currently_third_day_of_three_day_type2_yomtov_in_israel",
]


@pytest.mark.parametrize("language", ["english", "hebrew"])
@pytest.mark.parametrize(
    (
        "now",
        "candle_lighting",
        "havdalah",
        "diaspora",
        "tzname",
        "latitude",
        "longitude",
        "result",
    ),
    SHABBAT_PARAMS,
    ids=SHABBAT_TEST_IDS,
)
async def test_shabbat_times_sensor(
    hass: HomeAssistant,
    language,
    now,
    candle_lighting,
    havdalah,
    diaspora,
    tzname,
    latitude,
    longitude,
    result,
) -> None:
    """Test sensor output for upcoming shabbat/yomtov times."""
    time_zone = dt_util.get_time_zone(tzname)
    test_time = now.replace(tzinfo=time_zone)

    hass.config.set_time_zone(tzname)
    hass.config.latitude = latitude
    hass.config.longitude = longitude

    with alter_time(test_time):
        entry = MockConfigEntry(
            domain=jewish_calendar.DOMAIN,
            data={
                "name": "test",
                "language": language,
                "diaspora": diaspora,
                "candle_lighting_minutes_before_sunset": candle_lighting,
                "havdalah_minutes_after_sunset": havdalah,
            },
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        future = dt_util.utcnow() + timedelta(seconds=30)
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()

    for sensor_type, result_value in result.items():
        if not sensor_type.startswith(language):
            continue

        sensor_type = sensor_type.replace(f"{language}_", "")

        result_value = (
            dt_util.as_utc(result_value).isoformat()
            if isinstance(result_value, dt)
            else result_value
        )

        assert hass.states.get(f"sensor.jewish_calendar_{sensor_type}").state == str(
            result_value
        ), f"Value for {sensor_type}"


OMER_PARAMS = [
    (dt(2019, 4, 21, 0), "1"),
    (dt(2019, 4, 21, 23), "2"),
    (dt(2019, 5, 23, 0), "33"),
    (dt(2019, 6, 8, 0), "49"),
    (dt(2019, 6, 9, 0), "0"),
    (dt(2019, 1, 1, 0), "0"),
]
OMER_TEST_IDS = [
    "first_day_of_omer",
    "first_day_of_omer_after_tzeit",
    "lag_baomer",
    "last_day_of_omer",
    "shavuot_no_omer",
    "jan_1st_no_omer",
]


@pytest.mark.parametrize(("test_time", "result"), OMER_PARAMS, ids=OMER_TEST_IDS)
async def test_omer_sensor(hass: HomeAssistant, test_time, result) -> None:
    """Test Omer Count sensor output."""
    test_time = test_time.replace(tzinfo=dt_util.get_time_zone(hass.config.time_zone))

    with alter_time(test_time):
        entry = MockConfigEntry(domain=jewish_calendar.DOMAIN, data={"name": "test"})
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        future = dt_util.utcnow() + timedelta(seconds=30)
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()

    assert hass.states.get("sensor.jewish_calendar_omer_count").state == result


DAFYOMI_PARAMS = [
    (dt(2014, 4, 28, 0), "Beitzah 29"),
    (dt(2020, 1, 4, 0), "Niddah 73"),
    (dt(2020, 1, 5, 0), "Berachos 2"),
    (dt(2020, 3, 7, 0), "Berachos 64"),
    (dt(2020, 3, 8, 0), "Shabbos 2"),
]
DAFYOMI_TEST_IDS = [
    "randomly_picked_date",
    "end_of_cycle13",
    "start_of_cycle14",
    "cycle14_end_of_berachos",
    "cycle14_start_of_shabbos",
]


@pytest.mark.parametrize(("test_time", "result"), DAFYOMI_PARAMS, ids=DAFYOMI_TEST_IDS)
async def test_dafyomi_sensor(hass: HomeAssistant, test_time, result) -> None:
    """Test Daf Yomi sensor output."""
    test_time = test_time.replace(tzinfo=dt_util.get_time_zone(hass.config.time_zone))

    with alter_time(test_time):
        entry = MockConfigEntry(domain=jewish_calendar.DOMAIN, data={"name": "test"})
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        future = dt_util.utcnow() + timedelta(seconds=30)
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()

    assert hass.states.get("sensor.jewish_calendar_daf_yomi").state == result


async def test_no_discovery_info(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test setup without discovery info."""
    assert SENSOR_DOMAIN not in hass.config.components
    assert await async_setup_component(
        hass,
        SENSOR_DOMAIN,
        {SENSOR_DOMAIN: {"platform": jewish_calendar.DOMAIN}},
    )
    await hass.async_block_till_done()
    assert SENSOR_DOMAIN in hass.config.components
