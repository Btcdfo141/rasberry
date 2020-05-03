"""Constants for Synology DSM."""
from homeassistant.const import (
    DATA_MEGABYTES,
    DATA_RATE_KILOBYTES_PER_SECOND,
<<<<<<< HEAD
    PERCENTAGE,
=======
    DATA_TERABYTES,
    PERCENTAGE,
>>>>>>> 6f6c670b3b0efdd2e98a3a3ce39b234b1dd4b1d4
)

DOMAIN = "synology_dsm"
BASE_NAME = "Synology"

CONF_VOLUMES = "volumes"
DEFAULT_SSL = True
DEFAULT_PORT = 5000
DEFAULT_PORT_SSL = 5001

UTILISATION_SENSORS = {
    "cpu_other_load": ["CPU Load (Other)", PERCENTAGE, "mdi:chip"],
    "cpu_user_load": ["CPU Load (User)", PERCENTAGE, "mdi:chip"],
    "cpu_system_load": ["CPU Load (System)", PERCENTAGE, "mdi:chip"],
    "cpu_total_load": ["CPU Load (Total)", PERCENTAGE, "mdi:chip"],
    "cpu_1min_load": ["CPU Load (1 min)", PERCENTAGE, "mdi:chip"],
    "cpu_5min_load": ["CPU Load (5 min)", PERCENTAGE, "mdi:chip"],
    "cpu_15min_load": ["CPU Load (15 min)", PERCENTAGE, "mdi:chip"],
    "memory_real_usage": ["Memory Usage (Real)", PERCENTAGE, "mdi:memory"],
    "memory_size": ["Memory Size", DATA_MEGABYTES, "mdi:memory"],
    "memory_cached": ["Memory Cached", DATA_MEGABYTES, "mdi:memory"],
    "memory_available_swap": ["Memory Available (Swap)", DATA_MEGABYTES, "mdi:memory"],
    "memory_available_real": ["Memory Available (Real)", DATA_MEGABYTES, "mdi:memory"],
    "memory_total_swap": ["Memory Total (Swap)", DATA_MEGABYTES, "mdi:memory"],
    "memory_total_real": ["Memory Total (Real)", DATA_MEGABYTES, "mdi:memory"],
    "network_up": ["Network Up", DATA_RATE_KILOBYTES_PER_SECOND, "mdi:upload"],
    "network_down": ["Network Down", DATA_RATE_KILOBYTES_PER_SECOND, "mdi:download"],
}
STORAGE_VOL_SENSORS = {
    "volume_status": ["Status", None, "mdi:checkbox-marked-circle-outline"],
    "volume_device_type": ["Type", None, "mdi:harddisk"],
<<<<<<< HEAD
    "volume_size_total": ["Total Size", None, "mdi:chart-pie"],
    "volume_size_used": ["Used Space", None, "mdi:chart-pie"],
    "volume_percentage_used": ["Volume Used", PERCENTAGE, "mdi:chart-pie"],
=======
    "volume_size_total": ["Total Size", DATA_TERABYTES, "mdi:chart-pie"],
    "volume_size_used": ["Used Space", DATA_TERABYTES, "mdi:chart-pie"],
    "volume_percentage_used": ["Volume Used", PERCENTAGE, "mdi:chart-pie"],
>>>>>>> 6f6c670b3b0efdd2e98a3a3ce39b234b1dd4b1d4
    "volume_disk_temp_avg": ["Average Disk Temp", None, "mdi:thermometer"],
    "volume_disk_temp_max": ["Maximum Disk Temp", None, "mdi:thermometer"],
}
STORAGE_DISK_SENSORS = {
    "disk_name": ["Name", None, "mdi:harddisk"],
    "disk_device": ["Device", None, "mdi:dots-horizontal"],
    "disk_smart_status": ["Status (Smart)", None, "mdi:checkbox-marked-circle-outline"],
    "disk_status": ["Status", None, "mdi:checkbox-marked-circle-outline"],
    "disk_exceed_bad_sector_thr": ["Exceeded Max Bad Sectors", None, "mdi:test-tube"],
    "disk_below_remain_life_thr": ["Below Min Remaining Life", None, "mdi:test-tube"],
    "disk_temp": ["Temperature", None, "mdi:thermometer"],
}


TEMP_SENSORS_KEYS = ["volume_disk_temp_avg", "volume_disk_temp_max", "disk_temp"]
