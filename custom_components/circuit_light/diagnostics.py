from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
try:
    # Available in full Home Assistant installs.
    from homeassistant.helpers.diagnostics import async_redact_data
except ImportError:  # pragma: no cover
    # Minimal test harnesses may not bundle diagnostics helpers; keep behavior safe.
    def async_redact_data(data: dict[str, Any], _to_redact: set[str]) -> dict[str, Any]:
        return data

from .const import CONF_BULB_ENTITIES, CONF_NAME, CONF_POWER_ENTITY, DATA_KEY


TO_REDACT: set[str] = set()


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entity_reg = er.async_get(hass)
    runtime = hass.data.get(DATA_KEY, {}).get(entry.entry_id)
    coordinator_data = getattr(getattr(runtime, "coordinator", None), "data", None)

    info: dict[str, Any] = {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": {
                CONF_NAME: entry.data.get(CONF_NAME),
                CONF_POWER_ENTITY: entry.data.get(CONF_POWER_ENTITY),
                CONF_BULB_ENTITIES: entry.data.get(CONF_BULB_ENTITIES, []),
            },
            "options": dict(entry.options),
        },
        "entity_registry": {
            "power_entity_exists": entity_reg.async_get(entry.data.get(CONF_POWER_ENTITY, "")) is not None,
            "bulb_entities_exist": {
                ent: entity_reg.async_get(ent) is not None for ent in entry.data.get(CONF_BULB_ENTITIES, [])
            },
        },
        "coordinator": {
            "last_update_success": getattr(getattr(runtime, "coordinator", None), "last_update_success", None),
            "data": coordinator_data,
        },
    }

    return async_redact_data(info, TO_REDACT)

