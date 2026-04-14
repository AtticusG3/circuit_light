from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.circuit_light.const import (
    CONF_BULB_ENTITIES,
    CONF_POWER_ENTITY,
    DATA_KEY,
)
from custom_components.circuit_light.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_reports_entity_registry_and_coordinator(
    hass: HomeAssistant, setup_integration
) -> None:
    entry = setup_integration

    entity_reg = er.async_get(hass)
    # Entity registry avoids claiming an entity_id that already exists in the state machine.
    # Temporarily remove the states so we can create deterministic registry entries.
    hass.states.async_remove(entry.data[CONF_POWER_ENTITY])
    for bulb in entry.data[CONF_BULB_ENTITIES]:
        hass.states.async_remove(bulb)

    # Ensure deterministic entity_ids (avoid _2 suffix if a previous entry exists).
    if getattr(entity_reg, "async_remove", None):
        for ent_id in [entry.data[CONF_POWER_ENTITY], *entry.data[CONF_BULB_ENTITIES]]:
            # Create a dummy entry to ensure the remove path is exercised.
            if entity_reg.async_get(ent_id) is None:
                domain, object_id = ent_id.split(".", 1)
                entity_reg.async_get_or_create(
                    domain,
                    "test",
                    unique_id=f"preexisting:{ent_id}",
                    suggested_object_id=object_id,
                    config_entry=entry,
                )
            assert entity_reg.async_get(ent_id) is not None
            entity_reg.async_remove(ent_id)
    # Create registry entries so diagnostics can report existence accurately.
    entity_reg.async_get_or_create(
        "switch",
        "test",
        unique_id=entry.data[CONF_POWER_ENTITY],
        suggested_object_id=entry.data[CONF_POWER_ENTITY].split(".", 1)[1],
        config_entry=entry,
    )
    for bulb in entry.data[CONF_BULB_ENTITIES]:
        entity_reg.async_get_or_create(
            "light",
            "test",
            unique_id=bulb,
            suggested_object_id=bulb.split(".", 1)[1],
            config_entry=entry,
        )

    # Restore states for completeness (not required for diagnostics output).
    hass.states.async_set(entry.data[CONF_POWER_ENTITY], "on")
    for bulb in entry.data[CONF_BULB_ENTITIES]:
        hass.states.async_set(bulb, "on")

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["entry"]["entry_id"] == entry.entry_id
    assert diag["entry"]["data"][CONF_POWER_ENTITY] == "switch.relay"
    assert diag["entry"]["data"][CONF_BULB_ENTITIES] == ["light.bulb_1", "light.bulb_2"]

    assert diag["entity_registry"]["power_entity_exists"] is True
    assert diag["entity_registry"]["bulb_entities_exist"] == {
        "light.bulb_1": True,
        "light.bulb_2": True,
    }

    runtime = hass.data[DATA_KEY][entry.entry_id]
    assert diag["coordinator"]["last_update_success"] == runtime.coordinator.last_update_success
    assert diag["coordinator"]["data"] is not None

