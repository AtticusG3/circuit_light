from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_BULB_ENTITIES, CONF_POWER_ENTITY, DATA_KEY, PLATFORMS
from .coordinator import CircuitLightCoordinator


@dataclass(slots=True)
class CircuitLightEntryData:
    coordinator: CircuitLightCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Circuit Light from a config entry."""
    coordinator = CircuitLightCoordinator(hass, entry_id=entry.entry_id, entry_data=entry.data)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DATA_KEY, {})[entry.entry_id] = CircuitLightEntryData(
        coordinator=coordinator
    )

    # Forward setup to the light platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Hide the power and bulb entities from the UI
    entity_reg = er.async_get(hass)
    power_entity_id = entry.data[CONF_POWER_ENTITY]
    bulb_entity_ids = entry.data[CONF_BULB_ENTITIES]

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
        entry_data: CircuitLightEntryData | None = hass.data.get(DATA_KEY, {}).pop(
            entry.entry_id, None
        )
        if entry_data is not None:
            await entry_data.coordinator.async_shutdown()

        # Show the power and bulb entities again
        entity_reg = er.async_get(hass)
        power_entity_id = entry.data[CONF_POWER_ENTITY]
        bulb_entity_ids = entry.data[CONF_BULB_ENTITIES]

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