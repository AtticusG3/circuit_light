from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_BULB_ENTITIES,
    CONF_HIDE_CHILD_ENTITIES,
    CONF_POWER_ENTITY,
    DATA_KEY,
    PLATFORMS,
)
from .coordinator import CircuitLightCoordinator


@dataclass(slots=True)
class CircuitLightEntryData:
    coordinator: CircuitLightCoordinator


def _child_entity_ids(entry: ConfigEntry) -> list[str]:
    power_entity_id = entry.data.get(CONF_POWER_ENTITY)
    bulb_entity_ids = entry.data.get(CONF_BULB_ENTITIES, [])
    out: list[str] = []
    if isinstance(power_entity_id, str) and power_entity_id:
        out.append(power_entity_id)
    if isinstance(bulb_entity_ids, list):
        out.extend([e for e in bulb_entity_ids if isinstance(e, str) and e])
    return out


def _should_hide_children(entry: ConfigEntry) -> bool:
    # Default True to preserve the integration’s original behavior.
    return bool(entry.options.get(CONF_HIDE_CHILD_ENTITIES, True))


def _apply_child_hidden_state(hass: HomeAssistant, entry: ConfigEntry, *, hide: bool) -> None:
    entity_reg = er.async_get(hass)
    for ent_id in _child_entity_ids(entry):
        reg_entry = entity_reg.async_get(ent_id)
        if reg_entry is None:
            continue

        if hide:
            if reg_entry.hidden_by != er.RegistryEntryHider.INTEGRATION:
                entity_reg.async_update_entity(
                    ent_id, hidden_by=er.RegistryEntryHider.INTEGRATION
                )
        else:
            # Only unhide if we were the ones hiding it.
            if reg_entry.hidden_by == er.RegistryEntryHider.INTEGRATION:
                entity_reg.async_update_entity(ent_id, hidden_by=None)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Circuit Light from a config entry."""
    coordinator = CircuitLightCoordinator(hass, entry=entry, entry_data=entry.data)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DATA_KEY, {})[entry.entry_id] = CircuitLightEntryData(
        coordinator=coordinator
    )

    # Forward setup to the light platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if _should_hide_children(entry):
        _apply_child_hidden_state(hass, entry, hide=True)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


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

        if _should_hide_children(entry):
            _apply_child_hidden_state(hass, entry, hide=False)

    return unload_ok


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Circuit Light component."""
    return True