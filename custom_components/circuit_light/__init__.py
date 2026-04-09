from __future__ import annotations

import asyncio
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PLATFORMS
from .light import CircuitLight


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Circuit Light from a config entry."""
    # Forward setup to the light platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Hide the power and bulb entities from the UI
    entity_reg = er.async_get(hass)
    power_entity_id = entry.data["power_entity"]
    bulb_entity_ids = entry.data["bulb_entities"]

    # Hide power entity
    if power_entity_id:
        power_entity = entity_reg.async_get(power_entity_id)
        if power_entity:
            entity_reg.async_update_entity(
                power_entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
            )

    # Hide bulb entities
    for bulb_id in bulb_entity_ids:
        bulb_entity = entity_reg.async_get(bulb_id)
        if bulb_entity:
            entity_reg.async_update_entity(
                bulb_id, hidden_by=er.RegistryEntryHider.INTEGRATION
            )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Show the power and bulb entities again
        entity_reg = er.async_get(hass)
        power_entity_id = entry.data["power_entity"]
        bulb_entity_ids = entry.data["bulb_entities"]

        # Show power entity
        if power_entity_id:
            power_entity = entity_reg.async_get(power_entity_id)
            if power_entity:
                entity_reg.async_update_entity(
                    power_entity_id, hidden_by=None
                )

        # Show bulb entities
        for bulb_id in bulb_entity_ids:
            bulb_entity = entity_reg.async_get(bulb_id)
            if bulb_entity:
                entity_reg.async_update_entity(
                    bulb_id, hidden_by=None
                )

    return unload_ok


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Circuit Light component."""
    return True