"""Integration platform for recorder."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, callback


@callback
def exclude_attributes(hass: HomeAssistant) -> set[str]:
    """Exclude frequently changing attributes being recorded in the database."""
    return {
        # iOS mobile app
        "Available",
        "Available (Important)",
        "Available (Opportunistic)",
        # Android mobile app
        "Free internal storage",
        "current",
        "voltage",
        "android.appInfo",
        "android.contains.customView",
        "android.infoText",
        "android.largeIcon",
        "android.progress",
        "android.progressIndeterminate",
        "android.progressMax",
        "android.reduced.images",
        "android.remoteInputHistory",
        "android.showChronometer",
        "android.showWhen",
        "android.subText",
        "android.summaryText",
        "android.template",
        "android.text",
        "android.textLines",
        "android.title",
        "android.title.big",
        "android.title.template",
        "android.wearable.EXTENSIONS",
        "android.when",
        "android.whenText",
        "category",
        "channel",
        "channel_id",
        "group_id",
        "is_clearable",
        "is_ongoing",
        "package",
        "post_time",
        "androidx.core.app.extra.COMPAT_TEMPLATE",
    }
